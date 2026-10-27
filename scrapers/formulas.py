"""Formulas (Stat Systems Guide) scraper - parse <tabber> sections from the Stat_Systems_Guide wiki page."""

import re
from typing import Any


def parse_formulas(wikitext: str) -> list[dict[str, Any]]:
    """Parse formula data from tabber sections (Mechanics, Luck, Capacity, etc.)."""
    items = []
    seen_slugs = set()

    # Find the main tabber
    tabber_pattern = r"<tabber>(.*?)</tabber>"
    tabber_match = re.search(tabber_pattern, wikitext, re.DOTALL)
    if not tabber_match:
        return items

    tabber_content = tabber_match.group(1)

    # Parse each tab: |-| TabName = content
    tab_pattern = r"\|\-\|\s*([^=]+)\s*=(.*?)(?=\|\-\||$)"
    tab_matches = re.finditer(tab_pattern, tabber_content, re.DOTALL)

    for tab_match in tab_matches:
        tab_name = tab_match.group(1).strip()
        tab_content = tab_match.group(2).strip()

        if not tab_name:
            continue

        # Parse formulas from this tab
        tab_items = _parse_tab_content(tab_name, tab_content)
        for item in tab_items:
            slug = item["slug"]
            if slug in seen_slugs:
                # Add suffix to make unique
                base_slug = slug
                counter = 1
                while slug in seen_slugs:
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                item["slug"] = slug
                item["id"] = slug
            seen_slugs.add(slug)
            items.append(item)

    return items


def _parse_tab_content(tab_name: str, content: str) -> list[dict[str, Any]]:
    """Parse a single tab's content for formulas and key data."""
    items = []

    # Extract the Golden Rule formula from Mechanics tab
    if "mechanic" in tab_name.lower():
        golden_rule = _extract_golden_rule(content)
        if golden_rule:
            items.append(golden_rule)

        # Extract boost catalogue
        boosts = _extract_boost_catalogue(content)
        items.extend(boosts)

    # Extract stat-specific formulas
    stat_items = _extract_stat_formulas(tab_name, content)
    items.extend(stat_items)

    # Extract modifier price table
    if "modifier" in tab_name.lower():
        mod_table = _extract_modifier_price_table(content)
        if mod_table:
            items.append(mod_table)

    # Extract museum display info
    if "museum" in tab_name.lower():
        museum_items = _extract_museum_info(content)
        items.extend(museum_items)

    return items


def _categorize_tab(tab_name: str) -> str:
    """Categorize tab by name."""
    name = tab_name.lower()
    if "mechanic" in name:
        return "mechanics"
    elif "luck" in name:
        return "luck"
    elif "capacity" in name:
        return "capacity"
    elif "dig strength" in name:
        return "dig_strength"
    elif "dig speed" in name:
        return "dig_speed"
    elif "shake" in name:
        return "shake"
    elif "size boost" in name:
        return "size_boost"
    elif "sell boost" in name:
        return "sell_boost"
    elif "modifier boost" in name:
        return "modifier_boost"
    elif "museum" in name:
        return "museum"
    elif "quality" in name or "autopan" in name:
        return "quality_autopan"
    elif "inventory" in name or "banking" in name:
        return "inventory_banking"
    elif "quick reference" in name:
        return "quick_reference"
    return "other"


def _extract_golden_rule(content: str) -> dict[str, Any] | None:
    """Extract the Golden Rule formula from the Mechanics tab."""
    if "golden rule" not in content.lower():
        return None

    # Find the example that shows the formula
    example_match = re.search(r"\{\|.*?EXAMPLE.*?\n(.*?)\n\|\}", content, re.DOTALL)
    example_text = ""
    if example_match:
        example_text = example_match.group(1)
        example_text = re.sub(r"<[^>]+>", "", example_text)
        example_text = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", example_text)
        example_text = re.sub(r"\{\{[^}]+\}\}", "", example_text)
        example_text = example_text.strip()

    return {
        "id": "golden-rule",
        "type": "formula",
        "name": "Golden Rule",
        "slug": "golden-rule",
        "data": {
            "category": "mechanics",
            "formula": "Total = (Base + Flats) × (1 + Boosts) × Events",
            "description": "Every stat on the panel is produced by this calculation. Boosts add together before the single multiplication - they never multiply each other.",
            "components": {
                "Total": "The big number on the stat panel",
                "Base": "What your equipped gear provides (parentheses on the same line)",
                "Flats": "Bonuses added as raw points (potions, quest rewards)",
                "Boosts": "Every percentage bonus, added together as decimals (totems, museum, runes, mastery, cookies, friends)",
                "Events": "True multipliers at the very end (×2 meteor shower, ×1.5 weather events)",
            },
            "example": example_text,
            "note": "Toughness, Inventory Size, Efficiency, Treasure Map Chance, Status Timer Speed, and Jump Power currently have no 'boosts' or multipliers.",
        },
        "image_url": None,
    }


