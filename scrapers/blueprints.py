"""Blueprint scraper - parse blueprints from the Blueprint wiki page tabber."""

import re
from typing import Any


def parse_blueprints(wikitext: str) -> list[dict[str, Any]]:
    """Parse blueprint data from tabber sections."""
    blueprints = []

    # Find all tabber tags
    tabber_pattern = r"<tabber>(.*?)</tabber>"

    for tabber_match in re.finditer(tabber_pattern, wikitext, re.DOTALL):
        tabber_content = tabber_match.group(1)

        # The first tab doesn't have |-| before it, subsequent ones do
        # Split by |-| but keep the first part
        parts = re.split(r"\n\|\-\|", tabber_content)

        # First part is the first tab (before any |-|)
        if parts[0].strip():
            blueprint = _parse_blueprint_tab(parts[0])
            if blueprint:
                blueprints.append(blueprint)

        # Remaining parts are subsequent tabs
        for part in parts[1:]:
            blueprint = _parse_blueprint_tab(part)
            if blueprint:
                blueprints.append(blueprint)

    return blueprints


def _parse_blueprint_tab(tab_content: str) -> dict[str, Any] | None:
    """Parse a single blueprint tab content."""
    # Strip leading whitespace (from split)
    tab_content = tab_content.lstrip()

    # Tab format: TabName = content
    # The tab name can contain = signs (wiki markup)
    tab_match = re.match(r"([^\n]+?)\s*=(.*)", tab_content, re.DOTALL)
    if not tab_match:
        return None

    tab_name = tab_match.group(1).strip()
    content = tab_match.group(2).strip()

    if not tab_name:
        return None

    return _parse_blueprint_content(tab_name, content)


def _parse_blueprint_content(name: str, content: str) -> dict[str, Any] | None:
    """Parse a single blueprint's content."""
    # Clean up the name (remove " Blueprint" suffix if present, and wiki markup)
    clean_name = name.replace(" Blueprint", "").strip()
    # Remove wiki markup like ===== [[Equipment...|Name]] Blueprint =====
    markup_match = re.search(r"=+\s*\[\[[^\]]+\|([^\]]+)\]\]\s*Blueprint\s*=+", clean_name)
    if markup_match:
        clean_name = markup_match.group(1).strip()
    else:
        # Remove any remaining = signs
        clean_name = clean_name.strip("=").strip()

    if not clean_name:
        return None

    # Extract image
    image_match = re.search(r"\[\[File:([^\]]+)\]\]", content)
    image = image_match.group(1) if image_match else ""

    # Extract quest giver
    quest_giver = ""
    giver_match = re.search(r"'''Quest Giver:'''\s*\[\[([^\]]+)\]\]", content)
    if giver_match:
        quest_giver = giver_match.group(1)
    else:
        giver_match = re.search(r"'''Quest Giver:'''\s*([^\n]+)", content)
        if giver_match:
            quest_giver = giver_match.group(1).strip()

    # Extract quest name
    quest_name = ""
    quest_match = re.search(r"'''Quest Name:'''\s*\[\[([^\]]+)\]\]", content)
    if quest_match:
        quest_name = quest_match.group(1)
    else:
        quest_match = re.search(r"'''Quest Name:'''\s*([^\n]+)", content)
        if quest_match:
            quest_name = quest_match.group(1).strip()

    # Extract quest steps - look for {{Quest ...}} templates
    quest_steps = []
    quest_pattern = r"\{\{Quest\s*\n(.*?)\n\}\}"
    for quest_match in re.finditer(quest_pattern, content, re.DOTALL):
        quest_content = quest_match.group(1)
        step = _parse_quest_template(quest_content)
        if step:
            quest_steps.append(step)

    # Also check for simple purchase info
    purchase_info = ""
    if not quest_giver:
        buy_match = re.search(
            r"(?:can be bought|can be purchased).+?(?:for|costs)\s+([^\n.]+)",
            content,
            re.IGNORECASE,
        )
        if buy_match:
            purchase_info = buy_match.group(0).strip()

    event_shop = ""
    if "Event shop" in content or "Easter Event shop" in content:
        event_shop_match = re.search(
            r"(?:Easter|Event) shop.*?for\s+([^\n.]+)", content, re.IGNORECASE
        )
        if event_shop_match:
            event_shop = event_shop_match.group(0).strip()

    bp_type = "blueprint"

    return {
        "id": _slugify(clean_name),
        "type": bp_type,
        "name": clean_name,
        "slug": _slugify(clean_name),
        "data": {
            "description": f"Blueprint for {clean_name}",
            "image": image,
            "quest_giver": quest_giver,
            "quest_name": quest_name,
            "quest_steps": quest_steps,
            "purchase_info": purchase_info,
            "event_shop": event_shop,
        },
        "image_url": None,
    }


def _parse_quest_template(content: str) -> dict[str, Any]:
    """Parse a {{Quest}} template content.

    The template's fields are written as ``|QuestSub = value`` with spaces
    around the equals sign, so the field separator has to allow them.
    """
    result: dict[str, Any] = {}

    # Extract fields like |Quest = ..., |QuestStep1 = ..., etc.
    field_pattern = r"\|\s*([A-Za-z0-9_]+)\s*=\s*(.*?)(?=\n\|\s*[A-Za-z0-9_]+\s*=|\n\}\}|$)"

    for match in re.finditer(field_pattern, content, re.DOTALL):
        key = match.group(1).strip()
        value = match.group(2).strip()
        if value:
            result[key] = value

    return result


def _slugify(name: str) -> str:
    return (
        name.lower()
        .replace(" ", "-")
        .replace("'", "")
        .replace("(", "")
        .replace(")", "")
        .replace("’", "")
        .replace(":", "")
        .replace("#", "")
        .replace(".", "")
    )
