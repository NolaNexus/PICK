"""Locations scraper - parse location tables from the Locations wiki page."""

import re
from typing import Any

import mwparserfromhell


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace("'", "").replace("(", "").replace(")", "")


def parse_locations(wikitext: str) -> list[dict[str, Any]]:
    """Parse location data from wiki page using <tabber> structure.

    Returns list of location dicts with name, description, minerals, shopkeepers.
    """
    tree = mwparserfromhell.parse(wikitext)
    locations = []

    tabbers = tree.filter_tags("tabber")
    for tabber in tabbers:
        if not hasattr(tabber, "tag") or tabber.tag != "tabber":
            continue

        tabber_text = str(tabber).strip()

        tab_pattern = r"\|\-\|\s*([^=]+)\s*=(.*?)(?=\|\-\||</?tabber>|\Z)"
        tab_matches = re.finditer(tab_pattern, tabber_text, re.DOTALL)

        for match in tab_matches:
            tab_name = match.group(1).strip()
            tab_content = match.group(2).strip()

            if not tab_name:
                continue

            location_data = _parse_location_content(tab_content)

            location_item = {
                "id": _slugify(tab_name),
                "type": "location",
                "name": tab_name,
                "slug": _slugify(tab_name),
                "data": {
                    "description": location_data.get("description", ""),
                    "minerals": location_data.get("minerals", []),
                    "shopkeepers": location_data.get("shopkeepers", []),
                },
                "image_url": None,
            }

            locations.append(location_item)

    return locations


def _parse_location_content(content_wikitext: str) -> dict[str, Any]:
    """Extract description, minerals, and shopkeepers from location content."""
    result = {
        "description": "",
        "minerals": [],
        "shopkeepers": [],
    }

    if not content_wikitext:
        return result

    lines = content_wikitext.split("\n")

    desc_parts = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(";") or stripped.startswith("{{"):
            continue
        if "File:" in stripped:
            continue
        if stripped.startswith("* NPCs:"):
            continue
        if stripped.startswith("* "):
            # Bullet point - could be description
            text = stripped[2:].strip()
            if text.startswith("Toughness"):
                continue
            if text.startswith("{{"):
                continue
            # Remove wikilinks for cleaner description
            text = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", text)
            desc_parts.append(text)

    result["description"] = " ".join(desc_parts).strip()

    result["minerals"] = _extract_mineral_references(content_wikitext)
    result["shopkeepers"] = _extract_shopkeeper_references(content_wikitext)

    return result


def _extract_mineral_references(content: str) -> list[str]:
    """Extract mineral names from [[Minerals|Name]] wikilinks."""
    minerals = []

    # Pattern: [[Minerals|MineralName]] - this is how minerals are referenced
    minerals_matches = re.findall(r"\[\[Minerals\|([^\]]+)\]\]", content)
    for m in minerals_matches:
        if m and m not in minerals:
            minerals.append(m)

    # Also look for mineral template references like {{Mineral Name}}
    # but only for known patterns
    return minerals


def _extract_shopkeeper_references(content: str) -> list[str]:
    """Extract shopkeeper names from NPCs: [[Name]], [[Name2]] lines."""
    shopkeepers = []

    # Find NPCs: lines and extract all [[Name]] or [[Name|Display]] links
    npc_pattern = r"NPCs?:\s*([^\n]+)"
    for match in re.finditer(npc_pattern, content):
        line = match.group(1)
        # Extract all wikilinks from this line
        wikilink_pattern = r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]"
        for wl_match in re.finditer(wikilink_pattern, line):
            name = wl_match.group(1).strip()
            # Filter out generic names
            if name and name not in shopkeepers:
                if name not in ("John", "Trader", "Mechanic", "Shopkeeper", "NPC"):
                    shopkeepers.append(name)
                elif name in ("John", "Trader", "Mechanic"):
                    # These are actually shopkeepers
                    shopkeepers.append(name)

    return shopkeepers
