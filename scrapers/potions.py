"""Potions scraper - parse the merchant sections of the Potions wiki page.

The page lists every potion in the game, grouped by the merchant that sells
it. Each section is a wikitable with the columns Item, Cost, Effect,
Description and Image.
"""

import re
from typing import Any

from scrapers.stats import parse_modifier, parse_modifier_list

# A level-2 heading that names a merchant, e.g. "== Fortune River Town Alchemist ==".
_SECTION_PATTERN = re.compile(r"^==\s*([^=]+?)\s*==\s*$", re.MULTILINE)

# The duration a potion lasts, e.g. "(10 min)".
_DURATION_PATTERN = re.compile(r"\((\d+)\s*min\)")

# A cash amount, e.g. "{{$|50,000}}" or "{{$|200,000,000}}".
_CASH_PATTERN = re.compile(r"\{\{\$\|([\d,\.]+)\}\}")

# A shard amount, e.g. "{{Meteor Shards|30}}".
_SHARDS_PATTERN = re.compile(r"\{\{Meteor Shards\|([\d,\.]+)\}\}")

# A stat reference, e.g. "{{Stat|Luck}}" or "{{Stat|WalkSpeed}}".
_STAT_PATTERN = re.compile(r"\{\{Stat\|([^}|]+)\}\}", re.IGNORECASE)

# The table row separator.
_ROW_SEPARATOR = "\n|-"


def parse_potions(wikitext: str) -> list[dict[str, Any]]:
    """Parse the potions listed on the Potions wiki page."""
    potions: list[dict[str, Any]] = []

    for merchant, table in _merchant_tables(wikitext):
        for row in _table_rows(table):
            potion = _parse_row(row, merchant)
            if potion:
                potions.append(potion)

    return potions


def _merchant_tables(wikitext: str) -> list[tuple[str, str]]:
    """Pair every merchant heading with the table that follows it."""
    results: list[tuple[str, str]] = []

    matches = list(_SECTION_PATTERN.finditer(wikitext))
    for index, match in enumerate(matches):
        merchant = match.group(1).strip()

        # Skip the sections that are not merchants.
        if not merchant or merchant.lower() in {"overview", "trivia", "usage", "notes"}:
            continue

        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(wikitext)
        section = wikitext[start:end]

        table = _first_table(section)
        if table:
            results.append((merchant, table))

    return results


def _first_table(text: str) -> str:
    """Return the contents of the first wikitable in a section."""
    match = re.search(r"\{\|(.*?)\n\|\}", text, re.DOTALL)
    return match.group(1) if match else ""


def _table_rows(table: str) -> list[str]:
    """Split a table into its data rows."""
    rows: list[str] = []

    for chunk in table.split(_ROW_SEPARATOR):
        row = chunk.strip()
        if not row or row.startswith("!"):
            continue
        rows.append(row)

    return rows


def _cells(row: str) -> list[str]:
    """Split a table row into its cells."""
    # The first cell keeps the leading pipe of its row.
    if row.startswith("|"):
        row = row[1:]

    cells = [cell.strip() for cell in row.split("\n|")]
    return [cell for cell in cells if cell != ""]


def _parse_row(row: str, merchant: str) -> dict[str, Any] | None:
    """Parse a single potion row."""
    cells = _cells(row)
    if len(cells) < 4:
        return None

    name = _clean_name(cells[0])
    if not name:
        return None

    cost_cell = cells[1]
    effect_cell = cells[2]
    description = _clean_text(cells[3])
    image = _clean_image(cells[4]) if len(cells) > 4 else ""

    cash = _first_number(_CASH_PATTERN, cost_cell)
    shards = _first_number(_SHARDS_PATTERN, cost_cell)

    duration = _duration_of(effect_cell)
    modifiers = _effect_modifiers(effect_cell, duration)

    data: dict[str, Any] = {
        "description": description,
        "image": image,
        "effect": _clean_text(effect_cell),
        "sold_by": merchant,
    }

    if cash is not None:
        data["cost_cash"] = cash
    if shards is not None:
        data["cost_shards"] = shards
    if cash is not None or shards is not None:
        data["cost_text"] = _clean_text(cost_cell)
    if duration is not None:
        data["duration_min"] = duration
    if modifiers:
        data["modifiers"] = modifiers

    location = _location_of(merchant)
    if location:
        data["source_location"] = location

    return {
        "id": _slugify(name),
        "type": "potion",
        "name": name,
        "slug": _slugify(name),
        "data": data,
        "image_url": None,
    }


