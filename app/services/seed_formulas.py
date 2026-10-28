"""Seed the formulas table with the wiki-confirmed formulas.

The formulas themselves are read from the wiki by ``scrapers/formulas.py`` and
stored in the ``formulas`` table. This module holds the seed data for the ones
that the wiki states outright, so they are present even before a scrape has
run.

The calculator maths used to live here too. It was duplicated in
``app/services/calculators.py`` and in the frontend's ``lib/calculators.ts``,
and none of the three copies was the one users actually got. The frontend's is
the only implementation now.
"""

from typing import Any, TypedDict

from app.models.formula import Confidence


class FormulaSeed(TypedDict):
    """One row of the formulas table."""

    formula_id: str
    name: str
    description: str | None
    formula: str
    params: dict[str, Any]
    confidence: Confidence
    source_url: str | None
    patch_version: str | None


def seed_formulas(db) -> list[FormulaSeed]:
    """Seed the formulas table with wiki-confirmed formulas."""
    formulas: list[FormulaSeed] = [
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
