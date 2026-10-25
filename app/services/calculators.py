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


# =============================================================================
# MUSEUM CALCULATOR
# =============================================================================

# Display configuration: rarity -> {free, locked_money, locked_shards, total}
MUSEUM_DISPLAYS = {
    "Common": {
        "free": 1, "locked_money": 1, "locked_shards": 1, "total": 3
    },
    "Uncommon": {
        "free": 1, "locked_money": 1, "locked_shards": 1, "total": 3
    },
    "Rare": {
        "free": 1, "locked_money": 1, "locked_shards": 1, "total": 3
    },
    "Epic": {
        "free": 1, "locked_money": 1, "locked_shards": 1, "total": 3
    },
    "Legendary": {
        "free": 1, "locked_money": 1, "locked_shards": 1, "total": 3
    },
    "Mythic": {
        "free": 0, "locked_money": 1, "locked_shards": 1, "total": 2
    },
    "Exotic": {
        "free": 0, "locked_money": 0, "locked_shards": 1, "total": 1
    },
}

# Rarity display order
RARITY_ORDER = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic", "Exotic"]

# Modifier base bonuses (from Stat Systems Guide)
MODIFIER_BASE_BONUSES = {
    "Perfect": {"Luck": 1, "Capacity": 1, "Size Boost": 1},
    "Treasured": {"Luck": 2},
    "Lunar": {"Dig Speed": 1, "Shake Speed": 1, "Walk Speed": 1},
    "Voidtorn": {"Luck": 1, "Capacity": 1},
    "Mutated": {"Luck": 1, "Dig Strength": 1, "Modifier Boost": 1},
    "Cosmic": {"Capacity": 1, "Shake Strength": 1},
    "Electrified": {"Dig Speed": 1, "Shake Speed": 1},
    "Iridescent": {"Luck": 1},
    "Crystalline": {"Size Boost": 1},
    "Irradiated": {"Modifier Boost": 1},
    "Scorching": {"Dig Strength": 1},
    "Glowing": {"Shake Speed": 1},
    "Pure": {"Dig Speed": 1},
    "Shiny": {"Shake Strength": 1},
}

# Rarity multipliers for modifier riders
MODIFIER_RARITY_MULTIPLIERS = {
    "Common": 0.005,
    "Uncommon": 0.0075,
    "Rare": 0.0125,
    "Epic": 0.02,
    "Legendary": 0.03,
    "Mythic": 0.05,
    "Exotic": 0.08,
}


def get_modifier_rider(modifier: str, rarity: str) -> dict[str, float]:
    """Calculate modifier rider bonuses for a given modifier and display rarity."""
    if modifier not in MODIFIER_BASE_BONUSES:
        return {}

    base = MODIFIER_BASE_BONUSES[modifier]
    multiplier = MODIFIER_RARITY_MULTIPLIERS.get(rarity, 0)

    # Treasured gives 2x the amounts
    if modifier == "Treasured":
        multiplier *= 2

    return {stat: value * multiplier for stat, value in base.items()}


def weight_factor(kg: float, min_kg: float) -> float:
    """Calculate weight factor for museum display.

    Linear scaling below min_kg: factor = kg / min_kg
    Full effect at or above min_kg: factor = 1.0
    """
    if min_kg <= 0:
        return 1.0
    if kg >= min_kg:
        return 1.0
    return kg / min_kg


def parse_bonus_stat(bonus_str: str) -> list[tuple[str, float]]:
    """Parse bonus stat string into list of (stat_name, multiplier).

    Handles formats like:
    - "Dig Speed" -> [("Dig Speed", 1.0)]
    - "Luck, Capacity" -> [("Luck", 1.0), ("Capacity", 1.0)]
    - "Dig Strength, Size Boost" -> [("Dig Strength", 1.0), ("Size Boost", 1.0)]
    - "+Luck, -Size Boost" -> [("Luck", 1.0), ("Size Boost", -1.0)]
    """
    stats = []
    parts = bonus_str.replace("{{Stat|", "").replace("}}", "").split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        multiplier = 1.0
        if part.startswith("+"):
            part = part[1:].strip()
        elif part.startswith("-"):
            part = part[1:].strip()
            multiplier = -1.0
        # Handle "0.25×" format
        if "×" in part:
            stat_part, mult_part = part.split("×")
            stat = stat_part.strip()
            try:
                multiplier = float(mult_part.replace("×", "").strip())
            except ValueError:
                pass
        else:
            stat = part
        stats.append((stat, multiplier))
    return stats


