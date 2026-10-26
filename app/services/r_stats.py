"""R statistical bridge via rpy2.

Provides distribution fitting and Monte Carlo validation for calculator
math. Degrades gracefully to the pure-Python approximation when R/rpy2 is
not installed, so the project runs without R.
"""

from __future__ import annotations

try:
    import rpy2.robjects as ro
    from rpy2.robjects import numpy2ri
    from rpy2.robjects.packages import importr

    numpy2ri.activate()
    stats = importr("stats")
    MASS = importr("MASS")
    R_AVAILABLE = True
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
    normalized = {k: round(v / total, 6) for k, v in boosted.items()}
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

        ro.globalenv["modifier_counts"] = ro.FloatVector(counts)
        ro.globalenv["modifier_names"] = ro.StrVector(MODIFIER_ORDER)
        ro.globalenv["effective_mb"] = ro.FloatVector([float(effective_mb)])

        ro.r(
            """
            fit_distribution <- function(counts, names, effective_mb) {
                total <- sum(counts)
                if (total == 0) {
                    return(setNames(rep(0, length(counts)), names))
                }

                # Dirichlet-multinomial-ish shrinkage: add a small prior so
                # rare modifiers observed zero times still get nonzero mass.
                prior <- 0.5
                smoothed <- (counts + prior) / (total + prior * length(counts))

                # Apply effective-MB boost: higher MB shifts mass toward rarer
                # modifiers (lower base probability). Rarity weight is inverse
                # of smoothed frequency.
                rarity_weight <- 1 / (smoothed + 0.001)
                boost_factor <- switch(
                    as.character(cut(effective_mb, c(-Inf, 500, 1000, 1900, Inf))),
                    "(-Inf,500]" = 1.0,
                    "(500,1000]" = 1.5,
                    "(1000,1900]" = 2.0,
                    "(1900, Inf]" = 3.0,
                    1.0
                )
                boosted <- smoothed * (boost_factor ^ pmin(rarity_weight, 5))

                pct <- boosted / sum(boosted) * 100
                setNames(round(pct, 6), names)
            }
            """
        )
        fit_distribution = ro.globalenv["fit_distribution"]
        result = fit_distribution(
            ro.FloatVector(counts),
            ro.StrVector(MODIFIER_ORDER),
            ro.FloatVector([float(effective_mb)]),
        )
        return dict(
            zip(
                list(ro.StrVector(result).names),
                list(map(float, result)),
                strict=False,
            )
        )
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
        ro.globalenv["n_samples"] = ro.IntVector([int(samples)])
        ro.globalenv["ev_mean"] = ro.FloatVector([float(ev_per_pan_mean)])
        ro.globalenv["ev_sd"] = ro.FloatVector([float(ev_per_pan_sd)])
        ro.globalenv["pph_mean"] = ro.FloatVector([float(pph_mean)])
        ro.globalenv["pph_sd"] = ro.FloatVector([float(pph_sd)])

        ro.r(
            """
            mc_ev <- function(n, ev_mean, ev_sd, pph_mean, pph_sd) {
                set.seed(42)
                ev <- rnorm(n, mean = ev_mean, sd = ev_sd)
                pph <- rnorm(n, mean = pph_mean, sd = pph_sd)
                ev[ev < 0] <- 0
                pph[pph < 0] <- 0
                ev_hour <- ev * pph
                c(mean = mean(ev_hour), p05 = quantile(ev_hour, 0.05),
                  p95 = quantile(ev_hour, 0.95))
            }
            """
        )
        mc_ev = ro.globalenv["mc_ev"]
        result = mc_ev(
            ro.IntVector([int(samples)]),
            ro.FloatVector([float(ev_per_pan_mean)]),
            ro.FloatVector([float(ev_per_pan_sd)]),
            ro.FloatVector([float(pph_mean)]),
            ro.FloatVector([float(pph_sd)]),
        )
        names = list(ro.StrVector(result).names)
        values = list(map(float, result))
        return {
            n: round(v, 2)
            for n, v in zip(names, values, strict=False)
        }
    except Exception:
        ev_per_hour = ev_per_pan_mean * pph_mean
        return {
            "mean": round(ev_per_hour, 2),
            "p05": round(ev_per_hour * 0.9, 2),
            "p95": round(ev_per_hour * 1.1, 2),
        }


def is_available() -> bool:
    """Return True if R + rpy2 are available."""
    return R_AVAILABLE
