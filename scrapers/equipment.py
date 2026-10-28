"""Equipment scraper - parse {{Equipment row ...}} templates with <tabber> rarity sections."""

import re
from typing import Any

import mwparserfromhell

from scrapers.stats import parse_equipment_stats
from scrapers.types import ParsedItem


def parse_equipment(wikitext: str) -> list[ParsedItem]:
    """Parse equipment data from wikitext with tabbed rarity sections.

    Returns list of equipment dicts with name, slot, recipe, stats, price,
    description, image, and rarity tier extracted from <tabber> tab labels.
    """
    tree = mwparserfromhell.parse(wikitext)
    items: list[ParsedItem] = []

    tabbers = tree.filter_tags(matches="tabber")
    for tabber in tabbers:
        if not hasattr(tabber, "tag") or str(tabber.tag).strip() != "tabber":
            continue

        tabber_text = str(tabber).strip()

        # Parse tab labels: |-| TierName = content
        tab_pattern = r"\|\-\|\s*([^=]+)\s*=(.*?)(?=\|\-\||</?tabber>|\Z)"
        tab_matches = re.finditer(tab_pattern, tabber_text, re.DOTALL)

        for tab_match in tab_matches:
            tier = tab_match.group(1).strip()
            tab_content = tab_match.group(2).strip()

            if not tier:
                continue

            # Parse templates from this tab's content only, so items are
            # correctly associated with their rarity tier.
            content_tree = mwparserfromhell.parse(tab_content)
            for template in content_tree.filter_templates():
                template_name = str(template.name).strip()
                if "Equipment row" not in template_name:
                    continue

                item = _parse_equipment_row(template, tier)
                if item:
                    items.append(item)

    return items


def _parse_equipment_row(template: Any, tier: str) -> ParsedItem | None:
    """Parse a single {{Equipment row ...}} template into an item dict."""
    params: dict[str, str] = {}
    for param in template.params:
        key = str(param.name).strip().lower() if param.name else ""
        value = str(param.value).strip() if param.value else ""
        if key:
            params[key] = value

    name = params.get("name", "")
    if not name:
        return None

    slot = params.get("slot", "")
    price = params.get("price", "0")
    description = params.get("description", "")
    image = params.get("image", "")
    recipe = params.get("recipe", "")

    # Parse stats dynamically: stat1/val1/s6val1, stat2/val2/s6val2, etc.
    # The raw pairs are kept for display and the same values are also emitted
    # as structured modifiers so the UI and the calculators can use them.
    stats: dict[str, str] = {}
    for key, value in params.items():
        if key.startswith("stat"):
            stat_num = key.replace("stat", "")
            stats[f"stat{stat_num}"] = value
            stats[f"val{stat_num}"] = params.get(f"val{stat_num}", "")
            stats[f"s6val{stat_num}"] = params.get(f"s6val{stat_num}", "")

    modifiers = parse_equipment_stats(params)

    # Capture any extra params (candy, ornaments, etc.) not already handled
    known_keys = {
        "image",
        "name",
        "description",
        "name color",
        "slot",
        "recipe",
        "price",
    }
    extra: dict[str, str] = {}
    for key, value in params.items():
        if (
            key in known_keys
            or key.startswith("stat")
            or key.startswith("val")
            or key.startswith("s6val")
        ):
            continue
        extra[key] = value

    data: dict[str, Any] = {
        "image": image,
        "slot": slot,
        "description": description,
        "recipe": recipe,
        "stats": stats,
        "price": price,
        "rarity": tier,
    }
    if modifiers:
        data["modifiers"] = modifiers
    if extra:
        data["extra"] = extra

    return {
        "id": _slugify(name),
        "type": "equipment",
        "name": name,
        "slug": _slugify(name),
        "data": data,
        "image_url": None,
    }


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace("'", "").replace("(", "").replace(")", "")
