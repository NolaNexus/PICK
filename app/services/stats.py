"""Statistical helpers behind the calculator endpoints.

These functions used to be a bridge to R through rpy2. R was never installed in
the container or in CI, so every call already took the pure-Python path; the
bridge has been removed and what is left is that behaviour, unchanged.

The ``_r`` suffix on some names is historical. It is kept so the calculator
endpoints and their request/response shapes did not have to change.
"""

from __future__ import annotations


def _python_fallback(counts: dict[str, int], effective_mb: float) -> dict[str, float]:
    """Pure-Python approximation of the modifier distribution."""
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
    return {k: round(v / total * 100.0, 6) for k, v in boosted.items()}


def fit_modifier_distribution(
    observed_counts: dict[str, int],
    effective_mb: float,
) -> dict[str, float]:
    """Estimate the modifier drop distribution (percentages summing to 100).

    The observed counts are accepted for API stability; the approximation is
    driven by the effective modifier boost.
    """
    return _python_fallback(observed_counts or {}, effective_mb)


def monte_carlo_ev(
    samples: int,
    ev_per_pan_mean: float,
    ev_per_pan_sd: float,
    pph_mean: float,
    pph_sd: float,
) -> dict[str, float]:
    """Estimate EV per hour from the pan value and pans-per-hour means.

    A deterministic point estimate rather than a simulation: the mean is the
    product of the two means, and the 5th/95th percentiles are -10%/+10%.
    """
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
    """Return scored gear.

    The scoring model was R-only, and there is no Python implementation, so
    this returns an empty list. The endpoint keeps its shape.
    """
    return []


def score_hunt_locations_r(
    loc_names: list[str],
    loc_hunt_counts: list[int],
    loc_hunt_weights: list[float],
    loc_exotic_counts: list[int],
) -> list[dict]:
    """Return scored hunt locations (empty; the scoring model was R-only)."""
    return []


def score_exotic_locations_r(
    loc_names: list[str],
    loc_exotic_mineral_counts: list[int],
    loc_total_minerals: list[int],
    modifier_distribution: dict[str, float],
    player_modifier_boost: float,
) -> list[dict]:
    """Return scored Exotic-hunting locations (empty; the model was R-only)."""
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
    """Return the luck-cap comparison (empty; the model was R-only)."""
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
    """Return the continuous luck-cap optimum (None; the model was R-only)."""
    return None


def fit_modifier_fraction_r(
    query_eff_mb: list[float],
    obs_eff_mb: list[float],
    obs_modified: list[float],
    obs_total: list[float],
) -> list[dict] | None:
    """Return the fitted %-modified curve (None; the fit was R-only)."""
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
    """Return the quest survival analysis (None; the model was R-only)."""
    return None


def ev_pareto_frontier_r(
    candidates: list[dict],
    n_samples: int = 10000,
) -> list[dict] | None:
    """Return the EV / risk Pareto frontier (None; the model was R-only)."""
    return None


def is_available() -> bool:
    """Whether a statistical backend is available.

    Always False: there is no R backend any more, and the endpoints report
    ``r_used`` from this so clients keep seeing the same value they did when R
    was merely not installed.
    """
    return False