def calculate_effective_boost(
    ore_data: dict,
    kg: float,
    modifier: str | None,
    rarity: str
) -> dict[str, float]:
    """Calculate total stat boost from an ore in a display using max_boost cap.

    Args:
        ore_data: Dict with min_kg, bonus_stat, max_boost (from database)
        kg: Weight of the ore in kg
        modifier: Optional modifier name (e.g., "Perfect", "Cosmic")
        rarity: Display rarity (for modifier rider calculation)

    Returns:
        Dict of stat -> boost value (capped at max_boost)
    """
    min_kg = ore_data.get("min_kg", 0)
    bonus_str = ore_data.get("bonus_stat", "")
    max_boost = ore_data.get("max_boost", 0)

    # Parse max_boost - could be "0.05×" or "0.3×" or "0.75×, -0.5×"
    boost_values = []
    if isinstance(max_boost, str):
        for part in max_boost.split(","):
            part = part.strip().replace("×", "")
            try:
                boost_values.append(float(part))
            except ValueError:
                boost_values.append(0.0)
    else:
        boost_values = [float(max_boost)]

    # Parse bonus stats
    bonus_stats = parse_bonus_stat(bonus_str)

    # Calculate weight factor
    wf = weight_factor(kg, min_kg)

    # Calculate base ore boost (capped at max_boost via weight_factor)
    result = {}
    for i, (stat, sign) in enumerate(bonus_stats):
        boost = boost_values[i] if i < len(boost_values) else boost_values[0]
        # Apply weight factor - this caps at max_boost when kg >= min_kg
        result[stat] = result.get(stat, 0) + sign * boost * wf

    # Add modifier rider if applicable
    if modifier:
        rider = get_modifier_rider(modifier, rarity)
        for stat, value in rider.items():
            result[stat] = result.get(stat, 0) + value

    return result


