"""Locations scraper - parse the Areas and their sub-locations.

The Locations page lists the areas a player can travel to. Each area is a tab
and holds the places inside it, marked with a ``; {{Name}}`` heading. The areas
come in two kinds, regular and limited time.

The Museum is listed as an area of its own, but it is a place inside Caldera
Park, so it is moved there.
"""

import re
from typing import Any

from scrapers.types import ParsedItem

__all__ = ["parse_locations"]

# The heading that tells the two kinds of area apart.
_CATEGORY_HEADINGS = {
    "regular areas": "regular",
    "limited time areas": "limited_time",
}

# An area that is really a place inside another area.
AREA_PARENTS = {
    "museum": "calderapark",
}

# A sub-location heading, e.g. "; {{Volcanic Sands}}".
_SUBLOCATION_HEADING = re.compile(r"^;\s*\{\{([^}|]+)(?:\|[^}]*)?\}\}", re.MULTILINE)

# A sub-location's toughness, e.g. "* {{Volcanic Sands}} - '''Toughness 4'''".
_TOUGHNESS = re.compile(r"'''Toughness\s*(\d+(?:\.\d+)?)'''", re.IGNORECASE)

# The NPCs that are in a place, e.g. "* NPCs: [[Ranger]], [[Tourist]]".
_NPCS = re.compile(r"^\*\s*NPCs?:\s*(.+)$", re.MULTILINE | re.IGNORECASE)


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace("'", "").replace("(", "").replace(")", "")


def parse_locations(wikitext: str) -> list[ParsedItem]:
    """Parse the areas and their sub-locations from the Locations page."""
    if not wikitext:
        return []

    areas = _parse_areas(wikitext)
    if not areas:
        return []

    _apply_parents(areas)

    locations: list[ParsedItem] = []
    for area in areas:
        locations.append(
            {
                "id": area["slug"],
                "type": "location",
                "name": area["name"],
                "slug": area["slug"],
                "data": {
                    "category": area["category"],
                    "description": area["description"],
                    "image": area["image"],
                    "sublocations": area["sublocations"],
                },
                "image_url": None,
            }
        )

    return locations


def _parse_areas(wikitext: str) -> list[dict[str, Any]]:
    """Read every area tab and the places inside it."""
    areas: list[dict[str, Any]] = []
    category = "regular"

    # The category headings and the tabbers are read in document order, so the
    # area under a heading gets that heading's category.
    for match in re.finditer(
        r"^==+\s*'''?(?P<heading>[^'=]+?)'''?\s*==+\s*$|<tabber>(?P<tabber>.*?)</tabber>",
        wikitext,
        re.DOTALL | re.MULTILINE,
    ):
        heading = match.group("heading")
        if heading is not None:
            key = heading.strip().lower()
            if key in _CATEGORY_HEADINGS:
                category = _CATEGORY_HEADINGS[key]
            continue

        tabber = match.group("tabber") or ""
        for area in _parse_tabs(tabber, category):
            areas.append(area)

    return areas


def _parse_tabs(table: str, category: str) -> list[dict[str, Any]]:
    """Read the areas of one tabber."""
    areas: list[dict[str, Any]] = []

    tab_pattern = r"\|\-\|\s*([^=]+?)\s*=(.*?)(?=\|\-\||\Z)"
    for match in re.finditer(tab_pattern, table, re.DOTALL):
        name = match.group(1).strip()
        content = match.group(2).strip()
        if not name:
            continue

        sublocations = _parse_sublocations(content)
        areas.append(
            {
                "name": name,
                "slug": _slugify(name),
                "category": category,
                "description": _area_description(content),
                "image": _area_image(content),
                "sublocations": sublocations,
            }
        )

    return areas


def _parse_sublocations(content: str) -> list[dict[str, Any]]:
    """Read the places inside an area."""
    sublocations: list[dict[str, Any]] = []

    matches = list(_SUBLOCATION_HEADING.finditer(content))
    for index, match in enumerate(matches):
        name = match.group(1).strip()
        if not name:
            continue

        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        block = content[start:end]

        toughness = _TOUGHNESS.search(block)
        npcs = _read_npcs(block)
        notes = _read_notes(block)

        sublocations.append(
            {
                "name": name,
                "slug": _slugify(name),
                "toughness": float(toughness.group(1)) if toughness else None,
                "npcs": npcs,
                "notes": notes,
                "image": _block_image(block),
            }
        )

    return sublocations


def _read_npcs(block: str) -> list[str]:
    """Read the NPCs that are in a place."""
    match = _NPCS.search(block)
    if not match:
        return []

    names: list[str] = []
    for link in re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", match.group(1)):
        name = link.strip()
        if name and name not in names:
            names.append(name)
    return names


def _read_notes(block: str) -> list[str]:
    """Read the notes about a place."""
    notes: list[str] = []

    for line in block.splitlines():
        stripped = line.strip()
        if not stripped.startswith("*"):
            continue
        if _NPCS.match(stripped):
            continue

        text = stripped.lstrip("* ").strip()
        text = re.sub(r"\{\{([^}|]+)(?:\|[^}]*)?\}\}", r"\1", text)
        text = re.sub(r"'''?", "", text)
        text = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", text)
        text = text.strip()
        # The toughness is read on its own, so it is not repeated here.
        if text and not _TOUGHNESS.search(stripped):
            notes.append(text)

    return notes


def _block_image(block: str) -> str:
    """Read the picture of a place."""
    match = re.search(r"\[\[File:([^\]|]+)", block)
    return match.group(1).strip() if match else ""


def _area_image(content: str) -> str:
    """Read the picture of an area."""
    return _block_image(content)


def _area_description(content: str) -> str:
    """Read the description of an area.

    The description is the text of the area that is not part of one of its
    places.
    """
    parts: list[str] = []

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith((";", "[[File:", "*")):
            continue
        if stripped.startswith("{{"):
            continue
        text = re.sub(r"\{\{([^}|]+)(?:\|[^}]*)?\}\}", r"\1", stripped)
        text = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", text)
        text = text.strip()
        if text:
            parts.append(text)

    return " ".join(parts)


def _apply_parents(areas: list[dict[str, Any]]) -> None:
    """Move an area that is really a place inside another area.

    The Locations page gives the Museum its own tab, but it is a place inside
    Caldera Park, so it belongs there as one of its places.
    """
    by_key = {_name_key(area["name"]): area for area in areas}

    for name, parent_key in AREA_PARENTS.items():
        child = by_key.get(name)
        parent = by_key.get(parent_key)
        if child is None or parent is None:
            continue

        # The child keeps its own places; they move to the parent.
        moved = child["sublocations"] or [
            {
                "name": child["name"],
                "slug": child["slug"],
                "toughness": None,
                "npcs": [],
                "notes": [],
                "image": child["image"],
            }
        ]

        existing = {entry["name"] for entry in parent["sublocations"]}
        for entry in moved:
            if entry["name"] not in existing:
                parent["sublocations"].append(entry)
                existing.add(entry["name"])

        areas.remove(child)


def _name_key(name: str) -> str:
    """Return a comparison key for a name."""
    return re.sub(r"[^a-z0-9]+", "", str(name or "").lower())