def _clean_cell(text: str) -> str:
    """Clean a wiki table cell."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"'''([^']+)'''", r"\1", text)
    text = text.strip()
    # Remove leading | if present
    if text.startswith("|"):
        text = text[1:].strip()
    return text


def _extract_boost_catalogue(content: str) -> list[dict[str, Any]]:
    """Extract the boost catalogue table from the Mechanics tab."""
    items = []

    # Find the boost catalogue wikitable - it comes after "boosts that have been directly tested"
    boost_section_match = re.search(
        r"boosts that have been directly tested.*?(?:\{\| class=\"wikitable\".*?\n)(.*?)\n\|\}",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if not boost_section_match:
        return items

    table_body = boost_section_match.group(1)

    # Split by rows (|-)
    rows = re.split(r"\n\|\-", table_body)

    for row in rows:
        row = row.strip()
        if not row or row.startswith("!"):
            continue

        # Cells are separated by ||
        cells = [c.strip() for c in row.split("||")]
        if len(cells) < 3:
            continue

        boost_name = _clean_cell(cells[0])
        adds = _clean_cell(cells[1])
        notes = _clean_cell(cells[2])

        if not boost_name:
            continue

        items.append(
            {
                "id": _slugify(boost_name),
                "type": "formula",
                "name": boost_name,
                "slug": _slugify(boost_name),
                "data": {
                    "category": "boost",
                    "formula": "",
                    "description": f"Adds: {adds}. Notes: {notes}",
                    "components": {
                        "adds": adds,
                        "notes": notes,
                    },
                },
                "image_url": None,
            }
        )

    return items


def _extract_stat_formulas(tab_name: str, content: str) -> list[dict[str, Any]]:
    """Extract formulas from stat-specific tabs."""
    items = []

    # Specific known formulas per tab
    formulas = _get_known_formulas(tab_name)

    for formula_data in formulas:
        slug = _slugify(f"{tab_name} {formula_data['name']}")
        items.append(
            {
                "id": slug,
                "type": "formula",
                "name": f"{tab_name}: {formula_data['name']}",
                "slug": slug,
                "data": {
                    "category": _categorize_tab(tab_name),
                    "formula": formula_data["formula"],
                    "description": formula_data["description"],
                    "components": formula_data.get("components", {}),
                    "example": formula_data.get("example", ""),
                },
                "image_url": None,
            }
        )

    return items


def _get_known_formulas(tab_name: str) -> list[dict[str, Any]]:
    """Return known formulas for each tab."""
    formulas = []

    if "luck" in tab_name.lower():
        formulas.extend(
            [
                {
                    "name": "Ore Roll Distribution",
                    "formula": "25% at luck=1, 25% at luck/2, 50% at full luck",
                    "description": "Each ore slot rolls one of three ways: quarter at 1, quarter at half, half at full luck",
                    "example": "",
                },
                {
                    "name": "Modifier Luck",
                    "formula": "min(50, Luck / 1000) + Modifier Boost / 10",
                    "description": "Modifier Luck determines chance of modified ores",
                    "example": "",
                },
            ]
        )

    if "capacity" in tab_name.lower():
        formulas.append(
            {
                "name": "Items Per Pan",
                "formula": "avg_items = sqrt(capacity) * 1.08",
                "description": "Average number of items per pan",
                "example": "",
            }
        )

    if "dig strength" in tab_name.lower():
        formulas.append(
            {
                "name": "Dig Cliff",
                "formula": "digs = ceil(Capacity / (1.5 × Dig Strength))",
                "description": "Every time Capacity crosses a multiple of 1.5 × Dig Strength, digs increase by 1",
                "example": "",
            }
        )

    if "dig speed" in tab_name.lower():
        formulas.append(
            {
                "name": "Dig Time",
                "formula": "time_per_dig = 143.9 × Dig_Speed^(-0.93)",
                "description": "Seconds per dig based on Dig Speed",
                "example": "",
            }
        )

    if "shake" in tab_name.lower():
        formulas.append(
            {
                "name": "Shake Speed Bug",
                "formula": "shakes_per_second has irregular steps at 400%, 600-650%, 900-950%",
                "description": "Shake speed conversion is bugged; 1000-1700% is slower than 900%",
                "example": "",
            }
        )

    if "size boost" in tab_name.lower():
        formulas.append(
            {
                "name": "Weight Multiplier",
                "formula": "weight_mult = 1 + Size_Boost / 100",
                "description": "Size Boost multiplies ore weight linearly",
                "example": "",
            }
        )

    if "sell boost" in tab_name.lower():
        formulas.append(
            {
                "name": "Sell Multiplier",
                "formula": "sell_mult = 1 + Sell_Boost / 100",
                "description": "Sell Boost applies at moment of sale, multiplies base price",
                "example": "",
            }
        )

    if "modifier boost" in tab_name.lower():
        formulas.extend(
            [
                {
                    "name": "Job 1 - % Modified Ores",
                    "formula": "rises steeply, caps at 99.4% near 1900 effective MB",
                    "description": "Percentage of ores that receive a modifier",
                    "example": "",
                },
                {
                    "name": "Job 2 - Modifier Distribution",
                    "formula": "Higher effective MB shifts distribution toward rarer modifiers",
                    "description": "Determines which modifier you get on modified ores",
                    "example": "",
                },
            ]
        )

    if "museum" in tab_name.lower():
        formulas.append(
            {
                "name": "Display Value",
                "formula": "display = ore_base + modifier_rider × rarity_scale",
                "description": "Each slot gives ore base display + modifier rider scaled by rarity row (0.005 to 0.08)",
                "example": "",
            }
        )

    if "quality" in tab_name.lower() or "autopan" in tab_name.lower():
        formulas.append(
            {
                "name": "Quality Multiplier",
                "formula": "Manual: 100%, Autopan: 51% (⅔ luck), Mastered shovel enchant restores 100%",
                "description": "Quality affects everything dug; autopan at 51% quality unless Mastered enchant",
                "example": "",
            }
        )

    return formulas


def _extract_modifier_price_table(content: str) -> dict[str, Any] | None:
    """Extract the modifier price multiplier table."""
    # Find the modifier price wikitable
    table_match = re.search(
        r"\{\| class=\"wikitable\" style=\"width:100%; text-align:center;\"(.*?)\n\|\}",
        content,
        re.DOTALL,
    )
    if not table_match:
        return None

    table_body = table_match.group(1)

    # Check if this is the modifier table (has "modifier" and "price" in header)
    if "modifier" not in table_body.lower() or "price" not in table_body.lower():
        return None

    modifiers = []

    # Split by rows
    rows = re.split(r"\n\|\-", table_body)

    for row in rows:
        row = row.strip()
        if not row or row.startswith("!"):
            continue

        # This table has 5 columns: modifier, × price, modifier, × price, notes
        # But they're all on one line separated by ||
        cells = [c.strip() for c in row.split("||")]
        if len(cells) < 5:
            continue

        # First pair: modifier name and multiplier
        mod_name_1 = _clean_cell(cells[0])
        mult_1 = _clean_cell(cells[1])

        # Second pair: modifier name and multiplier
        mod_name_2 = _clean_cell(cells[2])
        mult_2 = _clean_cell(cells[3])

        # Notes
        notes = _clean_cell(cells[4]) if len(cells) > 4 else ""

        if mod_name_1 and mult_1:
            modifiers.append(
                {
                    "name": mod_name_1,
                    "multiplier": mult_1,
                    "notes": notes,
                }
            )
        if mod_name_2 and mult_2:
            modifiers.append(
                {
                    "name": mod_name_2,
                    "multiplier": mult_2,
                    "notes": notes,
                }
            )

    if not modifiers:
        return None

    return {
        "id": "modifier-price-table",
        "type": "formula",
        "name": "Modifier Price Multipliers",
        "slug": "modifier-price-table",
        "data": {
            "category": "modifier_boost",
            "formula": "",
            "description": "Price multipliers for each mineral modifier",
            "components": {
                "modifiers": modifiers,
            },
        },
        "image_url": None,
    }


def _extract_museum_info(content: str) -> list[dict[str, Any]]:
    """Extract museum display and rider information."""
    items = []

    # Look for the museum display formula
    if "display" in content.lower() and "museum" in content.lower():
        # Extract the formula from example box
        example_match = re.search(r"\{\|.*?EXAMPLE.*?\n(.*?)\n\|\}", content, re.DOTALL)
        example_text = ""
        if example_match:
            example_text = example_match.group(1)
            example_text = re.sub(r"<[^>]+>", "", example_text)
            example_text = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", example_text)
            example_text = re.sub(r"\{\{[^}]+\}\}", "", example_text)
            example_text = example_text.strip()

        items.append(
            {
                "id": "museum-display-formula",
                "type": "formula",
                "name": "Museum Display Formula",
                "slug": "museum-display-formula",
                "data": {
                    "category": "museum",
                    "formula": "display = ore_base + modifier_rider × rarity_scale",
                    "description": "Each displayed ore gives its own boost + modifier rider scaled by rarity row (0.005 Common to 0.08 Exotic). Treasured gives 2× Luck compared to Iridescent.",
                    "components": {
                        "rarity_scale": "Common: 0.005, ..., Exotic: 0.08",
                        "treasured_note": "2× Luck compared to Iridescent",
                    },
                    "example": example_text,
                },
                "image_url": None,
            }
        )

    return items


def _slugify(name: str) -> str:
    return (
        name.lower()
        .replace(" ", "-")
        .replace("'", "")
        .replace("(", "")
        .replace(")", "")
        .replace("’", "")
        .replace("&", "")
        .replace("#", "")
        .replace("×", "x")
        .replace("/", "-")
    )