def calculate_museum_comparison(
    current_displays: list[dict],
    available_ores: list[dict],
    target_stats: dict[str, float],
    size_boost: float = 0.0,
    ore_database: dict | None = None
) -> dict[str, Any]:
    """Compare current museum displays with available ores to find upgrades.

    Args:
        current_displays: List of dicts with slot_id, rarity, slot_index, ore_name, kg, modifier
        available_ores: List of dicts with name, rarity, kg, modifier (optional)
        target_stats: Dict stat_name -> weight for optimization
        size_boost: Player's size boost for weight calculation
        ore_database: Dict mapping (ore_name, rarity) -> ore_data (min_kg, bonus_stat, max_boost)

    Returns:
        Dict with slot_comparisons, current_total_stats, optimized_total_stats, by_rarity
    """
    # Group available ores by rarity
    available_by_rarity: dict[str, list[dict]] = {}
    for ore in available_ores:
        rarity = ore.get("rarity", "")
        if rarity not in available_by_rarity:
            available_by_rarity[rarity] = []
        available_by_rarity[rarity].append(ore)

    # Group current displays by rarity
    current_by_rarity: dict[str, list[dict]] = {}
    for display in current_displays:
        rarity = display.get("rarity", "")
        if rarity not in current_by_rarity:
            current_by_rarity[rarity] = []
        current_by_rarity[rarity].append(display)

    slot_comparisons = []
    current_total_stats = {}
    optimized_total_stats = {}
    by_rarity = {}

    for rarity in RARITY_ORDER:
        display_info = MUSEUM_DISPLAYS.get(rarity)
        if not display_info:
            continue

        total_slots = display_info["total"]
        current_slots = current_by_rarity.get(rarity, [])
        available_rarity_ores = available_by_rarity.get(rarity, [])

        rarity_current_total = {}
        rarity_optimized_total = {}
        current_ores = []
        recommended_swaps = []

        # Process each current display slot
        for slot in current_slots:
            slot_id = slot.get("slot_id", f"{rarity.lower()}-{slot.get('slot_index', 0)}")
            ore_name = slot.get("ore_name", "")
            kg = slot.get("kg", 0)
            modifier = slot.get("modifier")

            # Get ore data from database
            ore_data = {}
            if ore_database:
                ore_data = ore_database.get((ore_name, rarity), {})

            # Calculate current ore's effective boost
            current_boost = calculate_effective_boost(ore_data, kg, modifier, rarity)

            # Find best available ore of same rarity
            best_available = None
            best_boost = {}
            best_score = -1.0

            for avail_ore in available_rarity_ores:
                avail_name = avail_ore.get("name", "")
                avail_kg = avail_ore.get("kg", 0)
                avail_modifier = avail_ore.get("modifier")

                avail_ore_data = {}
                if ore_database:
                    avail_ore_data = ore_database.get((avail_name, rarity), {})

                avail_boost = calculate_effective_boost(avail_ore_data, avail_kg, avail_modifier, rarity)

                # Score based on target stats
                score = 0.0
                for stat, weight in target_stats.items():
                    score += avail_boost.get(stat, 0) * weight

                if score > best_score:
                    best_score = score
                    best_available = avail_ore
                    best_boost = avail_boost

            # Calculate stat deltas
            stat_deltas = {}
            all_stats = set(current_boost.keys()) | set(best_boost.keys())
            for stat in all_stats:
                current_val = current_boost.get(stat, 0)
                best_val = best_boost.get(stat, 0)
                stat_deltas[stat] = round(best_val - current_val, 4)

            # Determine recommendation
            total_delta = sum(stat_deltas.values())
            if best_available and total_delta > 0.001:  # Small threshold to avoid noise
                recommendation = f"Swap to {best_available['name']}"
            else:
                recommendation = "Keep current"

            slot_comparisons.append({
                "slot_id": slot_id,
                "rarity": rarity,
                "slot_index": slot.get("slot_index", 0),
                "current_ore": ore_name,
                "current_kg": kg,
                "current_modifier": modifier,
                "current_boost": {k: round(v, 4) for k, v in current_boost.items()},
                "best_available_ore": best_available["name"] if best_available else None,
                "best_available_kg": best_available.get("kg") if best_available else None,
                "best_available_modifier": best_available.get("modifier") if best_available else None,
                "best_boost": {k: round(v, 4) for k, v in best_boost.items()},
                "stat_deltas": stat_deltas,
                "recommendation": recommendation
            })

            # Add to current totals
            for stat, value in current_boost.items():
                current_total_stats[stat] = current_total_stats.get(stat, 0) + value
                rarity_current_total[stat] = rarity_current_total.get(stat, 0) + value

            # Add to optimized totals (use best available if better, else current)
            if best_available and total_delta > 0.001:
                for stat, value in best_boost.items():
                    optimized_total_stats[stat] = optimized_total_stats.get(stat, 0) + value
                    rarity_optimized_total[stat] = rarity_optimized_total.get(stat, 0) + value
                recommended_swaps.append({
                    "slot": slot_id,
                    "from": ore_name,
                    "to": best_available["name"]
                })
            else:
                for stat, value in current_boost.items():
                    optimized_total_stats[stat] = optimized_total_stats.get(stat, 0) + value
                    rarity_optimized_total[stat] = rarity_optimized_total.get(stat, 0) + value

            current_ores.append(ore_name)

        # Handle empty slots (if fewer current displays than total slots)
        filled_slots = len(current_slots)
        for slot_idx in range(filled_slots, total_slots):
            slot_id = f"{rarity.lower()}-{slot_idx + 1}"
            # Check if we have available ores to fill this slot
            if available_rarity_ores:
                # Find best available ore for empty slot
                best_available = None
                best_boost = {}
                best_score = -1.0

                for avail_ore in available_rarity_ores:
                    avail_name = avail_ore.get("name", "")
                    avail_kg = avail_ore.get("kg", 0)
                    avail_modifier = avail_ore.get("modifier")

                    avail_ore_data = {}
                    if ore_database:
                        avail_ore_data = ore_database.get((avail_name, rarity), {})

                    avail_boost = calculate_effective_boost(avail_ore_data, avail_kg, avail_modifier, rarity)

                    score = 0.0
                    for stat, weight in target_stats.items():
                        score += avail_boost.get(stat, 0) * weight

                    if score > best_score:
                        best_score = score
                        best_available = avail_ore
                        best_boost = avail_boost

                if best_available:
                    slot_comparisons.append({
                        "slot_id": slot_id,
                        "rarity": rarity,
                        "slot_index": slot_idx + 1,
                        "current_ore": None,
                        "current_kg": 0,
                        "current_modifier": None,
                        "current_boost": {},
                        "best_available_ore": best_available["name"],
                        "best_available_kg": best_available.get("kg"),
                        "best_available_modifier": best_available.get("modifier"),
                        "best_boost": {k: round(v, 4) for k, v in best_boost.items()},
                        "stat_deltas": {k: round(v, 4) for k, v in best_boost.items()},
                        "recommendation": f"Fill with {best_available['name']}"
                    })

                    for stat, value in best_boost.items():
                        optimized_total_stats[stat] = optimized_total_stats.get(stat, 0) + value
                        rarity_optimized_total[stat] = rarity_optimized_total.get(stat, 0) + value
                    recommended_swaps.append({
                        "slot": slot_id,
                        "from": "Empty",
                        "to": best_available["name"]
                    })

        by_rarity[rarity] = {
            "slots_filled": filled_slots,
            "total_slots": total_slots,
            "current_total_boost": {k: round(v, 4) for k, v in rarity_current_total.items()},
            "optimized_total_boost": {k: round(v, 4) for k, v in rarity_optimized_total.items()},
            "current_ores": current_ores,
            "recommended_swaps": recommended_swaps
        }

    # Round totals
    current_total_stats = {k: round(v, 4) for k, v in current_total_stats.items()}
    optimized_total_stats = {k: round(v, 4) for k, v in optimized_total_stats.items()}

    return {
        "slot_comparisons": slot_comparisons,
        "current_total_stats": current_total_stats,
        "optimized_total_stats": optimized_total_stats,
        "by_rarity": by_rarity
    }


