"""Trinkets scraper - parse wikitable from the Trinkets wiki page."""

import re
from typing import Any


def parse_trinkets(wikitext: str) -> list[dict[str, Any]]:
    """Parse trinket data from wikitable rows."""
    trinkets = []

    # Find the wikitable
    table_match = re.search(r"\{\| class=\"wikitable\"(.*?)\|\}", wikitext, re.DOTALL)
    if not table_match:
        return trinkets

    table_body = table_match.group(1)

    # Split by rows (|-)
    rows = re.split(r"\n\|\-", table_body)

    for row in rows:
        row = row.strip()
        if not row or row.startswith("!"):
            continue

        trinket = _parse_trinket_row(row)
        if trinket:
            trinkets.append(trinket)

    return trinkets


def _parse_trinket_row(row: str) -> dict[str, Any] | None:
    """Parse a single trinket row from the table.

    Row format (cells on separate lines starting with |):
    | Trinket name (with color span)
    | Perk/Function (image with alt text)
    | Obtainment
    | Location
    """
    # Split by lines and collect cells that start with |
    lines = row.split("\n")
    cells = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            content = stripped[1:].strip()
            cells.append(content)

    if len(cells) < 4:
        return None

    # Cell 0: Trinket name (with color span)
    name_cell = cells[0]
    # Extract name from <span style="color:#...">Name</span>
    name_match = re.search(r'<span style="color:#[^"]*">([^<]+)</span>', name_cell)
    if not name_match:
        # Fallback: just use the cell content
        name = name_cell.strip()
    else:
        name = name_match.group(1).strip()

    if not name:
        return None

    # Cell 1: Perk/Function (image with alt text describing the effect)
    perk_cell = cells[1]
    perk = ""
    alt_match = re.search(r'alt=([^\]]+)', perk_cell)
    if alt_match:
        perk = alt_match.group(1).strip()
    else:
        # Try to extract from File link
        file_match = re.search(r"\[\[File:([^\]]+)\]\]", perk_cell)
        if file_match:
            perk = file_match.group(1)

    # Cell 2: Obtainment - preserve template content like {{Sand Dollars|1000}}
    obtainment = cells[2].strip()
    # Clean up wikilinks but preserve template content
    obtainment = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", obtainment)
    # Don't remove templates - they contain useful info like currency amounts
    obtainment = obtainment.strip()

    # Cell 3: Location
    location = cells[3].strip()
    # Extract location from {{Location}} templates
    loc_match = re.findall(r"\{\{([^}]+)\}\}", location)
    if loc_match:
        location = ", ".join(loc_match)
    else:
        location = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", location)
        location = location.strip()

    # Extract color from name cell
    color_match = re.search(r'color:#([0-9A-Fa-f]+)', name_cell)
    color = f"#{color_match.group(1)}" if color_match else ""

    return {
        "id": _slugify(name),
        "type": "trinket",
        "name": name,
        "slug": _slugify(name),
        "data": {
            "perk": perk,
            "obtainment": obtainment,
            "location": location,
            "color": color,
        },
        "image_url": None,
    }


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace("'", "").replace("(", "").replace(")", "").replace("’", "")
