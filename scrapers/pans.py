"""Pans scraper - parse {{Pan row ...}} templates from the Pans wiki page."""

from typing import Any

import mwparserfromhell


def parse_pans(wikitext: str) -> list[dict[str, Any]]:
    """Parse pan data from wikitext containing {{Pan row ...}} templates."""
    tree = mwparserfromhell.parse(wikitext)
    pans = []

    for template in tree.filter_templates():
        template_name = str(template.name).strip()
        if "Pan" in template_name or "pan" in template_name.lower():
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

            pans.append(
                {
                    "id": _slugify(name),
                    "type": "pan",
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

    return pans


def _parse_float(value: Any) -> float:
    """Parse a float value, returning 0.0 for invalid/empty values."""
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace("'", "").replace("(", "").replace(")", "")
