"""R statistical bridge via rpy2.

Provides distribution fitting, Monte Carlo validation, and gear
recommendation scoring for calculator math. Degrades gracefully to the
pure-Python approximation when R/rpy2 is not installed, so the project
runs without R.
"""

from __future__ import annotations

from pathlib import Path

try:
    import rpy2.robjects as ro
    from rpy2.robjects import numpy2ri
    from rpy2.robjects.packages import importr

    numpy2ri.activate()
    stats = importr("stats")
    MASS = importr("MASS")
    R_AVAILABLE = True

    # Source R statistical models so they live in .R files, not inline strings.
    _r_dir = Path(__file__).resolve().parent.parent.parent / "R"
    for r_file in sorted(_r_dir.glob("*.R")):
        ro.r["source"](str(r_file))

except Exception:  # rpy2 or R not installed
    ro = None  # type: ignore[assignment]
    stats = None  # type: ignore[assignment]
    MASS = None  # type: ignore[assignment]
    R_AVAILABLE = False

# Modifier categories in the same order as the hardcoded base distribution.
MODIFIER_ORDER = [
    "Perfect",
    "Treasured",
    "Lunar",
    "Voidtorn",
    "Mutated",
    "Cosmic",
    "Iridescent",
    "Irradiated",
    "Crystalline",
    "Scorching",
    "Glowing",
    "Pure",
    "Shiny",
]


def _python_fallback(counts: dict[str, int], effective_mb: float) -> dict[str, float]:
    """Pure-Python approximation matching the existing calculator behavior."""
    base = {
        "Perfect": 0.002,
        "Treasured": 0.01,
        "Lunar": 0.05,
        "Voidtorn": 0.1,
        "Mutated": 0.3,
        "Cosmic": 1.0,
        "Iridescent": 3.0,
        "Irradiated": 8.0,
        "Crystalline": 15.0,
        "Scorching": 25.0,
        "Glowing": 40.0,
        "Pure": 55.0,
        "Shiny": 70.0,
    }
    if effective_mb >= 1900:
        rare_boost = 3.0
    elif effective_mb >= 1000:
        rare_boost = 2.0
    elif effective_mb >= 500:
        rare_boost = 1.5
    else:
        rare_boost = 1.0

    boosted: dict[str, float] = {}
    for mod, base_pct in base.items():
        rarity_factor = 1 / (base_pct + 0.1)
        boosted[mod] = base_pct * (rare_boost ** min(rarity_factor, 5))

    total = sum(boosted.values())
    normalized = {k: round(v / total * 100.0, 6) for k, v in boosted.items()}
    return normalized


def fit_modifier_distribution(
    observed_counts: dict[str, int],
    effective_mb: float,
) -> dict[str, float]:
    """Fit a modifier drop distribution from observed counts using R.

    Args:
        observed_counts: Mapping of modifier name -> observed drop count.
        effective_mb: Effective modifier boost, used to weight the fit.

    Returns:
        Mapping of modifier name -> fitted percentage (0-100 scale).
    """
    if not R_AVAILABLE or not observed_counts:
        return _python_fallback(observed_counts or {}, effective_mb)

    try:
        counts = [float(observed_counts.get(m, 0)) for m in MODIFIER_ORDER]
        total = sum(counts)
        if total <= 0:
            return _python_fallback(observed_counts, effective_mb)

        fit_distribution = ro.globalenv["fit_modifier_distribution"]
        result = fit_distribution(
            ro.FloatVector(counts),
            ro.FloatVector([float(effective_mb)]),
        )
        names = list(ro.StrVector(result).names)
        values = list(map(float, result))
        return {n: round(v, 6) for n, v in zip(names, values, strict=False)}
    except Exception:
        return _python_fallback(observed_counts, effective_mb)


def monte_carlo_ev(
    samples: int,
    ev_per_pan_mean: float,
    ev_per_pan_sd: float,
    pph_mean: float,
    pph_sd: float,
) -> dict[str, float]:
    """Monte Carlo simulation of EV per hour using R.

    Args:
        samples: Number of simulation draws.
        ev_per_pan_mean: Mean EV per pan.
        ev_per_pan_sd: Standard deviation of EV per pan.
        pph_mean: Mean pans per hour.
        pph_sd: Standard deviation of pans per hour.

    Returns:
        Dict with simulated mean, 5th/95th percentile EV per hour.
    """
    if not R_AVAILABLE:
        # Deterministic point estimate fallback.
        ev_per_hour = ev_per_pan_mean * pph_mean
        return {
            "mean": round(ev_per_hour, 2),
            "p05": round(ev_per_hour * 0.9, 2),
            "p95": round(ev_per_hour * 1.1, 2),
        }

    try:
        mc_ev = ro.globalenv["monte_carlo_ev"]
        result = mc_ev(
            ro.IntVector([int(samples)]),
            ro.FloatVector([float(ev_per_pan_mean)]),
            ro.FloatVector([float(ev_per_pan_sd)]),
            ro.FloatVector([float(pph_mean)]),
            ro.FloatVector([float(pph_sd)]),
        )
        names = list(ro.StrVector(result).names)
        values = list(map(float, result))
        return {n: round(v, 2) for n, v in zip(names, values, strict=False)}
    except Exception:
        ev_per_hour = ev_per_pan_mean * pph_mean
        return {
            "mean": round(ev_per_hour, 2),
            "p05": round(ev_per_hour * 0.9, 2),
            "p95": round(ev_per_hour * 1.1, 2),
        }


