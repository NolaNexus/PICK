# R Statistical Tiers — Implementation Plan

**Status:** OBSOLETE — do not implement. The entire R integration was deleted along
with the backend calculator API in commit `5af31c5`, and the API itself was then
removed entirely: there is no `R/` directory, no `app/services/r_stats.py`, no
`app/schemas/calculator.py`, no `rpy2` in `requirements*.txt`, no
`/calculators/stats/*` route, and no `app/api/` or `app/main.py`. The plan's premise
— "R stays server-side doing statistical inference the browser cannot" — has no
server side left to live on. The calculator maths is client-side only, in
`frontend/src/lib/calculators.ts` and `frontend/src/lib/museum.ts`.

If statistical work is wanted again, it starts from nothing and should be written
as a new plan against the current tree, not revived from this one.

**Guiding principle:** R stays server-side doing statistical inference/simulation/optimization that the browser cannot. Do NOT port R math to the frontend (calculator port is already done client-side). R is optional with Python graceful degradation preserved.

---

## Tier 1 — Keep & harden (R already the natural home)

**Goal:** Make the existing R-backed endpoints actually use R when installed, and harden them.

### 1a. fit_modifier_distribution (shrinkage prior + effective-MB boost)
- R script `R/fit_modifier_distribution.R`: Bayesian shrinkage prior so zero-count modifiers still get mass; effective-MB shifts mass to rarer modifiers.
- Bridge `r_stats.py::fit_modifier_distribution`: calls R, falls back to `_python_fallback`.
- Endpoint `POST /calculators/stats/modifier-distribution` — exists, returns `modifier_distribution`, `r_used`, `effective_mb`.

### 1b. monte_carlo_ev (simulation + confidence intervals)
- R script `R/monte_carlo_ev.R`: correlated normal draws, mean + p05/p95 of EV/hour.
- Bridge `r_stats.py::monte_carlo_ev`: calls R, falls back to deterministic point estimate.
- Endpoint `POST /calculators/stats/monte-carlo-ev` — exists.

### Tier 1 work items
1. Install R + `rpy2==3.5.14` in dev env and Dockerfile (already has `RPY2_CFFI_MODE=ABI`).
2. Add R to `requirements.txt` (already: `rpy2==3.5.14`).
3. Add tests asserting `r_used=True` when R available, output shape correctness, fallback parity with Python.
4. Verify all 6 stats endpoints return `r_used: true` once R is installed.

---

## Tier 2 — Upgrade to leverage R's unique strengths (not just Python ports)

**Goal:** Replace heuristic Python approximations with statistically principled R methods.

### 2a. luck_cap_optimization → continuous optimization
**Current:** `R/luck_cap_optimization.R` brute-forces a fixed grid of luck caps and picks max `bonuses_per_hour`.
**Upgrade:** Frame as continuous optimization. Use R's `optim()` / `nlminb()` (L-BFGS-B) over luck cap (bounded [0, 100000]) maximizing expected bonuses per hour, accounting for the +3 luck/quest accrual and modifier_luck curve. Return both the continuous optimum and a per-cap table for UI comparison.

**Files to change:**
- `R/luck_cap_optimization.R`: add `optimize_luck_cap_continuous()` using `optim()`; keep `optimize_luck_cap()` grid for backwards compat.
- `app/services/r_stats.py`: add `optimize_luck_cap_continuous_r()` wrapper calling the new R function; fall back to grid when R unavailable.
- `app/schemas/calculator.py`: add `LuckCapOptimizationContinuousRequest`/`Response` schemas (current_luck, modifier_boost, solar_magnifier, modifier_surge, bonus_interval, bounds).
- `app/api/calculators.py`: add `POST /calculators/stats/optimize-luck-cap-continuous` endpoint returning `optimal_cap`, `optimal_bonuses_per_hour`, `r_used`.
- Tests: compare continuous optimum vs grid optimum on synthetic inputs.

### 2b. pct_ores_modified curve → fit from observed data
**Current:** `pct_ores_modified()` in `calculators.py` uses hardcoded `x^0.3 * 1.15` approximation capped at 99.4% near MB 1900.
**Upgrade:** Fit the modifier-fraction curve from observed drop counts using R's `mgcv::gam()` (smooth saturating curve) or `stats::nls()`. Store per-player / per-build fitted curve; fall back to the approximation when no data.

**Files to change:**
- `R/`: new `R/modifier_fraction_curve.R` with `fit_modifier_fraction(obs_modified, obs_total, eff_mb)` using `mgcv::gam()` (family binomial, logit link) or `nls()` saturating model.
- `app/services/r_stats.py`: add `fit_modifier_fraction_r()` wrapper.
- `app/services/calculators.py`: `modifier_distribution()` / `pct_ores_modified()` accept optional observed counts; use fitted curve when available.
- `app/schemas/calculator.py`: `ModifierFractionFitRequest`/`Response`.
- `app/api/calculators.py`: `POST /calculators/stats/modifier-fraction` endpoint.
- Tests: fitted curve within tolerance of known data.

---

## Tier 3 — New high-value capabilities (only R practically provides)

**Goal:** Capabilities Python cannot match practically; R's survival/GAM/optimization/ggplot2 ecosystem.

