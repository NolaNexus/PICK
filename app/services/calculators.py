"""Calculator implementations using formulas from Stat_Systems_Guide."""

import math
from typing import Any

# Shake speed conversion (buggy - from Stat Systems Guide)
SHAKE_SPEED_STEPS = [
    (0, 400, 0.4),      # 0-400%: linear
    (400, 600, 0.6),    # 400-600%: buggy
    (600, 650, 0.65),   # 600-650%: sweet spot
    (650, 900, 0.9),    # 650-900%: linear
    (900, 950, 0.95),   # 900-950%: sweet spot
    (950, 1000, 0.9),   # 950-1000%: buggy zone
    (1000, 1700, 0.9),  # 1000-1700%: BUGGED - same as 900%
    (1700, float('inf'), 1.0),  # 1700%+: linear
]


def shakes_per_second(shake_speed_pct: float) -> float:
    """Calculate shakes per second from shake speed percentage.

    Based on Stat Systems Guide: shake speed conversion is buggy.
    Sweet spots: 400%, 600-650%, 900-950%
    Buggy zone: 1000-1700% (same speed as 900%)
    """
    # Base rate at 100% = 0.1 shakes/sec
    base_rate = 0.1

    for min_pct, max_pct, multiplier in SHAKE_SPEED_STEPS:
        if min_pct <= shake_speed_pct < max_pct:
            return base_rate * multiplier

    return base_rate * 1.0


def digs_per_pan(capacity: float, dig_strength: float) -> int:
    """Calculate digs per pan based on capacity and dig strength.

    Formula: digs = ceil(Capacity / (1.5 * Dig Strength))
    From Stat Systems Guide: "The moment Capacity crosses a multiple of 1.5 × Dig Strength,
    every future pan costs one more dig"
    """
    if dig_strength <= 0:
        return 1
    return max(1, math.ceil(capacity / (1.5 * dig_strength)))


def dig_time_per_dig(dig_speed: float) -> float:
    """Calculate seconds per dig based on dig speed.

    Formula: time_per_dig = 143.9 * Dig_Speed^(-0.93)
    From Stat Systems Guide
    """
    if dig_speed <= 0:
        return 1.0
    return 143.9 * (dig_speed ** -0.93)


def items_per_pan(capacity: float) -> float:
    """Calculate average items per pan based on capacity.

    Formula: avg_items = sqrt(capacity) * 1.08
    From Stat Systems Guide
    """
    if capacity <= 0:
        return 0
    return math.sqrt(capacity) * 1.08


def weight_multiplier(size_boost: float) -> float:
    """Calculate weight multiplier from size boost.

    Formula: weight_mult = 1 + Size_Boost / 100
    With Solar Magnifier: ×1.5
    With Volcanic Eruption: ×1.5
    """
    return 1 + (size_boost / 100)


def sell_multiplier(sell_boost: float) -> float:
    """Calculate sell multiplier from sell boost.

    Formula: sell_mult = 1 + Sell_Boost / 100
    Applied at moment of sale
    """
    return 1 + (sell_boost / 100)


def modifier_luck(luck: float, modifier_boost: float) -> float:
    """Calculate modifier luck.

    Formula: min(50, Luck / 1000) + Modifier Boost / 10
    From Stat Systems Guide
    """
    return min(50, luck / 1000) + (modifier_boost / 10)


def effective_modifier_boost(
    panel_modifier_boost: float,
    solar_magnifier: bool = False,
    modifier_surge: bool = False,
    for_which_modifier: bool = False
) -> float:
    """Calculate effective modifier boost.

    For Job 1 (% ores modified): Solar Magnifier doubles, Modifier Surge doubles
    For Job 2 (which modifier): Solar Magnifier does NOT double, Modifier Surge doubles
    """
    effective = panel_modifier_boost

    if for_which_modifier:
        # Job 2: which modifier you get
        if modifier_surge:
            effective *= 2
        # Solar Magnifier does NOT affect Job 2
    else:
        # Job 1: % of ores that get a modifier
        if solar_magnifier:
            effective *= 2
        if modifier_surge:
            effective *= 2

    return effective


def pct_ores_modified(effective_mb: float) -> float:
    """Calculate percentage of ores that receive a modifier.

    Rises steeply, caps at 99.4% near 1900 effective MB.
    Approximate formula based on the curve described in Stat Systems Guide.
    """
    if effective_mb <= 0:
        return 0.0
    if effective_mb >= 1900:
        return 99.4

    # Approximate the steep curve: rapid rise then plateau
    # Using a sigmoid-like curve
    x = effective_mb / 1900
    # Steep rise: use x^0.3 for initial steepness, then level off
    return min(99.4, 99.4 * (x ** 0.3) * 1.15)


