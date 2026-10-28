"""Treasure Chest scraper - parse per-location loot pools from the wiki page."""

import re
from typing import Any

from scrapers.types import ParsedItem

TAB_PATTERN = re.compile(r"\|\-\|\s*([^=\n]+?)\s*=(.*?)(?=\|\-\||$)", re.DOTALL)
TEMPLATE_PATTERN = re.compile(r"\{\{([^{}|]+)(?:\|[^}]*)?\}\}")
LINK_PATTERN = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def parse_treasure_chests(wikitext: str) -> list[ParsedItem]:
    """Parse the per-location Treasure Chest loot pools.

    A Treasure Chest is its own item. The loot depends on the location where
    the chest was found, so there is one row per location.
    """
    chests: list[ParsedItem] = []
    for location, content in _tabs(wikitext):
        loot = _parse_loot(content, location)
        if not loot:
            continue
        chests.append(
            {
                "id": _slugify(location),
                "type": "treasure_chest",
                "name": f"{location} Treasure Chest",
                "slug": _slugify(f"{location} Treasure Chest"),
                "data": {
                    "location": location,
                    "loot": loot,
                    "modifier": "Treasured",
                    "size_boost_applies": True,
                    "luck_applies": False,
                    "obtained_from": "treasure_map",
                },
                "image_url": None,
            }
        )
    return chests


def _tabs(wikitext: str) -> list[tuple[str, str]]:
    tabber = re.search(r"<tabber>(.*?)</tabber>", wikitext, re.DOTALL)
    if not tabber:
        return []
    return [
        (match.group(1).strip(), match.group(2)) for match in TAB_PATTERN.finditer(tabber.group(1))
    ]


def _parse_loot(content: str, location: str) -> list[dict[str, Any]]:
    loot: list[dict[str, Any]] = []
    for line in content.splitlines():
        line = line.strip()
        if not line.startswith("*"):
            continue

        text = line.lstrip("*").strip()
        if not text:
            continue

        lowered = text.lower()
        if lowered.startswith("random") and lowered.endswith("ore"):
            loot.append(
                {
                    "kind": "ore",
                    "location": _template_name(text) or location,
                    "label": _strip_markup(text),
                }
            )
            continue

        name = _template_name(text) or _link_name(text) or _strip_markup(text)
        if name:
            loot.append({"kind": "item", "name": name})
    return loot


def _template_name(text: str) -> str | None:
    match = TEMPLATE_PATTERN.search(text)
    return match.group(1).strip() if match else None


def _link_name(text: str) -> str | None:
    match = LINK_PATTERN.search(text)
    return match.group(1).strip() if match else None


def _strip_markup(text: str) -> str:
    text = TEMPLATE_PATTERN.sub(r"\1", text)
    text = LINK_PATTERN.sub(r"\1", text)
    text = re.sub(r"'''?", "", text)
    return text.strip()


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