def calculate_museum_projection(
    current_displays: list[dict],
    size_boost: float = 0.0,
    ore_database: dict | None = None
) -> dict[str, float]:
    """Calculate total stat projection from current museum setup.

    Args:
        current_displays: List of {slot_id, rarity, slot_index, ore_name, kg, modifier}
        size_boost: Player's size boost
        ore_database: Dict mapping (ore_name, rarity) -> ore_data

    Returns:
        Dict of total stat boosts
    """
    total_stats = {}

    for display in current_displays:
        rarity = display.get("rarity", "")
        ore_name = display.get("ore_name", "")
        kg = display.get("kg", 0)
        modifier = display.get("modifier")

        ore_data = {}
        if ore_database:
            ore_data = ore_database.get((ore_name, rarity), {})

        ore_boost = calculate_effective_boost(ore_data, kg, modifier, rarity)

        for stat, value in ore_boost.items():
            total_stats[stat] = total_stats.get(stat, 0) + value

    return {k: round(v, 4) for k, v in total_stats.items()}


def calculate_weight_gate(
    available_ores: list[dict],
    size_boost: float,
    ore_database: dict | None = None
) -> list[dict]:
    """Check which ores meet min_kg requirement for their rarity.

    Args:
        available_ores: List of {name, rarity, kg}
        size_boost: Player's size boost percentage
        ore_database: Dict mapping (ore_name, rarity) -> ore_data with min_kg

    Returns:
        List of {ore_name, rarity, min_kg, current_kg, effective_kg, meets_requirement}
    """
    # Weight multiplier from size boost
    weight_mult = 1 + (size_boost / 100)

    results = []
    for ore in available_ores:
        ore_name = ore.get("name", "")
        rarity = ore.get("rarity", "")

        # Look up min_kg from database
        min_kg = 0
        if ore_database:
            ore_data = ore_database.get((ore_name, rarity), {})
            min_kg = ore_data.get("min_kg", 0)

        current_kg = ore.get("kg", 0)
        effective_kg = current_kg * weight_mult

        results.append({
            "ore_name": ore_name,
            "rarity": rarity,
            "min_kg": min_kg,
            "current_kg": current_kg,
            "effective_kg": round(effective_kg, 1),
            "meets_requirement": effective_kg >= min_kg
        })

    return results


