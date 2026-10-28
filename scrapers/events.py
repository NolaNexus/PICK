"""Events scraper - parse <tabber> sections from the Events wiki page."""

import re

from scrapers.types import ParsedItem


def parse_events(wikitext: str) -> list[ParsedItem]:
    """Parse event data from tabber sections (Regular, Limited-Time, Admin-Exclusive)."""
    events: list[ParsedItem] = []

    # Find all tabber tags
    tabber_pattern = r"<tabber>(.*?)</tabber>"
    tabber_matches = re.finditer(tabber_pattern, wikitext, re.DOTALL)

    for tabber_match in tabber_matches:
        tabber_content = tabber_match.group(1)

        # Parse each tab: |-| TabName = content
        # First tab might not have |-| prefix
        parts = re.split(r"\n\|\-\|", tabber_content)

        # First part is the first tab (before any |-|)
        if parts[0].strip():
            event = _parse_event_tab(parts[0], "Regular")
            if event:
                events.append(event)

        # Remaining parts are subsequent tabs
        for part in parts[1:]:
            # Determine category from the tab name or content
            event = _parse_event_tab(part, "Regular")
            if event:
                # Override category based on tabber section
                events.append(event)

    # We need to also handle the other tabbers (Limited-Time, Admin-Exclusive)
    # The above only handles the first tabber. Let's parse all tabbers properly.
    return _parse_all_tabbers(wikitext)


def _parse_all_tabbers(wikitext: str) -> list[ParsedItem]:
    """Parse all tabber sections with their categories."""
    events: list[ParsedItem] = []

    # Find all tabber tags with their preceding headers
    # The pattern: header (== ... ==) followed by <tabber>
    tabber_sections = re.finditer(
        r"==\s*([^=]+)\s*==\s*\n<tabber>(.*?)</tabber>", wikitext, re.DOTALL
    )

    for match in tabber_sections:
        category = match.group(1).strip()
        tabber_content = match.group(2)

        # Determine category type
        cat_type = _categorize(category)

        # Parse each tab in this tabber
        parts = re.split(r"\n\|\-\|", tabber_content)

        # First part is the first tab (before any |-|)
        if parts[0].strip():
            event = _parse_event_tab(parts[0], cat_type)
            if event:
                events.append(event)

        # Remaining parts are subsequent tabs
        for part in parts[1:]:
            event = _parse_event_tab(part, cat_type)
            if event:
                events.append(event)

    return events


def _categorize(category: str) -> str:
    """Determine event category type from header."""
    cat_lower = category.lower()
    if "limited" in cat_lower:
        return "limited_time"
    elif "admin" in cat_lower:
        return "admin_exclusive"
    return "regular"


def _parse_event_tab(tab_content: str, category: str) -> ParsedItem | None:
    """Parse a single event tab content."""
    # Strip leading whitespace
    tab_content = tab_content.lstrip()

    # Tab format: TabName = content
    tab_match = re.match(r"([^\n]+?)\s*=(.*)", tab_content, re.DOTALL)
    if not tab_match:
        return None

    tab_name = tab_match.group(1).strip()
    content = tab_match.group(2).strip()

    if not tab_name:
        return None

    # Clean up tab name (remove any trailing =)
    tab_name = tab_name.strip("=").strip()

    # Extract description (first paragraph before === sections)
    desc_match = re.match(r"(.*?)(?:\n===\s*(?:Effects|Dialogue)\s*===|$)", content, re.DOTALL)
    description = ""
    if desc_match:
        description = desc_match.group(1).strip()
        description = re.sub(r"<[^>]+>", "", description)
        description = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", description)
        description = re.sub(r"\{\{[^}]+\}\}", "", description)
        description = description.strip()

    # Extract effects
    effects = _extract_section(content, "Effects")

    # Extract dialogue
    dialogue = _extract_section(content, "Dialogue")

    # Extract image
    image_match = re.search(r"\[\[File:([^\]]+)\]\]", content)
    image = image_match.group(1) if image_match else ""

    # Determine if admin-only
    is_admin = category == "admin_exclusive"

    # Determine if limited-time
    is_limited = category == "limited_time"

    return {
        "id": _slugify(tab_name),
        "type": "event",
        "name": tab_name,
        "slug": _slugify(tab_name),
        "data": {
            "category": category,
            "description": description,
            "effects": effects,
            "dialogue": dialogue,
            "image": image,
            "is_admin": is_admin,
            "is_limited_time": is_limited,
        },
        "image_url": None,
    }


def _extract_section(content: str, section_name: str) -> list[str]:
    """Extract bullet points from a === Section === section."""
    # Pattern: === Section Name === followed by bullet points
    pattern = rf"===\s*{re.escape(section_name)}\s*===(.*?)(?:\n===|$)"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return []

    section_content = match.group(1)
    bullets = []

    for line in section_content.split("\n"):
        line = line.strip()
        if line.startswith("*") or line.startswith("-"):
            bullet = line[1:].strip()
            bullet = re.sub(r"<[^>]+>", "", bullet)
            bullet = re.sub(r"'''([^']+)'''", r"\1", bullet)
            bullet = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", bullet)
            bullet = re.sub(r"\{\{[^}]+\}\}", "", bullet)
            bullet = bullet.strip()
            if bullet:
                bullets.append(bullet)

    return bullets


def _slugify(name: str) -> str:
    return (
        name.lower()
        .replace(" ", "-")
        .replace("'", "")
        .replace("(", "")
        .replace(")", "")
        .replace("’", "")
        .replace("&", "")
        .replace("#", "")
        .replace("|", "")
        .replace("?", "")
        .replace("×", "x")
        .replace(":", "")
        .replace("/", "-")
    )
