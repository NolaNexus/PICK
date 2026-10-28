"""Shovels scraper - parse {{Shovel row ...}} templates from the Shovels wiki page."""

from typing import Any

import mwparserfromhell

from scrapers.types import ParsedItem


def parse_shovels(wikitext: str) -> list[ParsedItem]:
    """Parse shovel data from wikitext containing {{Shovel row ...}} templates."""
    tree = mwparserfromhell.parse(wikitext)
    shovels: list[ParsedItem] = []

    for template in tree.filter_templates():
        template_name = str(template.name).strip()
        if "Shovel" in template_name or "shovel" in template_name.lower():
            params = {}
            for param in template.params:
                key = str(param.name).strip() if param.name else None
                value = str(param.value).strip() if param.value else None
                if key and value is not None:
                    params[key] = value

            name = params.get("name", "")
            if not name:
                continue

            luck = _parse_float(params.get("luck", "0"))
            capacity = _parse_float(params.get("capacity", "0"))
            strength = _parse_float(params.get("strength", "0"))
            speed = _parse_float(params.get("speed", "0"))
            price = params.get("price", "0")

            location = params.get("location", "")

            shovels.append(
                {
                    "id": _slugify(name),
                    "type": "shovel",
                    "name": name,
                    "slug": _slugify(name),
                    "data": {
                        "image": params.get("image", ""),
                        "description": params.get("description", ""),
                        "price": price,
                        "luck": luck,
                        "capacity": capacity,
                        "strength": strength,
                        "speed": speed,
                        "location": location,
                    },
                    "image_url": None,
                }
            )

    return shovels


def _parse_float(value: Any) -> float:
    """Parse a float value, returning 0.0 for invalid/empty values."""
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace("'", "").replace("(", "").replace(")", "")
