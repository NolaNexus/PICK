"""Shared representation of the stat bonuses an item grants.

Many item types grant stats: equipment rolls a range per slot, potions grant
a flat or percentage boost for a while, museum ores give a rider, modifiers
multiply prices. They all describe the same thing in different words, so they
share one shape and one set of parsers.

A modifier looks like::

    {"stat": "Dig Speed", "amount": 20, "amount_max": 60,
     "unit": "percent", "duration_min": 20}

Only a modifier that matches a strict pattern is emitted. Text that cannot be
read confidently is left in its original field, so nothing is guessed.
"""

from __future__ import annotations

import re
from typing import Any

__all__ = [
    "StatModifier",
    "parse_modifier",
    "parse_modifier_list",
    "parse_range",
]

#: A modifier as stored on an item.
StatModifier = dict[str, Any]

# The units a stat can be granted in.
FLAT = "flat"
PERCENT = "percent"
MULTIPLIER = "multiplier"

# Stat names as the game spells them. Only these are recognised, so prose
# that happens to contain a number is not mistaken for a stat grant.
_STAT_NAMES = (
    "Dig Strength",
    "Dig Speed",
    "Shake Strength",
    "Shake Speed",
    "Inventory Size",
    "Luck",
    "Capacity",
    "Toughness",
    "Efficiency",
    "Treasure Map Chance",
    "Status Timer Speed",
    "Jump Power",
    "Modifier Boost",
    "Size Boost",
    "Sell Boost",
    "Walk Speed",
    "walkspeed",
)

# Matches "+25 Luck", "-10% Dig Speed", "+1.5x Capacity".
_MODIFIER_PATTERN = re.compile(
    r"(?P<sign>[+-])?\s*(?P<amount>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>%|x|×)?\s*"
    r"(?P<stat>[A-Za-z][A-Za-z ]*?)"
    r"(?=$|[,;(]|\s+\d|\s+for\b|\s+during\b|\s+at\b|\s+when\b|\s+more\b)"
)

# Matches the phrasing used in prose, e.g. "20% more luck during the night".
_MORE_PATTERN = re.compile(
    r"(?P<amount>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>%|x|×)?\s*more\s+"
    r"(?P<stat>[A-Za-z][A-Za-z ]*?)"
    r"(?=$|[,;(]|\s+\d|\s+for\b|\s+during\b|\s+at\b|\s+when\b)"
)

# Matches the condition a bonus applies under, e.g. "during the night".
_CONDITION_PATTERN = re.compile(r"\b(during\s+the\s+\w+|at\s+\w+\s+time|when\s+\w+)", re.IGNORECASE)

# Matches "0.3 – 0.8" (an en dash) or "0.3 - 0.8".
_RANGE_PATTERN = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*[–\-—]\s*(-?\d+(?:\.\d+)?)\s*$")


def _normalize_stat(name: str) -> str | None:
    """Return the canonical stat name, or None when it is not a known stat."""
    cleaned = name.strip().strip(".,;")
    if not cleaned:
        return None

    lowered = cleaned.lower()
    for known in _STAT_NAMES:
        if known.lower() == lowered:
            return known

    # The short forms and spacings the wiki uses.
    aliases = {
        "dig str": "Dig Strength",
        "dig str.": "Dig Strength",
        "shake str": "Shake Strength",
        "shake str.": "Shake Strength",
        "map chance": "Treasure Map Chance",
        "modifier boost": "Modifier Boost",
        "walkspeed": "Walk Speed",
        "walk speed": "Walk Speed",
        "size boost": "Size Boost",
        "sell boost": "Sell Boost",
        "inventory size": "Inventory Size",
        "jump power": "Jump Power",
        "treasure map chance": "Treasure Map Chance",
    }
    return aliases.get(lowered)


def _unit_for(unit: str | None) -> str:
    """Map a unit marker onto a schema unit."""
    if unit == "%":
        return PERCENT
    if unit in {"x", "×"}:
        return MULTIPLIER
    return FLAT


