"""Sluices scraper - parse {{Sluice row ...}} templates from the Sluices wiki page."""

from typing import Any

import mwparserfromhell


def parse_sluices(wikitext: str) -> list[dict[str, Any]]:
    """Parse sluice data from wikitext containing {{Sluice row ...}} templates."""
    tree = mwparserfromhell.parse(wikitext)
    sluices = []

    for template in tree.filter_templates():
        template_name = str(template.name).strip()
        if "Sluice" in template_name or "sluice" in template_name.lower():
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
            efficiency = _parse_float(params.get("efficiency", "0"))
            toughness = _parse_float(params.get("toughness", "0"))
            price = params.get("price", "0")

            # Handle limited-time sluice extra params
            eggs = _parse_float(params.get("eggs", "0"))

            location = params.get("location", "")

            sluices.append(
                {
                    "id": _slugify(name),
                    "type": "sluice",
                    "name": name,
                    "slug": _slugify(name),
                    "data": {
                        "image": params.get("image", ""),
                        "description": params.get("description", ""),
                        "price": price,
                        "luck": luck,
                        "capacity": capacity,
                        "efficiency": efficiency,
                        "toughness": toughness,
                        "location": location,
                        "name_color": params.get("name color", ""),
                        "eggs": eggs if eggs > 0 else None,
                    },
                    "image_url": None,
                }
            )

    return sluices


def _parse_float(value: Any) -> float:
    """Parse a float value, returning 0.0 for invalid/empty values."""
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace("'", "").replace("(", "").replace(")", "")