def score_gear_r(
    gear: list[dict],
    dig_strength: float = 0,
    shake_strength: float = 0,
    shake_speed: float = 0,
    target_capacity: float = 0,
    min_luck: float = 0,
    min_size_boost: float = 0,
    min_modifier_boost: float = 0,
) -> list[dict]:
    """Score and rank gear using R's gear_recommendation model.

    Args:
        gear: List of gear dicts with name, capacity, dig_strength,
            shake_strength, shake_speed, luck, size_boost, modifier_boost.
        dig_strength: Player's dig strength.
        shake_strength: Player's shake strength.
        shake_speed: Player's shake speed.
        target_capacity: Optional minimum capacity filter.
        min_luck: Optional minimum luck filter.
        min_size_boost: Optional minimum size boost filter.
        min_modifier_boost: Optional minimum modifier boost filter.

    Returns:
        List of scored gear dicts sorted by score descending.
    """
    if not R_AVAILABLE or not gear:
        return []

    try:

        names = [str(g.get("name", "")) for g in gear]
        capacities = [float(g.get("capacity", 0)) for g in gear]
        dig_strs = [float(g.get("dig_strength", 0)) for g in gear]
        shake_strs = [float(g.get("shake_strength", 0)) for g in gear]
        shake_spds = [float(g.get("shake_speed", 0)) for g in gear]
        lucks = [float(g.get("luck", 0)) for g in gear]
        size_boosts = [float(g.get("size_boost", 0)) for g in gear]
        mod_boosts = [float(g.get("modifier_boost", 0)) for g in gear]

        gear_df = ro.DataFrame({
            "name": ro.StrVector(names),
            "capacity": ro.FloatVector(capacities),
            "dig_strength": ro.FloatVector(dig_strs),
            "shake_strength": ro.FloatVector(shake_strs),
            "shake_speed": ro.FloatVector(shake_spds),
            "luck": ro.FloatVector(lucks),
            "size_boost": ro.FloatVector(size_boosts),
            "modifier_boost": ro.FloatVector(mod_boosts),
        })

        score_gear = ro.globalenv["score_gear"]
        result = score_gear(
            gear_df,
            ro.FloatVector([float(dig_strength)]),
            ro.FloatVector([float(shake_strength)]),
            ro.FloatVector([float(shake_speed)]),
            ro.FloatVector([float(target_capacity)]),
            ro.FloatVector([float(min_luck)]),
            ro.FloatVector([float(min_size_boost)]),
            ro.FloatVector([float(min_modifier_boost)]),
        )

        # Convert R data frame back to list of dicts.
        n_rows = int(result.nrow)
        col_names = [str(c) for c in result.colnames]
        out = []
        for i in range(n_rows):
            row = {}
            for col in col_names:
                val = list(result.rx2(col))[i]
                if hasattr(val, "item"):
                    val = val.item()
                elif isinstance(val, bytes):
                    val = val.decode("utf-8")
                row[col] = val
            out.append(row)
        return out
    except Exception:
        return []


def score_hunt_locations_r(
    loc_names: list[str],
    loc_hunt_counts: list[int],
    loc_hunt_weights: list[float],
    loc_exotic_counts: list[int],
) -> list[dict]:
    """Score and rank locations for a mineral hunt list using R.

    Args:
        loc_names: Location names.
        loc_hunt_counts: Number of hunt-list minerals at each location.
        loc_hunt_weights: Sum of tier weights for hunt minerals at each location.
        loc_exotic_counts: Number of Exotic-tier minerals at each location.

    Returns:
        List of location score dicts sorted by score descending.
    """
    if not R_AVAILABLE or not loc_names:
        return []

    try:
        score_hunt = ro.globalenv["score_hunt_locations"]
        result = score_hunt(
            ro.StrVector([str(n) for n in loc_names]),
            ro.IntVector([int(c) for c in loc_hunt_counts]),
            ro.FloatVector([float(w) for w in loc_hunt_weights]),
            ro.IntVector([int(c) for c in loc_exotic_counts]),
        )

        n_rows = int(result.nrow)
        col_names = [str(c) for c in result.colnames]
        out = []
        for i in range(n_rows):
            row = {}
            for col in col_names:
                val = list(result.rx2(col))[i]
                if hasattr(val, "item"):
                    val = val.item()
                elif isinstance(val, bytes):
                    val = val.decode("utf-8")
                row[col] = val
            out.append(row)
        return out
    except Exception:
        return []