def _clean_name(cell: str) -> str:
    """Read the potion name from a cell."""
    name = re.sub(r"'{2,}", "", cell)
    name = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", name)
    name = re.sub(r"<[^>]+>", "", name)
    return name.strip()


def _clean_text(cell: str) -> str:
    """Read a text cell."""
    text = re.sub(r"\{\{Stat\|([^}|]+)\}\}", r"\1", cell, flags=re.IGNORECASE)
    text = re.sub(r"\{\{Meteor Shards\|([\d,\.]+)\}\}", r"\1 Meteor Shards", text)
    text = re.sub(r"\{\{\$\|([\d,\.]+)\}\}", r"$\1", text)
    text = re.sub(r"\{\{[^}]+\}\}", "", text)
    text = re.sub(r"\[File:([^\]|]+)(?:\|[^\]]*)?\]", r"\1", text)
    text = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"'{2,}", "", text)
    return text.strip()


def _clean_image(cell: str) -> str:
    """Read the image file name from a cell."""
    match = re.search(r"\[\[File:([^\]|]+)", cell)
    return match.group(1).strip() if match else ""


def _first_number(pattern: re.Pattern[str], text: str) -> float | None:
    """Read the first number a pattern matches, as a float."""
    match = pattern.search(text)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def _duration_of(effect: str) -> int | None:
    """Read how long a potion lasts."""
    match = _DURATION_PATTERN.search(effect)
    return int(match.group(1)) if match else None


def _effect_modifiers(effect: str, duration: int | None) -> list[dict[str, Any]]:
    """Build the stat modifiers a potion grants.

    The effect cell reads e.g. ``+250 {{Stat|Luck}}, +20% {{Stat|Dig Speed}}
    (10 min)``, so each comma separated part names its own stat.
    """
    modifiers: list[dict[str, Any]] = []
    seen: set[tuple[str, float, str]] = set()

    # Read the stat name out of the cell so the amount can be matched to it.
    parts = effect.split(",")
    for part in parts:
        stat_match = _STAT_PATTERN.search(part)
        amount_match = re.search(r"([+-]?\s*\d+(?:\.\d+)?)\s*(%|x|×)?", part)

        if not stat_match or not amount_match:
            continue

        stat = stat_match.group(1).strip()
        amount_text = amount_match.group(1)
        unit = amount_match.group(2)

        modifier = parse_modifier(amount_text, stat=stat)
        if not modifier:
            continue

        # The unit marker is next to the amount, not part of the stat.
        if unit == "%":
            modifier["unit"] = "percent"
        elif unit in {"x", "×"}:
            modifier["unit"] = "multiplier"

        if duration is not None:
            modifier["duration_min"] = duration

        key = (modifier["stat"], modifier["amount"], modifier["unit"])
        if key in seen:
            continue
        seen.add(key)
        modifiers.append(modifier)

    # Fall back to reading the whole cell when it does not name its stats.
    if not modifiers:
        modifiers = parse_modifier_list(_clean_text(effect))
        if duration is not None:
            for modifier in modifiers:
                modifier.setdefault("duration_min", duration)

    return modifiers


def _location_of(merchant: str) -> str:
    """Guess the location a merchant is found at from its name."""
    known = {
        "fortune river town alchemist": "Fortune River",
        "volcanic sands alchemist": "Volcanic Sands",
        "frostbitten path alchemist": "Frostbitten Path",
        "rotwood swamp alchemist": "Rotwood Swamp",
        "astral caverns alchemist": "Astral Caverns",
        "desert alchemist": "Sunscorched Desert",
        "shard merchant": "Fortune River",
        "traveling merchant": "",
    }
    return known.get(merchant.lower(), "")


def _slugify(name: str) -> str:
    return (
        name.lower()
        .replace(" ", "-")
        .replace("'", "")
        .replace("’", "")
        .replace("(", "")
        .replace(")", "")
        .replace(":", "")
        .replace(".", "")
    )
