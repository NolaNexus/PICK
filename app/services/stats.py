"""Statistical helpers behind the calculator endpoints.

These functions used to be a bridge to R through rpy2. R was never installed in
the container or in CI, so every call already took the pure-Python path; the
bridge has been removed and what is left is that behaviour, unchanged.
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