def calculate_unlock_costs(unlocked_displays: list[dict] | None = None) -> dict[str, Any]:
    """Calculate money/shards cost to unlock all museum displays.

    Args:
        unlocked_displays: List of already-unlocked display identifiers.

    Returns:
        Dict with money_cost, shards_cost, total_cost breakdown.
    """
    unlocked = set(unlocked_displays or [])
    total_money = 0
    total_shards = 0

    for rarity, info in MUSEUM_DISPLAYS.items():
        total_slots = info["total"]
        free_slots = info["free"]
        locked_money = info["locked_money"]
        locked_shards = info["locked_shards"]

        # Slots that need unlocking beyond free ones
        locked_slots = max(0, total_slots - free_slots)
        # Subtract any already-unlocked slots for this rarity
        unlocked_count = sum(
            1 for d in unlocked if d.get("rarity", "") == rarity
        )
        remaining_locked = max(0, locked_slots - unlocked_count)

        total_money += remaining_locked * locked_money
        total_shards += remaining_locked * locked_shards

    return {
        "money_cost": total_money,
        "shards_cost": total_shards,
        "total_cost": {"money": total_money, "shards": total_shards},
    }


def calculate_museum_optimizer(
    available_ores: list[dict],
    unlocked_displays: list[dict] | None = None,
    target_stats: dict[str, float] | None = None,
    size_boost: float = 0.0,
) -> dict[str, Any]:
    """Optimize museum display ore assignments for target stats.

    Args:
        available_ores: List of available ore dicts.
        unlocked_displays: List of already-unlocked display dicts.
        target_stats: Dict of stat_name -> weight for optimization.
        size_boost: Player's size boost percentage.

    Returns:
        Dict with slot_recommendations, total_stats, by_rarity,
        unlock_costs, weight_gate_info.
    """
    target_stats = target_stats or {}
    unlocked = unlocked_displays or []

    # Build current_displays from unlocked_displays for comparison
    current_displays = []
    for i, ud in enumerate(unlocked):
        current_displays.append({
            "slot_id": ud.get("slot_id", f"slot-{i}"),
            "rarity": ud.get("rarity", "Common"),
            "slot_index": ud.get("slot_index", i),
            "ore_name": ud.get("ore_name", ""),
            "kg": ud.get("kg", 0),
            "modifier": ud.get("modifier"),
        })

    # Use the existing comparison engine
    comparison = calculate_museum_comparison(
        current_displays=current_displays,
        available_ores=available_ores,
        target_stats=target_stats,
        size_boost=size_boost,
    )

    unlock_info = calculate_unlock_costs(unlocked)
    weight_info = calculate_weight_gate(
        available_ores=available_ores,
        size_boost=size_boost,
    )

    return {
        "slot_recommendations": comparison.get("slot_comparisons", []),
        "total_stats": comparison.get("optimized_total_stats", {}),
        "by_rarity": comparison.get("by_rarity", {}),
        "unlock_costs": unlock_info,
        "weight_gate_info": weight_info,
    }
