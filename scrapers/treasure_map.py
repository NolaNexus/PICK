"""Treasure Map scraper - parse per-location map types from the wiki page."""

import re

from scrapers.types import ParsedItem

DEFAULT_DROP_CHANCE = 0.2
DEFAULT_MAX_INVENTORY = 5
DEFAULT_MAX_WITH_ENCHANT = 10


def parse_treasure_maps(wikitext: str) -> list[ParsedItem]:
    """Parse the per-location Treasure Map variants.

    A Treasure Map is a special item that points at a buried Treasure Chest.
    Each map type targets one location, so there is one row per location.
    """
    drop_chance = _first_float(
        wikitext, r"base\s+([\d.]+)\s*%\s+drop\s+chance", DEFAULT_DROP_CHANCE
    )
    max_inventory = _first_int(wikitext, r"maximum\s+of\s+'''?(\d+)'''?", DEFAULT_MAX_INVENTORY)
    max_with_enchant = _first_int(
        wikitext, r"increases\s+to\s+'''?(\d+)'''?", DEFAULT_MAX_WITH_ENCHANT
    )

    return [
        {
            "id": _slugify(location),
            "type": "treasure_map",
            "name": f"{location} Treasure Map",
            "slug": _slugify(f"{location} Treasure Map"),
            "data": {
                "location": location,
                "base_drop_chance_percent": drop_chance,
                "drop_chance_scales_inversely_with_digspeed": True,
                "max_inventory": max_inventory,
                "max_inventory_with_treasure_hunter": max_with_enchant,
                "obtained_from": "digging",
                "points_to": "treasure_chest",
            },
            "image_url": None,
        }
        for location in _map_locations(wikitext)
    ]


def _map_locations(wikitext: str) -> list[str]:
    """Extract the location names listed under the Map Types heading."""
    parts = wikitext.split("== Map Types ==", 1)
    if len(parts) < 2:
        return []

    text = parts[1].split("[[Category:", 1)[0]
    locations: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("*"):
            continue
        match = re.search(r"\{\{([^{}|]+)(?:\|[^}]*)?\}\}", line)
        if match:
            name = match.group(1).strip()
            if name and name not in locations:
                locations.append(name)
    return locations


def _first_float(wikitext: str, pattern: str, default: float) -> float:
    match = re.search(pattern, wikitext, re.IGNORECASE)
    if not match:
        return default
    try:
        return float(match.group(1))
    except (TypeError, ValueError):
        return default


def _first_int(wikitext: str, pattern: str, default: int) -> int:
    match = re.search(pattern, wikitext, re.IGNORECASE)
    if not match:
        return default
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return default


def _slugify(name: str) -> str:
    return (
        name.lower()
        .replace(" ", "-")
        .replace("'", "")
        .replace("’", "")
        .replace("(", "")
        .replace(")", "")
        .replace(":", "")
        .replace("#", "")
    )
