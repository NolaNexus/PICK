"""Tests for the R statistical bridge and /calculators/stats/* API endpoints.

R + rpy2 are installed in this environment, so these tests exercise the real
R code path and assert r_used: true where applicable. Fallback parity is
verified by monkeypatching R_AVAILABLE to False.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.r_stats import (
    ev_pareto_frontier_r,
    fit_modifier_distribution,
    fit_modifier_fraction_r,
    is_available,
    monte_carlo_ev,
    optimize_luck_cap_continuous_r,
    optimize_luck_cap_r,
    quest_survival_r,
    score_exotic_locations_r,
    score_gear_r,
    score_hunt_locations_r,
)

client = TestClient(app)

MODIFIER_NAMES = [
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


class TestRStatsBridgeUnit:
    """Unit tests for all 6 r_stats bridge functions (real R path)."""

    def test_is_available_true(self):
        assert is_available() is True

    def test_fit_modifier_distribution_r_path(self):
        counts = {"Shiny": 100, "Pure": 50, "Glowing": 20, "Iridescent": 5, "Perfect": 1}
        result = fit_modifier_distribution(counts, effective_mb=500)
        assert set(result.keys()) == set(MODIFIER_NAMES)
        assert all(v >= 0 for v in result.values())
        assert abs(sum(result.values()) - 100.0) < 1e-6

    def test_fit_modifier_distribution_empty_counts_fallback(self):
        # Empty dict short-circuits to the Python fallback (non-zero base dist).
        result = fit_modifier_distribution({}, effective_mb=500)
        assert set(result.keys()) == set(MODIFIER_NAMES)
        assert all(v >= 0 for v in result.values())

    def test_fit_modifier_distribution_all_zero_counts_fallback(self):
        # All-zero counts: total <= 0, bridge returns Python fallback (non-zero base dist).
        result = fit_modifier_distribution(dict.fromkeys(MODIFIER_NAMES, 0), effective_mb=500)
        assert set(result.keys()) == set(MODIFIER_NAMES)
        assert all(v >= 0 for v in result.values())

    def test_monte_carlo_ev_r_path(self):
        result = monte_carlo_ev(
            samples=10000,
            ev_per_pan_mean=5000.0,
            ev_per_pan_sd=500.0,
            pph_mean=120.0,
            pph_sd=10.0,
        )
        assert set(result.keys()) == {"mean", "p05", "p95"}
        assert result["p05"] <= result["mean"] <= result["p95"]
        assert result["mean"] > 0

    def test_score_gear_r_path(self):
        gear = [
            {
                "name": "Golden Pan",
                "capacity": 100,
                "dig_strength": 20,
                "shake_strength": 20,
                "shake_speed": 600,
                "luck": 500,
                "size_boost": 50,
                "modifier_boost": 100,
            }
        ]
        result = score_gear_r(
            gear=gear,
            dig_strength=50,
            shake_strength=50,
            shake_speed=500,
            target_capacity=80,
            min_luck=100,
        )
        assert len(result) == 1
        assert result[0]["name"] == "Golden Pan"
        assert "score" in result[0]
        assert "pans_per_hour" in result[0]
        assert "digs_per_pan" in result[0]

    def test_score_gear_r_empty_input(self):
        assert score_gear_r(gear=[]) == []

    def test_score_hunt_locations_r_path(self):
        result = score_hunt_locations_r(
            loc_names=["LocA", "LocB"],
            loc_hunt_counts=[4, 2],
            loc_hunt_weights=[64.0, 8.0],
            loc_exotic_counts=[2, 0],
        )
        assert len(result) == 2
        assert result[0]["name"] == "LocA"
        assert result[0]["score"] > result[1]["score"]
        assert all("hunt_count" in r and "exotic_count" in r for r in result)

    def test_score_hunt_locations_r_empty(self):
        assert score_hunt_locations_r([], [], [], []) == []

    def test_score_exotic_locations_r_path(self):
        result = score_exotic_locations_r(
            loc_names=["LocA", "LocB"],
            loc_exotic_mineral_counts=[3, 1],
            loc_total_minerals=[10, 10],
            modifier_distribution={"Exotic": 8.0, "Shiny": 70.0},
            player_modifier_boost=500.0,
        )
        assert len(result) == 2
        assert result[0]["score"] > result[1]["score"]
        assert all("exotic_rate" in r and "exotic_mod_prob" in r for r in result)

    def test_score_exotic_locations_r_empty(self):
        assert score_exotic_locations_r([], [], [], {}, 0.0) == []

    def test_optimize_luck_cap_r_path(self):
        result = optimize_luck_cap_r(
            current_luck=5000,
            modifier_boost=200,
            solar_magnifier=False,
            modifier_surge=False,
            bonus_interval=10,
            n_quests=100,
            luck_caps=[0, 5000, 10000, 20000, 50000],
        )
        assert len(result) == 5
        optimal = [r for r in result if r.get("optimal") is True]
        assert len(optimal) == 1
        assert all("bonuses_per_hour" in r and "luck_cap" in r for r in result)
        assert result[0]["bonuses_per_hour"] >= result[-1]["bonuses_per_hour"]

    def test_optimize_luck_cap_r_default_caps(self):
        result = optimize_luck_cap_r(current_luck=1000, modifier_boost=0)
        assert len(result) > 0
        optimal = [r for r in result if r.get("optimal") is True]
        assert len(optimal) == 1


class TestRStatsFallbackParity:
    """When R/rpy2 is unavailable, each function must degrade gracefully."""

    def test_fit_modifier_distribution_fallback(self):
        counts = {"Shiny": 100, "Pure": 50}
        with patch("app.services.r_stats.R_AVAILABLE", False):
            result = fit_modifier_distribution(counts, effective_mb=500)
        assert set(result.keys()) == set(MODIFIER_NAMES)
        assert all(v >= 0 for v in result.values())
        assert abs(sum(result.values()) - 100.0) < 1e-6

    def test_monte_carlo_ev_fallback(self):
        with patch("app.services.r_stats.R_AVAILABLE", False):
            result = monte_carlo_ev(
                samples=1000,
                ev_per_pan_mean=500.0,
                ev_per_pan_sd=50.0,
                pph_mean=100.0,
                pph_sd=10.0,
            )
        assert set(result.keys()) == {"mean", "p05", "p95"}
        assert result["p05"] <= result["mean"] <= result["p95"]

    def test_score_gear_r_fallback_returns_empty(self):
        with patch("app.services.r_stats.R_AVAILABLE", False):
            assert score_gear_r(gear=[{"name": "X"}]) == []

    def test_score_hunt_locations_r_fallback_returns_empty(self):
        with patch("app.services.r_stats.R_AVAILABLE", False):
            assert score_hunt_locations_r(["A"], [1], [1.0], [0]) == []

    def test_score_exotic_locations_r_fallback_returns_empty(self):
        with patch("app.services.r_stats.R_AVAILABLE", False):
            assert score_exotic_locations_r(["A"], [1], [10], {}, 0.0) == []

    def test_optimize_luck_cap_r_fallback_returns_empty(self):
        with patch("app.services.r_stats.R_AVAILABLE", False):
            assert optimize_luck_cap_r(current_luck=1000) == []


class TestStatsApiEndpoints:
    """Integration tests for /api/v1/calculators/stats/* endpoints (no DB required)."""

    def test_modifier_distribution_endpoint_r_used(self):
        payload = {
            "observed_counts": {"Shiny": 100, "Pure": 50, "Glowing": 20},
            "effective_mb": 500,
        }
        response = client.post("/api/v1/calculators/stats/modifier-distribution", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["r_used"] is True
        assert data["effective_mb"] == 500
        assert set(data["modifier_distribution"].keys()) == set(MODIFIER_NAMES)

    def test_modifier_distribution_endpoint_empty_counts(self):
        response = client.post(
            "/api/v1/calculators/stats/modifier-distribution",
            json={"observed_counts": {}, "effective_mb": 0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["r_used"] is True

    def test_monte_carlo_ev_endpoint_r_used(self):
        payload = {
            "samples": 10000,
            "ev_per_pan_mean": 5000.0,
            "ev_per_pan_sd": 500.0,
            "pph_mean": 120.0,
            "pph_sd": 10.0,
        }
        response = client.post("/api/v1/calculators/stats/monte-carlo-ev", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["r_used"] is True
        assert data["p05"] <= data["mean"] <= data["p95"]

    def test_gear_recommendations_endpoint_r_used(self):
        payload = {
            "gear": [
                {
                    "name": "Golden Pan",
                    "capacity": 100,
                    "dig_strength": 20,
                    "shake_strength": 20,
                    "shake_speed": 600,
                    "luck": 500,
                    "size_boost": 50,
                    "modifier_boost": 100,
                }
            ],
            "dig_strength": 50,
            "shake_strength": 50,
            "shake_speed": 500,
        }
        response = client.post("/api/v1/calculators/stats/gear-recommendations", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["r_used"] is True
        assert len(data["recommendations"]) == 1

    def test_gear_recommendations_endpoint_empty(self):
        response = client.post(
            "/api/v1/calculators/stats/gear-recommendations",
            json={"gear": []},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["recommendations"] == []

    def test_optimize_luck_cap_endpoint_r_used(self):
        payload = {
            "current_luck": 5000,
            "modifier_boost": 200,
            "solar_magnifier": False,
            "modifier_surge": False,
            "bonus_interval": 10,
            "n_quests": 100,
            "luck_caps": [0, 5000, 10000, 20000, 50000],
        }
        response = client.post("/api/v1/calculators/stats/optimize-luck-cap", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["r_used"] is True
        assert isinstance(data["optimal_cap"], (int, float))
        assert any(r.get("optimal") is True for r in data["recommendations"])


class TestOptimizeLuckCapContinuous:
    """Tests for continuous luck-cap optimization (R's Brent search)."""

    def test_optimize_luck_cap_continuous_r_path(self):
        result = optimize_luck_cap_continuous_r(
            current_luck=5000,
            modifier_boost=200,
            solar_magnifier=False,
            modifier_surge=False,
            bonus_interval=10,
            n_quests=100,
            lower=0,
            upper=100000,
        )
        assert result is not None
        assert set(result.keys()) == {
            "optimal_cap",
            "optimal_bonuses_per_hour",
            "saturation_cap",
            "lower",
            "upper",
        }
        assert result["optimal_bonuses_per_hour"] > 0
        assert 0 <= result["saturation_cap"] <= result["upper"]
        assert result["lower"] == 0 and result["upper"] == 100000

    def test_optimize_luck_cap_continuous_r_defaults(self):
        result = optimize_luck_cap_continuous_r(current_luck=5000, modifier_boost=200)
        assert result is not None
        assert result["lower"] == 0
        assert result["upper"] == 100000
        assert result["optimal_bonuses_per_hour"] > 0

    def test_optimize_luck_cap_continuous_fallback_returns_none(self):
        with patch("app.services.r_stats.R_AVAILABLE", False):
            assert optimize_luck_cap_continuous_r(current_luck=5000) is None

    def test_optimize_luck_cap_continuous_endpoint_r_used(self):
        payload = {
            "current_luck": 5000,
            "modifier_boost": 200,
            "solar_magnifier": False,
            "modifier_surge": False,
            "bonus_interval": 10,
            "n_quests": 100,
            "lower": 0,
            "upper": 100000,
        }
        response = client.post(
            "/api/v1/calculators/stats/optimize-luck-cap-continuous", json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["r_used"] is True
        assert data["optimal_bonuses_per_hour"] > 0
        assert data["saturation_cap"] >= 0
        assert data["lower"] == 0 and data["upper"] == 100000


class TestFitModifierFraction:
    """Tests for % ores modified curve fitting (R's nls)."""

    def test_fit_modifier_fraction_r_path(self):
        result = fit_modifier_fraction_r(
            query_eff_mb=[0, 250, 500, 1000, 1500, 1900],
            obs_eff_mb=[100, 500, 1000, 1500, 1900],
            obs_modified=[5, 30, 60, 85, 95],
            obs_total=[100, 100, 100, 100, 100],
        )
        assert result is not None
        assert len(result) == 6
        eff_mbs = [p["eff_mb"] for p in result]
        pcts = [p["pct_modified"] for p in result]
        assert eff_mbs == [0.0, 250.0, 500.0, 1000.0, 1500.0, 1900.0]
        assert pcts[0] == 0.0  # eff_mb 0 -> 0% modified
        assert all(0 <= p <= 99.4 for p in pcts)
        assert pcts == sorted(pcts)  # monotonic non-decreasing

    def test_fit_modifier_fraction_r_too_few_points(self):
        result = fit_modifier_fraction_r(
            query_eff_mb=[100], obs_eff_mb=[100], obs_modified=[5], obs_total=[100]
        )
        assert result is None

    def test_fit_modifier_fraction_r_all_zero(self):
        result = fit_modifier_fraction_r(
            query_eff_mb=[100, 200],
            obs_eff_mb=[100, 200],
            obs_modified=[0, 0],
            obs_total=[100, 100],
        )
        assert result is None

    def test_fit_modifier_fraction_r_fallback_returns_none(self):
        with patch("app.services.r_stats.R_AVAILABLE", False):
            assert (
                fit_modifier_fraction_r(
                    query_eff_mb=[100, 500],
                    obs_eff_mb=[100, 500, 1000],
                    obs_modified=[5, 30, 60],
                    obs_total=[100, 100, 100],
                )
                is None
            )

    def test_modifier_fraction_endpoint_r_used(self):
        payload = {
            "query_eff_mb": [0, 250, 500, 1000, 1500, 1900],
            "obs_eff_mb": [100, 500, 1000, 1500, 1900],
            "obs_modified": [5, 30, 60, 85, 95],
            "obs_total": [100, 100, 100, 100, 100],
        }
        response = client.post("/api/v1/calculators/stats/modifier-fraction", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["r_used"] is True
        assert len(data["curve"]) == 6
        assert data["curve"][0]["eff_mb"] == 0.0
        assert data["curve"][0]["pct_modified"] == 0.0
        pcts = [p["pct_modified"] for p in data["curve"]]
        assert pcts == sorted(pcts)

    def test_modifier_fraction_endpoint_too_few_points(self):
        payload = {
            "query_eff_mb": [100],
            "obs_eff_mb": [100],
            "obs_modified": [5],
            "obs_total": [100],
        }
        response = client.post("/api/v1/calculators/stats/modifier-fraction", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["r_used"] is False
        assert data["curve"] == []


class TestQuestSurvival:
    """Tests for quest survival analysis (R's survival::coxph)."""

    def test_quest_survival_r_path(self):
        result = quest_survival_r(
            n_runs=40,
            n_quests=20,
            max_time_hours=24,
            time_points=[1, 5, 10, 24],
            luck_levels=[0, 5000],
            modifier_boost_levels=[0, 200],
        )
        assert result is not None
        assert set(result.keys()) >= {
            "coefficients",
            "hazard_ratios",
            "baseline_median_time_hours",
            "n_runs",
            "n_completed",
            "n_censored",
            "survival_curve",
            "completion_prob_within",
            "r_used",
        }
        assert result["r_used"] is True
        assert result["n_runs"] > 0
        assert isinstance(result["coefficients"], dict)
        assert isinstance(result["hazard_ratios"], dict)
        assert isinstance(result["survival_curve"], list)
        assert isinstance(result["completion_prob_within"], dict)

    def test_quest_survival_single_covariate(self):
        # Only one luck level: no varying covariates -> intercept-only model.
        result = quest_survival_r(
            n_runs=30,
            n_quests=10,
            max_time_hours=24,
            luck_levels=[5000],
            modifier_boost_levels=[200],
        )
        assert result is not None
        assert result["r_used"] is True
        assert result["coefficients"] == {} or result["coefficients"] is not None

    def test_quest_survival_fallback_returns_none(self):
        with patch("app.services.r_stats.R_AVAILABLE", False):
            assert quest_survival_r(n_runs=30) is None

    def test_quest_survival_endpoint_r_used(self):
        payload = {
            "n_runs": 40,
            "n_quests": 20,
            "max_time_hours": 24,
            "time_points": [1, 5, 10, 24],
            "luck_levels": [0, 5000],
            "modifier_boost_levels": [0, 200],
        }
        response = client.post("/api/v1/calculators/stats/quest-survival", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["r_used"] is True
        assert isinstance(data["coefficients"], dict)
        assert isinstance(data["hazard_ratios"], dict)
        assert isinstance(data["survival_curve"], list)
        assert isinstance(data["completion_prob_within"], dict)
        assert isinstance(data["baseline_median_time_hours"], (int, float))


class TestEvParetoFrontier:
    """Tests for EV / risk Pareto frontier (R's stats::rnost + dominance)."""

    def test_ev_pareto_frontier_r_path(self):
        candidates = [
            {
                "name": "Build A",
                "ev_per_pan_mean": 5000,
                "ev_per_pan_sd": 500,
                "pph_mean": 100,
                "pph_sd": 10,
            },
            {
                "name": "Build B",
                "ev_per_pan_mean": 4000,
                "ev_per_pan_sd": 200,
                "pph_mean": 150,
                "pph_sd": 20,
            },
            {
                "name": "Build C",
                "ev_per_pan_mean": 6000,
                "ev_per_pan_sd": 1500,
                "pph_mean": 80,
                "pph_sd": 40,
            },
        ]
        result = ev_pareto_frontier_r(candidates=candidates, n_samples=3000)
        assert result is not None
        assert len(result) == 3
        # Every candidate has the expected fields.
        for row in result:
            assert set(row.keys()) >= {
                "name",
                "mean_ev_hour",
                "p05_ev_hour",
                "p95_ev_hour",
                "on_frontier",
                "dominated_by",
            }
            assert isinstance(row["on_frontier"], bool)
        # At least one candidate is on the frontier.
        assert any(row["on_frontier"] for row in result)
        # Frontier candidates are not dominated.
        for row in result:
            if row["on_frontier"]:
                assert row["dominated_by"] == ""

    def test_ev_pareto_frontier_r_empty(self):
        assert ev_pareto_frontier_r(candidates=[]) == []

    def test_ev_pareto_frontier_r_fallback_returns_none(self):
        with patch("app.services.r_stats.R_AVAILABLE", False):
            assert (
                ev_pareto_frontier_r(
                    candidates=[
                        {
                            "name": "X",
                            "ev_per_pan_mean": 1000,
                            "ev_per_pan_sd": 100,
                            "pph_mean": 50,
                            "pph_sd": 5,
                        }
                    ]
                )
                is None
            )

    def test_ev_pareto_frontier_endpoint_r_used(self):
        payload = {
            "candidates": [
                {
                    "name": "Build A",
                    "ev_per_pan_mean": 5000,
                    "ev_per_pan_sd": 500,
                    "pph_mean": 100,
                    "pph_sd": 10,
                },
                {
                    "name": "Build B",
                    "ev_per_pan_mean": 4000,
                    "ev_per_pan_sd": 200,
                    "pph_mean": 150,
                    "pph_sd": 20,
                },
            ],
            "n_samples": 3000,
        }
        response = client.post("/api/v1/calculators/stats/ev-pareto-frontier", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["r_used"] is True
        assert isinstance(data["frontier"], list)
        assert isinstance(data["all_candidates"], list)
        assert data["n_frontier"] == len(data["frontier"])
        assert len(data["all_candidates"]) == 2