### 3a. Hierarchical modifier drop model (partial pooling across players)
New player with few observed drops borrows strength from the population → accurate modifier odds immediately; community data compounds.
- R: `brms` or `rstanarm` hierarchical binomial model: modifier drop ~ player + population prior, partial pooling.
- Bridge: POST player's observed counts, get back shrunken per-modifier probabilities.
- Endpoint: `POST /calculators/stats/hierarchical-modifier-distribution`.
- Schema: `HierarchicalModifierRequest` (player_id, observed_counts, effective_mb, population_prior optional).

### 3b. Survival analysis for Dredge Master quests
R's `survival` package (gold standard for time-to-event). Model expected quest completion with censoring (incomplete quests), competing risks (different mineral targets), covariates (luck, MB, solar magnifier, modifier surge).
- R: `survival::survreg()` / `coxph()` on quest completion times.
- Output: median time-to-quest-complete, hazard ratios, survival curve points.
- Endpoint: `POST /calculators/stats/quest-survival`.
- Schema: `QuestSurvivalRequest` (current_luck, modifier_boost, events, target_mineral, n_simulations).

### 3c. EV frontier / Pareto multi-objective optimization
Multi-objective trade-offs: EV vs risk vs time. Use R's `emoa` / `mco` or custom weighted scalarization with `optim()`. Return Pareto frontier points (EV/hour, p05 EV, hours) so players see trade-off curves, not one recommendation.
- Endpoint: `POST /calculators/stats/ev-frontier`.
- Schema: `EvFrontierRequest` (gear options, location drop table, objective weights).

### 3d. ggplot2 statistical plots
Serve plot JSON/images for the React frontend: modifier distribution curves, EV/TTG sensitivity plots, luck-cap trade-off curves, survival curves.
- R: `ggplot2` + `plotly`/`jsonlite` to emit plot data as JSON.
- Endpoint: `GET /calculators/stats/plot/{plot_type}` returning JSON plot spec.
- Frontend renders via a lightweight plotting lib (recharts/plotly.js).

---

## Tier 4 — Integration architecture (keep disciplined)

**Goal:** R stays an optional, server-side statistical engine with clean Python fallback.

1. **Graceful degradation:** Every `r_stats.py` function checks `R_AVAILABLE` first, wraps R calls in try/except, returns Python fallback. Already done — preserve.
2. **Small R calls only:** rpy2 marshaling is slow for bulk data. Pass scalars/small vectors to R; never ship full drop tables or item lists. Aggregated inputs in, small result out.
3. **Server-side only:** R stays in backend (`app/services/r_stats.py`). Frontend calculator port (`calculators.ts`, `museum.ts`) remains pure TypeScript — no R dependency there.
4. **Optional dependency:** `rpy2` in `requirements.txt`; Dockerfile installs via apt + pip with `RPY2_CFFI_MODE=ABI`. Project must run (tests pass, endpoints degrade) without R installed.
5. **Bridge centralization:** All R invocation funnels through `app/services/r_stats.py`. No inline `ro.r["source"]` or `ro.globalenv` calls elsewhere.

---

## Implementation order (recommended)

| Phase | Tier | Work | Files |
|---|---|---|---|
| P0 | 1 | Install R + rpy2; verify existing 6 endpoints return `r_used: true` | Dockerfile, requirements.txt, tests |
| P1 | 1 | Add tests for all 6 stats endpoints (R path + fallback parity) | tests/test_r_stats.py |
| P2 | 2 | Continuous luck-cap optimization via `optim()` | R/luck_cap_optimization.R, r_stats.py, schemas, api |
| P3 | 2 | Fit pct_ores_modified curve from data (mgcv/nls) | R/modifier_fraction_curve.R, calculators.py, api |
| P4 | 3 | Hierarchical modifier drop model | R/hierarchical_modifier.R, r_stats.py, schemas, api |
| P5 | 3 | Survival analysis for quests | R/quest_survival.R, r_stats.py, schemas, api |
| P6 | 3 | EV frontier / Pareto optimization | R/ev_frontier.R, r_stats.py, schemas, api |
| P7 | 3 | ggplot2 plot endpoints | R/plots.R, api |
| P8 | 4 | Audit: no inline R calls outside r_stats.py; docs | r_stats.py, README/ROADMAP |

---

## Validation
- `pytest tests/ -v` passes (R path + fallback).
- `ruff check app/` passes.
- All 6 existing stats endpoints return `r_used: true` once R installed; identical to fallback when R absent.
- New endpoints return correct shapes and `r_used` flag.

---
## Tier 4 — Integration discipline (complete)

### Audit findings
- **Centralization:** All `ro.globalenv` / `ro.r["source"]` calls are confined to `app/services/r_stats.py`. `app/api/calculators.py` and `app/services/calculators.py` only import from `r_stats` — no inline R calls elsewhere.
- **Server-side only:** Frontend (`frontend/`) has zero R references; calculator math remains pure TypeScript (`calculators.ts`, `museum.ts`).
- **Small calls only:** Every R function accepts scalars/small vectors (observed counts, query points, candidate builds). No bulk drop tables or full item lists are marshaled to R.
- **Optional dependency:** `rpy2==3.5.14` in `requirements.txt`; Dockerfile now installs `r-base` so `rpy2` has the R shared library. The `r_stats.py` import is wrapped in `try/except` setting `R_AVAILABLE = False`, so the project runs (tests pass, endpoints degrade) with or without R installed.

### Verification
- Fallback parity tested via `patch("app.services.r_stats.R_AVAILABLE", False)` for every bridge function — all return deterministic empty/deterministic results.
- `ruff check app/ tests/` clean; full suite 204 passed.

