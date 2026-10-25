"""Formula implementations from the Stat Systems Guide (confirmed formulas)."""

import math
from typing import TypedDict


class FormulaResult(TypedDict):
    value: float
    confidence: str
    source: str


def items_per_pan(capacity: float) -> float:
    """Items per pan = sqrt(capacity) × 1.08 [confirmed: Capacity tab]"""
    return math.sqrt(max(capacity, 0)) * 1.08


def size_weight_multiplier(size_boost: float) -> float:
    """Ore weight multiplier = 1 + SizeBoost/100 [confirmed: Size Boost tab]"""
    return 1 + size_boost / 100


def digs_per_pan(capacity: float, dig_strength: float) -> int:
    """Digs per pan = ceil(capacity / (1.5 × dig_strength)) [confirmed: Dig Strength tab]"""
    if dig_strength <= 0:
        return 1
    return math.ceil(capacity / (1.5 * dig_strength))


def seconds_per_dig(dig_speed: float) -> float:
    """Seconds per dig = 143.9 × speed^(-0.93) [confirmed: Dig Speed tab]"""
    if dig_speed <= 0:
        return 0.0
    return 143.9 * (dig_speed ** -0.93)


def time_per_pan(capacity: float, dig_strength: float, dig_speed: float) -> float:
    """Total time per pan = digs_per_pan × seconds_per_dig [confirmed]"""
    digs = digs_per_pan(capacity, dig_strength)
    sec_per_dig = seconds_per_dig(dig_speed)
    return digs * sec_per_dig


def modifier_luck(luck: float, modifier_boost: float) -> float:
    """Effective modifier luck = min(50, luck/1000) + modifier_boost/10 [confirmed: Luck tab]"""
    return min(50, luck / 1000) + modifier_boost / 10


def modifier_fraction(effective_luck: float) -> float:
    """
    % of ores that get a modifier [confirmed curve, no closed form].
    Rises steeply, caps ~99.4% near effective ~1,900.
    """
    # Approximate saturating function; marked as approximate in formulas table
    cap = 0.994
    scale = 1900.0
    return cap * (1 - math.exp(-effective_luck / scale))


def event_luck_multiplier(meteor: bool = False, weather_events: int = 0) -> float:
    """Event luck multiplier: ×2 for meteor, ×1.5 per weather event [confirmed: Events tab]"""
    mult = 1.0
    if meteor:
        mult *= 2.0
    mult *= 1.5 ** weather_events
    return mult


def golden_rule(base: float, flats: float, boosts: float) -> float:
    """Golden Rule: Total = (Base + Flats) × (1 + Boosts) [confirmed: Stat Systems Guide Mechanics]"""
    return (base + flats) * (1 + boosts)


def seed_formulas(db) -> list[dict]:
    """Seed the formulas table with wiki-confirmed formulas."""
    formulas = [
        {
            "formula_id": "golden-rule",
            "name": "Stat Total (Golden Rule)",
            "description": "Total = (Base + Flats) × (1 + Boosts). Boosts add as decimals.",
            "formula": "(base + flats) * (1 + sum(boosts))",
            "params": {
                "base": "number",
                "flats": "number",
                "boosts": "number[]",
            },
            "confidence": "confirmed",
            "source_url": "https://prospecting.miraheze.org/wiki/Stat_Systems_Guide",
            "patch_version": "2024-12",
        },
        {
            "formula_id": "items-per-pan",
            "name": "Items per Pan",
            "description": "Items per pan = sqrt(capacity) × 1.08",
            "formula": "sqrt(capacity) * 1.08",
            "params": {"capacity": "number"},
            "confidence": "confirmed",
            "source_url": "https://prospecting.miraheze.org/wiki/Stat_Systems_Guide#Capacity",
            "patch_version": "2024-12",
        },
        {
            "formula_id": "size-weight-multiplier",
            "name": "Ore Weight Multiplier",
            "description": "Ore weight multiplier = 1 + SizeBoost/100",
            "formula": "1 + size_boost / 100",
            "params": {"size_boost": "number"},
            "confidence": "confirmed",
            "source_url": "https://prospecting.miraheze.org/wiki/Stat_Systems_Guide#Size_Boost",
            "patch_version": "2024-12",
        },
        {
            "formula_id": "digs-per-pan",
            "name": "Digs per Pan",
            "description": "Digs per pan = ceil(capacity / (1.5 × dig_strength))",
            "formula": "ceil(capacity / (1.5 * dig_strength))",
            "params": {"capacity": "number", "dig_strength": "number"},
            "confidence": "confirmed",
            "source_url": "https://prospecting.miraheze.org/wiki/Stat_Systems_Guide#Dig_Strength",
            "patch_version": "2024-12",
        },
        {
            "formula_id": "seconds-per-dig",
            "name": "Seconds per Dig",
            "description": "Seconds per dig = 143.9 × speed^(-0.93)",
            "formula": "143.9 * speed^(-0.93)",
            "params": {"dig_speed": "number"},
            "confidence": "confirmed",
            "source_url": "https://prospecting.miraheze.org/wiki/Stat_Systems_Guide#Dig_Speed",
            "patch_version": "2024-12",
        },
        {
            "formula_id": "modifier-luck",
            "name": "Effective Modifier Luck",
            "description": "Effective modifier luck = min(50, luck/1000) + modifier_boost/10",
            "formula": "min(50, luck / 1000) + modifier_boost / 10",
            "params": {"luck": "number", "modifier_boost": "number"},
            "confidence": "confirmed",
            "source_url": "https://prospecting.miraheze.org/wiki/Stat_Systems_Guide#Luck",
            "patch_version": "2024-12",
        },
        {
            "formula_id": "modifier-fraction",
            "name": "Modifier Fraction (Ores with Modifier)",
            "description": "Rises steeply, caps ~99.4% near effective ~1,900. No closed form.",
            "formula": "cap * (1 - exp(-effective_luck / scale))",
            "params": {"effective_luck": "number"},
            "confidence": "approximate",
            "source_url": "https://prospecting.miraheze.org/wiki/Stat_Systems_Guide#Modifier_Boost",
            "patch_version": "2024-12",
        },
        {
            "formula_id": "event-luck-multiplier",
            "name": "Event Luck Multiplier",
            "description": "×2 for meteor, ×1.5 per weather event. Stack multiplicatively.",
            "formula": "2 if meteor else 1 * 1.5^weather_events",
            "params": {"meteor": "bool", "weather_events": "int"},
            "confidence": "confirmed",
            "source_url": "https://prospecting.miraheze.org/wiki/Events",
            "patch_version": "2024-12",
        },
    ]
    return formulas