def score_exotic_locations_r(
    loc_names: list[str],
    loc_exotic_mineral_counts: list[int],
    loc_total_minerals: list[int],
    modifier_distribution: dict[str, float],
    player_modifier_boost: float,
) -> list[dict]:
    """Score and rank locations for Exotic modifier hunting using R.

    Args:
        loc_names: Location names.
        loc_exotic_mineral_counts: Exotic minerals at each location.
        loc_total_minerals: Total minerals at each location.
        modifier_distribution: Fitted modifier distribution (name -> pct).
        player_modifier_boost: Player's effective modifier boost.

    Returns:
        List of location score dicts sorted by score descending.
    """
    if not R_AVAILABLE or not loc_names:
        return []

    try:
        mod_names = list(modifier_distribution.keys())
        mod_pcts = list(modifier_distribution.values())

        score_exotic = ro.globalenv["score_exotic_locations"]
        result = score_exotic(
            ro.StrVector([str(n) for n in loc_names]),
            ro.IntVector([int(c) for c in loc_exotic_mineral_counts]),
            ro.IntVector([int(c) for c in loc_total_minerals]),
            ro.StrVector([str(n) for n in mod_names]),
            ro.FloatVector([float(p) for p in mod_pcts]),
            ro.FloatVector([float(player_modifier_boost)]),
        )

        n_rows = int(result.nrow)
        col_names = [str(c) for c in result.colnames]
        out = []
        for i in range(n_rows):
            row = {}
            for col in col_names:
                val = list(result.rx2(col))[i]
                if hasattr(val, "item"):
                    val = val.item()
                elif isinstance(val, bytes):
                    val = val.decode("utf-8")
                row[col] = val
            out.append(row)
        return out
    except Exception:
        return []


def optimize_luck_cap_r(
    current_luck: float,
    modifier_boost: float = 0.0,
    solar_magnifier: bool = False,
    modifier_surge: bool = False,
    bonus_interval: int = 10,
    n_quests: int = 100,
    luck_caps: list[float] | None = None,
) -> list[dict]:
    """Optimize luck cap for Dredge Master quest completion using R.

    Models quest completion rate as a function of luck cap, accounting for
    the modifier_luck curve, +3 luck per quest, and bonus rewards every X
    quests.

    Args:
        current_luck: Player's current luck.
        modifier_boost: Player's panel modifier boost.
        solar_magnifier: Whether Solar Magnifier is active.
        modifier_surge: Whether Modifier Surge is active.
        bonus_interval: Quests between bonus rewards.
        n_quests: Number of quests to simulate.
        luck_caps: List of luck cap values to evaluate. Defaults to a
            standard range if None.

    Returns:
        List of result dicts per luck cap, sorted by bonuses_per_hour desc.
        Includes an 'optimal' flag for the best cap.
    """
    if not R_AVAILABLE:
        return []

    if luck_caps is None:
        luck_caps = [0, 1000, 2500, 5000, 10000, 15000, 20000, 30000, 50000]

    try:
        optimize_luck_cap = ro.globalenv["optimize_luck_cap"]
        result = optimize_luck_cap(
            ro.FloatVector([float(current_luck)]),
            ro.FloatVector([float(modifier_boost)]),
            ro.BoolVector([bool(solar_magnifier)]),
            ro.BoolVector([bool(modifier_surge)]),
            ro.IntVector([int(bonus_interval)]),
            ro.IntVector([int(n_quests)]),
            ro.FloatVector([float(c) for c in luck_caps]),
        )

        n_rows = int(result.nrow)
        col_names = [str(c) for c in result.colnames]
        out = []
        for i in range(n_rows):
            row = {}
            for col in col_names:
                val = list(result.rx2(col))[i]
                if hasattr(val, "item"):
                    val = val.item()
                elif isinstance(val, bytes):
                    val = val.decode("utf-8")
                elif isinstance(val, (bool,)):
                    val = bool(val)
                row[col] = val
            out.append(row)
        return out
    except Exception:
        return []


def is_available() -> bool:
    """Return True if R + rpy2 are available."""
    return R_AVAILABLE