def parse_range(value: str) -> tuple[float | None, float | None]:
    """Parse a stat range such as ``0.3 – 0.8``.

    Returns ``(amount, amount_max)``. A single number yields the same value
    twice.
    """
    if value is None:
        return None, None

    text = str(value).strip()
    if not text:
        return None, None

    range_match = _RANGE_PATTERN.match(text)
    if range_match:
        low = float(range_match.group(1))
        high = float(range_match.group(2))
        if low > high:
            low, high = high, low
        return low, high

    try:
        single = float(text.rstrip("%x× "))
    except ValueError:
        return None, None
    return single, single


def parse_modifier(text: str, stat: str | None = None) -> StatModifier | None:
    """Parse a single stat grant from text.

    ``stat`` may be given when the stat is known from elsewhere and only the
    amount has to be read from the text.
    """
    if text is None:
        return None

    raw = str(text).strip()
    if not raw:
        return None

    if stat:
        name = _normalize_stat(stat)
        if not name:
            return None
        amount, amount_max = parse_range(raw)
        if amount is None:
            return None
        modifier: StatModifier = {"stat": name, "amount": amount, "unit": FLAT}
        if amount_max is not None and amount_max != amount:
            modifier["amount_max"] = amount_max
        return modifier

    # The "20% more luck" phrasing is checked first, because the plain
    # pattern would otherwise read the leading word as the stat name.
    match = _MORE_PATTERN.search(raw)
    if match:
        name = _normalize_stat(match.group("stat"))
        if not name:
            return None

        return {
            "stat": name,
            "amount": float(match.group("amount")),
            "unit": _unit_for(match.group("unit")),
        }

    match = _MODIFIER_PATTERN.search(raw)
    if not match:
        return None

    name = _normalize_stat(match.group("stat"))
    if not name:
        return None

    amount = float(match.group("amount"))
    modifier = {
        "stat": name,
        "amount": amount,
        "unit": _unit_for(match.group("unit")),
    }

    # A negative amount is a penalty.
    if match.group("sign") == "-":
        modifier["amount"] = -amount

    return modifier


def parse_modifier_list(text: str) -> list[StatModifier]:
    """Parse every stat grant mentioned in a piece of text."""
    if not text:
        return []

    modifiers: list[StatModifier] = []
    seen: set[tuple[str, float, str]] = set()

    condition = _condition_of(text)

    for chunk in re.split(r"[,;•]|\band\b|\bplus\b", str(text)):
        modifier = parse_modifier(chunk)
        if not modifier:
            continue
        key = (modifier["stat"], modifier["amount"], modifier["unit"])
        if key in seen:
            continue
        seen.add(key)
        if condition:
            modifier["condition"] = condition
        modifiers.append(modifier)

    return modifiers


def _condition_of(text: str) -> str | None:
    """Read the condition a bonus applies under, e.g. 'during the night'."""
    match = _CONDITION_PATTERN.search(str(text))
    return match.group(1).strip() if match else None


def parse_equipment_stats(params: dict[str, str]) -> list[StatModifier]:
    """Build the stat modifiers of an equipment row.

    The wiki stores them as ``stat1``/``val1`` pairs, with an optional
    ``s6val1`` for the stat the slot grants at stage 6.
    """
    modifiers: list[StatModifier] = []

    for key in sorted(params):
        if not key.startswith("stat"):
            continue

        index = key[len("stat") :]
        if not index.isdigit():
            continue

        stat_name = params.get(key, "")
        value = params.get(f"val{index}", "")
        stage_value = params.get(f"s6val{index}", "")

        modifier = parse_modifier(value, stat=stat_name)
        if modifier:
            modifiers.append(modifier)

        if stage_value:
            stage_modifier = parse_modifier(stage_value, stat=stat_name)
            if stage_modifier:
                stage_modifier["stage"] = 6
                modifiers.append(stage_modifier)

    return modifiers


def parse_multiplier(text: str, stat: str) -> StatModifier | None:
    """Parse a multiplier such as ``1.05x`` or ``2×`` for a named stat."""
    if not text:
        return None

    match = re.search(r"(-?\d+(?:\.\d+)?)\s*[x×]", str(text))
    if not match:
        return None

    name = _normalize_stat(stat)
    if not name:
        return None

    return {"stat": name, "amount": float(match.group(1)), "unit": MULTIPLIER}
