"""Minerals scraper - parse {{Mineral row slim ...}} templates from the Minerals wiki page."""

import re

import mwparserfromhell

from scrapers.types import ParsedItem


def parse_minerals(wikitext: str) -> list[ParsedItem]:
    """Parse mineral data from wikitext containing Mineral tables with tabber tiers."""
    minerals: list[ParsedItem] = []

    # Find tabber sections (tiers like Common, Uncommon, etc.).
    tabber_pattern = r"<tabber>(.*?)</tabber>"
    tabber_match = re.search(tabber_pattern, wikitext, re.DOTALL | re.IGNORECASE)
    if tabber_match:
        tabber_text = tabber_match.group(1)
        tab_pattern = r"\|\-\|\s*([^=]+)\s*=(.*?)(?=\|\-\||\Z)"
        for tab_match in re.finditer(tab_pattern, tabber_text, re.DOTALL):
            tier = tab_match.group(1).strip()
            _parse_mineral_templates(tab_match.group(2), tier, minerals)

    # Templates outside a tabber have no tier.
    outside = re.sub(tabber_pattern, "", wikitext, flags=re.DOTALL | re.IGNORECASE)
    _parse_mineral_templates(outside, "", minerals)

    # Keep the first occurrence of a slug so the tabber tier wins.
    unique: list[ParsedItem] = []
    seen: set[str] = set()
    for mineral in minerals:
        if mineral["slug"] in seen:
            continue
        seen.add(mineral["slug"])
        unique.append(mineral)
    return unique


def _parse_mineral_templates(text: str, tier: str, minerals: list[ParsedItem]) -> None:
    """Parse every Mineral row slim template in a block of wikitext."""
    tree = mwparserfromhell.parse(text)
    for template in tree.filter_templates(matches="Mineral row slim"):
        params = {str(p.name).strip().lower(): str(p.value).strip() for p in template.params}

        name = params.get("name", "")
        if not name:
            continue

        try:
            value = float(params.get("value", "0").replace(",", "").strip())
        except (ValueError, TypeError):
            value = 0

        locations = _parse_mineral_locations(params.get("locations", ""))
        description = params.get("description", "")
        image = params.get("image", "")

        minerals.append(
            {
                "id": _slugify(name),
                "type": "mineral",
                "name": name,
                "slug": _slugify(name),
                "data": {
                    "image": image,
                    "value": value,
                    "locations": locations,
                    "description": description,
                    "tier": tier,
                },
                "image_url": None,
            }
        )


def _parse_mineral_locations(locations_str: str) -> list[str]:
    """Parse location names from a locations parameter."""
    locations: list[str] = []
    for match in re.finditer(r"\{\{([^}]+)\}\}", locations_str):
        name = match.group(1).strip()
        if name and name not in locations:
            locations.append(name)
    for match in re.finditer(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", locations_str):
        name = match.group(1).strip()
        if name and name not in locations:
            locations.append(name)
    return locations


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace("'", "").replace("(", "").replace(")", "")
PY