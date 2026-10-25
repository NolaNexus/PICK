"""Modifiers scraper - parse == Modifier Name == sections from the Modifiers wiki page."""

import re
from typing import Any


def parse_modifiers(wikitext: str) -> list[dict[str, Any]]:
    """Parse modifier data from wiki sections headings == Modifier Name ==."""
    modifiers = []

    # Pattern to match == Modifier Name == sections
    # Each section starts with == Name == and ends before the next == or end of text
    section_pattern = r"==\s*([^=]+)\s*==\n(.*?)(?=\n==\s|$)"

    for match in re.finditer(section_pattern, wikitext, re.DOTALL):
        name = match.group(1).strip()
        content = match.group(2).strip()

        if not name or name.startswith("Mineral Modifiers"):
            continue

        modifier = _parse_modifier_section(name, content)
        if modifier:
            modifiers.append(modifier)

    return modifiers


def _parse_modifier_section(name: str, content: str) -> dict[str, Any] | None:
    """Parse a single modifier section."""
    # Extract bullet points
    bullet_pattern = r"\*\s*'''([^:]+):'''\s*(.*?)(?=\n\*|\n\*|\Z)"

    data = {
        "sell_price_multiplier": None,
        "color": None,
        "description": None,
        "image": None,
        "tools": None,
        "equipment": None,
        "location_boosts": None,
        "event_boosts": None,
        "museum_bonus": None,
        "chance": None,
    }

    for match in re.finditer(bullet_pattern, content, re.DOTALL):
        key = match.group(1).strip().lower().replace(" ", "_")
        value = match.group(2).strip()

        # Clean up the value
        value = re.sub(r"<[^>]+>", "", value)
        value = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", value)
        value = re.sub(r"\{\{[^}]+\}\}", "", value)
        value = value.strip()

        # Map keys to data fields
        if "sell_price_multiplier" in key or "sell_multiplier" in key:
            # Extract numeric multiplier
            mult_match = re.search(r"([\d.]+)×?", value)
            if mult_match:
                data["sell_price_multiplier"] = float(mult_match.group(1))
        elif "color" in key:
            # Extract hex color from style
            color_match = re.search(r'color:#([0-9A-Fa-f]+)', match.group(2))
            if color_match:
                data["color"] = f"#{color_match.group(1)}"
            else:
                data["color"] = value
        elif "description" in key:
            data["description"] = value
        elif "image" in key:
            img_match = re.search(r"\[\[File:([^\]]+)\]\]", value)
            if img_match:
                data["image"] = img_match.group(1)
            else:
                data["image"] = value
        elif "tools" in key:
            data["tools"] = value
        elif "equipment" in key:
            data["equipment"] = value
        elif "location_boost" in key or "location boost" in key:
            data["location_boosts"] = value
        elif "event_boost" in key or "event boost" in key:
            data["event_boosts"] = value
        elif "museum_bonus" in key or "museum bonus" in key:
            # Clean up stat references
            value = re.sub(r"\{\{Stat\|([^}]+)\}\}", r"\1", value)
            data["museum_bonus"] = value
        elif "chance" in key:
            data["chance"] = value

    # Skip if no meaningful data
    if data["sell_price_multiplier"] is None and data["description"] is None:
        return None

    return {
        "id": _slugify(name),
        "type": "modifier",
        "name": name,
        "slug": _slugify(name),
        "data": data,
        "image_url": None,
    }


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace("'", "").replace("(", "").replace(")", "").replace("’", "")
