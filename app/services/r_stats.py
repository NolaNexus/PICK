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

        gear_df = ro.DataFrame(
            {
                "name": ro.StrVector(names),
                "capacity": ro.FloatVector(capacities),
                "dig_strength": ro.FloatVector(dig_strs),
                "shake_strength": ro.FloatVector(shake_strs),
                "shake_speed": ro.FloatVector(shake_spds),
                "luck": ro.FloatVector(lucks),
                "size_boost": ro.FloatVector(size_boosts),
                "modifier_boost": ro.FloatVector(mod_boosts),
            }
        )

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


def optimize_luck_cap_continuous_r(
    current_luck: float,
    modifier_boost: float = 0.0,
    solar_magnifier: bool = False,
    modifier_surge: bool = False,
    bonus_interval: int = 10,
    n_quests: int = 100,
    lower: float = 0.0,
    upper: float = 100000.0,
) -> dict | None:
    """Continuously optimize the luck cap using R's Brent bounded search.

    Wraps R's `optimize_luck_cap_continuous`, which finds the luck cap
    maximizing expected bonuses per hour without being tied to a fixed grid.
    Returns the optimal cap, the maximum bonuses per hour, and the saturation
    cap (smallest cap within 1% tolerance of the maximum — the actionable
    recommendation).

    Gracefully returns None when R/rpy2 is unavailable.
    """
    if not R_AVAILABLE:
        return None

    try:
        optimize_luck_cap_continuous = ro.globalenv["optimize_luck_cap_continuous"]
        result = optimize_luck_cap_continuous(
            ro.FloatVector([float(current_luck)]),
            ro.FloatVector([float(modifier_boost)]),
            ro.BoolVector([bool(solar_magnifier)]),
            ro.BoolVector([bool(modifier_surge)]),
            ro.IntVector([int(bonus_interval)]),
            ro.IntVector([int(n_quests)]),
            ro.FloatVector([float(lower)]),
            ro.FloatVector([float(upper)]),
        )

        out = {}
        for col in ["optimal_cap", "optimal_bonuses_per_hour", "saturation_cap", "lower", "upper"]:
            val = list(result.rx2(col))[0]
            if hasattr(val, "item"):
                val = val.item()
            out[col] = float(val)
        return out
    except Exception:
        return None


def fit_modifier_fraction_r(
    query_eff_mb: list[float],
    obs_eff_mb: list[float],
    obs_modified: list[float],
    obs_total: list[float],
) -> list[dict] | None:
    """Fit the % ores modified curve from observed data using R.

    Wraps R's `fit_modifier_fraction` (stats::nls asymptotic exponential),
    returning predicted pct_modified (0-100) at each query eff_mb point.
    Returns None when R/rpy2 is unavailable or the fit fails to converge,
    so callers can fall back to the hardcoded approximation.

    Args:
        query_eff_mb: Effective MB values at which to predict pct_modified.
        obs_eff_mb: Observed effective MB values.
        obs_modified: Observed modified-ore counts per point.
        obs_total: Observed total ore counts per point.

    Returns:
        List of {eff_mb, pct_modified} dicts, or None on failure/unavailable.
    """
    if not R_AVAILABLE:
        return None

    if not query_eff_mb or len(obs_eff_mb) < 3:
        return None

    try:
        fit_modifier_fraction = ro.globalenv["fit_modifier_fraction"]
        result = fit_modifier_fraction(
            ro.FloatVector([float(v) for v in query_eff_mb]),
            ro.FloatVector([float(v) for v in obs_eff_mb]),
            ro.FloatVector([float(v) for v in obs_modified]),
            ro.FloatVector([float(v) for v in obs_total]),
        )

        if result is None or result.nrow == 0:
            return None

        n_rows = int(result.nrow)
        col_names = [str(c) for c in result.colnames]
        out = []
        for i in range(n_rows):
            row = {}
            for col in col_names:
                val = list(result.rx2(col))[i]
                if hasattr(val, "item"):
                    val = val.item()
                row[col] = val
            out.append(row)
        return out
    except Exception:
        return None


def _r_named_list_to_dict(result, col: str) -> dict | None:
    """Convert an R named list/vector column to a Python dict."""
    try:
        val = result.rx2(col)
        if val is None:
            return None
        names = list(val.names) if hasattr(val, "names") and val.names is not None else []
        values = list(val)
        if len(names) != len(values):
            return None
        out = {}
        for n, v in zip(names, values, strict=False):
            if hasattr(v, "item"):
                v = v.item()
            out[str(n)] = v
        return out or None
    except Exception:
        return None