# Modifier base distribution (from Stat Systems Guide table)
MODIFIER_BASE_DISTRIBUTION = {
    "Perfect": 0.002,      # 0.002%
    "Treasured": 0.01,     # treasure chests only
    "Lunar": 0.05,         # night only
    "Voidtorn": 0.1,       # Void tools only
    "Mutated": 0.3,
    "Cosmic": 1.0,
    "Iridescent": 3.0,
    "Irradiated": 8.0,
    "Crystalline": 15.0,   # geodes / Crystal Touch
    "Scorching": 25.0,
    "Glowing": 40.0,
    "Pure": 55.0,
    "Shiny": 70.0,
}

MODIFIER_PRICE_MULTIPLIERS = {
    "Perfect": 24.0,
    "Treasured": 15.0,
    "Lunar": 14.0,
    "Voidtorn": 11.0,
    "Mutated": 9.0,
    "Cosmic": 6.0,
    "Iridescent": 3.5,
    "Irradiated": 2.5,
    "Crystalline": 2.0,
    "Scorching": 2.0,
    "Glowing": 1.6,
    "Pure": 1.35,
    "Shiny": 1.2,
}


def modifier_distribution(effective_mb: float) -> dict[str, float]:
    """Calculate modifier distribution based on effective MB.

    Higher effective MB shifts distribution toward rarer modifiers.
    """
    if effective_mb <= 0:
        return dict.fromkeys(MODIFIER_BASE_DISTRIBUTION, 0.0)

    # Boost factor for rare modifiers based on effective MB
    if effective_mb >= 1900:
        rare_boost = 3.0
    elif effective_mb >= 1000:
        rare_boost = 2.0
    elif effective_mb >= 500:
        rare_boost = 1.5
    else:
        rare_boost = 1.0

    # Apply boost: rarer modifiers (lower base %) get boosted more
    boosted = {}
    for mod, base_pct in MODIFIER_BASE_DISTRIBUTION.items():
        # Rarity factor: inverse of base probability (rarer = higher factor)
        rarity_factor = 1 / (base_pct + 0.1)
        boosted[mod] = base_pct * (rare_boost ** min(rarity_factor, 5))

    # Normalize to sum to pct_modified
    pct_mod = pct_ores_modified(effective_mb)
    total = sum(boosted.values())
    normalized = {k: round(v / total * pct_mod, 3) for k, v in boosted.items()}

    return normalized


def quality_multiplier(autopan: bool = False, mastered_shovel: bool = False) -> float:
    """Calculate quality multiplier.

    Manual: 100%
    Autopan: 51% (⅔ luck)
    Mastered shovel enchant restores 100% quality
    """
    if autopan:
        if mastered_shovel:
            return 1.0
        return 0.51
    return 1.0


def pans_per_hour(
    capacity: float,
    dig_strength: float,
    dig_speed: float,
    shake_strength: float,
    shake_speed: float
) -> float:
    """Calculate pans per hour."""
    digs = digs_per_pan(capacity, dig_strength)
    dig_time = dig_time_per_dig(dig_speed)
    shake_sps = shakes_per_second(shake_speed)
    shake_time = capacity / (shake_strength * shake_sps) if shake_strength > 0 and shake_sps > 0 else 0

    pan_time = digs * dig_time + shake_time
    if pan_time <= 0:
        return 0
    return 3600 / pan_time


def calculate_ev(
    location_drop_table: list[dict],
    luck: float,
    modifier_boost: float,
    quality: float = 1.0,
    autopan: bool = False,
    mastered_shovel: bool = False,
    solar_magnifier: bool = False,
    modifier_surge: bool = False,
) -> dict[str, Any]:
    """Calculate Expected Value per pan for a location.

    Args:
        location_drop_table: List of items with 'base_price', 'base_weight', 'rarity'
        luck: Panel luck value
        modifier_boost: Panel modifier boost
        quality: Quality multiplier (1.0 = manual, 0.51 = autopan)
        autopan: Whether using autopan
        mastered_shovel: Whether has mastered shovel enchant
        solar_magnifier: Whether Solar Magnifier active
        modifier_surge: Whether Modifier Surge active
    """
    # Items per pan
    avg_items = items_per_pan(0)  # Will be overridden by location-specific capacity

    # Quality multiplier
    q = quality_multiplier(autopan, mastered_shovel)

    # Effective modifier boost
    eff_mb = effective_modifier_boost(
        modifier_boost,
        solar_magnifier=solar_magnifier,
        modifier_surge=modifier_surge
    )

    # Modifier distribution
    mod_dist = modifier_distribution(eff_mb)

    # Calculate EV
    total_ev = 0.0

    # This is a simplified calculation - real implementation needs
    # location-specific drop tables with base prices and weights

    return {
        "ev_per_pan": total_ev,
        "items_per_pan": avg_items,
        "quality_multiplier": q,
        "effective_modifier_boost": eff_mb,
        "modifier_distribution": mod_dist,
        "pct_modified": pct_ores_modified(eff_mb),
    }


