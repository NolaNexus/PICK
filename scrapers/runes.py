"""Runes scraper - parse runes from the Runes wiki page wikitable."""

import re
from typing import Any

from scrapers.stats import parse_modifier_list
from scrapers.types import ParsedItem


def parse_runes(wikitext: str) -> list[ParsedItem]:
    """Parse rune data from wikitable."""
    runes: list[ParsedItem] = []

    # Find the wikitable with runes
    # The table has columns: Runes !! Icon !! Description !! Location
    table_pattern = r"\{\| class=\"wikitable\"(.*?)\|\}"

    for table_match in re.finditer(table_pattern, wikitext, re.DOTALL):
        table_content = table_match.group(1)

        # Check if this is the runes table (has "Runes !! Icon !! Description !! Location")
        if "Runes !! Icon !! Description !! Location" not in table_content:
            continue

        # Parse rows: each row starts with |-
        rows = re.split(r"\n\|\-", table_content)

        for row in rows:
            row = row.strip()
            if not row or row.startswith("!"):
                continue

            rune = _parse_rune_row(row)
            if rune:
                runes.append(rune)

    return runes


def _parse_rune_row(row: str) -> ParsedItem | None:
    """Parse a single rune row from the table."""
    # Row format:
    # | [[Runes|<span style="color:#...">Name</span>]]
    # || [[File:Icon.png|50px]]
    # || Description
    # || Location

    # Split by || to get cells
    cells = [c.strip() for c in row.split("||")]
    if len(cells) < 4:
        return None

    # Cell 0: Rune name (with color span and link)
    name_cell = cells[0]
    name_match = re.search(r"\[\[Runes\|<span[^>]*>([^<]+)</span>\]\]", name_cell)
    if not name_match:
        # Try alternative format
        name_match = re.search(r"\[\[Runes\|([^\]]+)\]\]", name_cell)
        if name_match:
            name = name_match.group(1)
            # Clean up any HTML
            name = re.sub(r"<[^>]+>", "", name).strip()
        else:
            return None
    else:
        name = name_match.group(1).strip()

    if not name:
        return None

    # Cell 1: Icon (file)
    icon_cell = cells[1]
    icon_match = re.search(r"\[\[File:([^\]]+)\]\]", icon_cell)
    icon = icon_match.group(1) if icon_match else ""

    # Cell 2: Description
    description = cells[2].strip()
    # Clean up references
    description = re.sub(r"<ref[^>]*>.*?</ref>", "", description, flags=re.DOTALL)
    description = re.sub(r"<ref[^>]*/>", "", description)
    description = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", description)

    # Cell 3: Location - extract from {{Location}} templates
    location_cell = cells[3].strip()
    location = _extract_location(location_cell)

    # Extract color from name cell for type classification
    color_match = re.search(r"color:#([0-9A-Fa-f]+)", name_cell)
    color = color_match.group(1) if color_match else ""

    # The stats the rune grants, e.g. "20% more luck during the night".
    modifiers = parse_modifier_list(description)

    data: dict[str, Any] = {
        "description": description,
        "location": location,
        "icon": icon,
        "color": color,
    }
    if modifiers:
        data["modifiers"] = modifiers

    return {
        "id": _slugify(name),
        "type": "rune",
        "name": name,
        "slug": _slugify(name),
        "data": data,
        "image_url": None,
    }


def _extract_location(text: str) -> str:
    """Extract location from wiki text, preserving {{Location}} template content."""
    # First try to find {{LocationName}} templates
    template_matches = re.findall(r"\{\{([^}]+)\}\}", text)
    if template_matches:
        # Join multiple locations with ", "
        locations = [m.strip() for m in template_matches]
        return ", ".join(locations)

    # Fallback: clean up wikilinks
    location = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", text)
    location = re.sub(r"\{\{[^}]+\}\}", "", location)
    return location.strip()


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
        .replace("–", "-")
    )