def quest_survival_r(
    n_runs: int = 200,
    n_quests: int = 50,
    max_time_hours: float = 48.0,
    time_points: list[float] | None = None,
    luck_levels: list[float] | None = None,
    modifier_boost_levels: list[float] | None = None,
    meteor: bool = False,
    weather_events: int = 0,
    solar_magnifier: bool = False,
    modifier_surge: bool = False,
    bonus_interval: int = 10,
    base_pph: float = 100.0,
) -> dict | None:
    """Run Dredge Master quest survival analysis using R.

    Wraps R's `quest_survival_analysis` (survival::coxph). Simulates many quest
    runs across a grid of build/event configurations, fits a Cox proportional
    hazards model, and returns coefficients, hazard ratios, baseline median
    time-to-completion, a survival curve, and quest-completion probabilities
    within key time windows.

    Returns None when R/rpy2 is unavailable or the model fails to fit.
    """
    if not R_AVAILABLE:
        return None

    if time_points is None:
        time_points = [1.0, 5.0, 10.0, 24.0, 48.0]
    if luck_levels is None:
        luck_levels = [0.0, 5000.0, 10000.0, 25000.0, 50000.0]
    if modifier_boost_levels is None:
        modifier_boost_levels = [0.0, 200.0, 500.0, 1000.0]

    try:
        quest_survival_analysis = ro.globalenv["quest_survival_analysis"]
        result = quest_survival_analysis(
            ro.IntVector([int(n_runs)]),
            ro.IntVector([int(n_quests)]),
            ro.FloatVector([float(max_time_hours)]),
            ro.FloatVector([float(v) for v in time_points]),
            ro.FloatVector([float(v) for v in luck_levels]),
            ro.FloatVector([float(v) for v in modifier_boost_levels]),
            ro.BoolVector([bool(meteor)]),
            ro.IntVector([int(weather_events)]),
            ro.BoolVector([bool(solar_magnifier)]),
            ro.BoolVector([bool(modifier_surge)]),
            ro.IntVector([int(bonus_interval)]),
            ro.FloatVector([float(base_pph)]),
        )

        if result is None:
            return None

        out: dict = {}

        # Scalar fields (single-row result).
        for col in ["baseline_median_time_hours", "n_runs", "n_completed", "n_censored", "r_used"]:
            val = list(result.rx2(col))[0]
            if hasattr(val, "item"):
                val = val.item()
            out[col] = float(val) if col != "r_used" else bool(val)

        # Named list fields → dicts.
        coeffs = _r_named_list_to_dict(result, "coefficients")
        hrs = _r_named_list_to_dict(result, "hazard_ratios")
        out["coefficients"] = (
            {str(k): float(v) for k, v in (coeffs or {}).items()} if coeffs else {}
        )
        out["hazard_ratios"] = {str(k): float(v) for k, v in (hrs or {}).items()} if hrs else {}

        # Completion probabilities (named list) → dict keyed by time.
        cpw = _r_named_list_to_dict(result, "completion_prob_within")
        out["completion_prob_within"] = {str(k): float(v) for k, v in cpw.items()} if cpw else {}

        # Survival curve data frame → list of dicts.
        sc = result.rx2("survival_curve")
        if sc is not None and int(sc.nrow) > 0:
            sc_names = [str(c) for c in sc.colnames]
            sc_rows = []
            n_sc = int(sc.nrow)
            for i in range(n_sc):
                row = {}
                for col in sc_names:
                    v = list(sc.rx2(col))[i]
                    if hasattr(v, "item"):
                        v = v.item()
                    row[col] = v
                sc_rows.append(row)
            out["survival_curve"] = sc_rows
        else:
            out["survival_curve"] = []

        return out
    except Exception:
        return None


def ev_pareto_frontier_r(
    candidates: list[dict],
    n_samples: int = 10000,
) -> list[dict] | None:
    """Compute the EV / risk Pareto frontier for candidate builds using R.

    Wraps R's `ev_pareto_frontier`. For each candidate build (with EV per pan
    mean/SD and pans per hour mean/SD), runs a Monte Carlo simulation of
    EV/hour, then returns the non-dominated Pareto frontier on mean EV/hour
    vs p05 EV/hour (risk-adjusted downside).

    Returns None when R/rpy2 is unavailable.
    """
    if not R_AVAILABLE:
        return None

    if not candidates:
        return []

    try:
        ev_pareto_frontier = ro.globalenv["ev_pareto_frontier"]
        names = [str(c.get("name", "")) for c in candidates]
        ev_means = [float(c.get("ev_per_pan_mean", 0)) for c in candidates]
        ev_sds = [float(c.get("ev_per_pan_sd", 0)) for c in candidates]
        pph_means = [float(c.get("pph_mean", 0)) for c in candidates]
        pph_sds = [float(c.get("pph_sd", 0)) for c in candidates]

        candidates_df = ro.DataFrame(
            {
                "name": ro.StrVector(names),
                "ev_per_pan_mean": ro.FloatVector(ev_means),
                "ev_per_pan_sd": ro.FloatVector(ev_sds),
                "pph_mean": ro.FloatVector(pph_means),
                "pph_sd": ro.FloatVector(pph_sds),
            }
        )

        result = ev_pareto_frontier(
            candidates_df,
            ro.IntVector([int(n_samples)]),
        )

        if result is None or int(result.nrow) == 0:
            return []

        col_names = [str(c) for c in result.colnames]
        n_rows = int(result.nrow)
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
        return None


def is_available() -> bool:
    """Return True if R + rpy2 are available."""
    return R_AVAILABLE