def calculate_ttg(
    goal_value: float,
    location_ev_per_pan: float,
    capacity: float,
    dig_strength: float,
    dig_speed: float,
    shake_strength: float,
    shake_speed: float,
) -> dict[str, Any]:
    """Calculate Time To Goal."""
    pph = pans_per_hour(capacity, dig_strength, dig_speed, shake_strength, shake_speed)
    ev_per_hour = location_ev_per_pan * pph

    if ev_per_hour <= 0:
        hours = float('inf')
    else:
        hours = goal_value / ev_per_hour

    return {
        "hours_to_goal": round(hours, 2),
        "pans_per_hour": round(pph, 2),
        "ev_per_hour": round(ev_per_hour, 2),
        "ev_per_pan": round(location_ev_per_pan, 2),
        "digs_per_pan": digs_per_pan(capacity, dig_strength),
        "dig_time_per_dig": round(dig_time_per_dig(dig_speed), 3),
        "shake_time": round(capacity / (shake_strength * shakes_per_second(shake_speed)), 2),
    }


def calculate_modifier_odds(
    panel_modifier_boost: float,
    solar_magnifier: bool = False,
    modifier_surge: bool = False,
) -> dict[str, Any]:
    """Calculate modifier odds and distribution."""
    eff_mb_1 = effective_modifier_boost(
        panel_modifier_boost,
        solar_magnifier=solar_magnifier,
        modifier_surge=modifier_surge,
        for_which_modifier=False
    )
    eff_mb_2 = effective_modifier_boost(
        panel_modifier_boost,
        solar_magnifier=solar_magnifier,
        modifier_surge=modifier_surge,
        for_which_modifier=True
    )

    pct_mod = pct_ores_modified(eff_mb_1)
    distribution = modifier_distribution(eff_mb_2)

    return {
        "effective_modifier_boost_job1": round(eff_mb_1, 1),
        "effective_modifier_boost_job2": round(eff_mb_2, 1),
        "pct_ores_modified": round(pct_mod, 1),
        "modifier_distribution": distribution,
        "note": "Solar Magnifier doubles for Job 1 only. Modifier Surge doubles for both jobs.",
    }


def calculate_best_pan(
    pans: list[dict],
    dig_strength: float,
    shake_strength: float,
    shake_speed: float,
    target_capacity: float = 0,
    min_luck: float = 0,
    min_size_boost: float = 0,
    min_modifier_boost: float = 0,
) -> dict[str, Any]:
    """Score and recommend best pan for given build parameters."""

    scored_pans = []

    for pan in pans:
        data = pan.get("data", {})
        capacity = data.get("capacity", 0)
        dig_str = data.get("dig_strength", 0)
        shake_str = data.get("shake_strength", 0)
        shake_spd = data.get("shake_speed", 0)
        luck = data.get("luck", 0)
        size_boost = data.get("size_boost", 0)
        mod_boost = data.get("modifier_boost", 0)

        # Apply filters
        if target_capacity and capacity < target_capacity:
            continue
        if min_luck and luck < min_luck:
            continue
        if min_size_boost and size_boost < min_size_boost:
            continue
        if min_modifier_boost and mod_boost < min_modifier_boost:
            continue

        # Score the pan
        # Higher capacity = more items per pan
        # Higher dig strength = fewer digs (avoid cliff boundaries)
        # Higher shake strength/speed = faster emptying
        # Luck, Size Boost, Modifier Boost are multipliers

        # Calculate digs (lower is better)
        digs = digs_per_pan(capacity, dig_strength) if dig_strength > 0 else 999

        # Calculate pans per hour
        pph = pans_per_hour(capacity, dig_str, 1000, shake_str, shake_spd) if dig_str > 0 else 0

        # Simple scoring: prioritize PPH, then capacity, then stats
        score = (pph * 0.5) + (capacity * 0.2) + (luck * 0.1) + (size_boost * 0.1) + (mod_boost * 0.1)

        scored_pans.append({
            "pan": pan,
            "score": round(score, 2),
            "capacity": capacity,
            "digs_per_pan": digs,
            "pans_per_hour": round(pph, 2),
            "luck": luck,
            "size_boost": size_boost,
            "modifier_boost": mod_boost,
        })

    # Sort by score descending
    scored_pans.sort(key=lambda x: x["score"], reverse=True)

    return {
        "recommendations": scored_pans[:5],
        "criteria": {
            "target_capacity": target_capacity,
            "dig_strength": dig_strength,
            "shake_strength": shake_strength,
            "shake_speed": shake_speed,
        },
    }
