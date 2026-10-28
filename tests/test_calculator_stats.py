"""Tests for the calculator statistics helpers and the /calculators/stats endpoints.

These used to be R-backed. R was never installed in the container or in CI, so
the pure-Python behaviour covered here is the behaviour the site has always
served; the R code path has been removed.

``r_used`` is kept in every response and is always False.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.services.stats import (
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


class TestStatsHelpers:
    def test_is_available_is_false(self):
        assert is_available() is False

    def test_fit_modifier_distribution_is_a_full_distribution(self):
        result = fit_modifier_distribution({"Shiny": 100, "Pure": 50}, effective_mb=500)
        assert set(result.keys()) == set(MODIFIER_NAMES)
        assert all(v >= 0 for v in result.values())
        assert abs(sum(result.values()) - 100.0) < 1e-4

    def test_fit_modifier_distribution_ignores_empty_counts(self):
        result = fit_modifier_distribution({}, effective_mb=500)
        assert set(result.keys()) == set(MODIFIER_NAMES)
        assert abs(sum(result.values()) - 100.0) < 1e-4

    def test_fit_modifier_distribution_ignores_all_zero_counts(self):
        result = fit_modifier_distribution(dict.fromkeys(MODIFIER_NAMES, 0), effective_mb=500)
        assert set(result.keys()) == set(MODIFIER_NAMES)
        assert abs(sum(result.values()) - 100.0) < 1e-4

    def test_monte_carlo_ev_is_a_point_estimate(self):
        result = monte_carlo_ev(
            samples=1000,
            ev_per_pan_mean=500.0,
            ev_per_pan_sd=50.0,
            pph_mean=100.0,
            pph_sd=10.0,
        )
        assert result == {"mean": 50000.0, "p05": 45000.0, "p95": 55000.0}

    def test_gear_scoring_is_empty(self):
        assert score_gear_r(gear=[{"name": "X"}]) == []

    def test_hunt_location_scoring_is_empty(self):
        assert score_hunt_locations_r(["A"], [1], [1.0], [0]) == []

    def test_exotic_location_scoring_is_empty(self):
        assert score_exotic_locations_r(["A"], [1], [10], {}, 0.0) == []

    def test_luck_cap_optimisation_is_empty(self):
        assert optimize_luck_cap_r(current_luck=1000) == []

    def test_continuous_luck_cap_optimisation_is_none(self):
        assert optimize_luck_cap_continuous_r(current_luck=5000) is None

    def test_modifier_fraction_fit_is_none(self):
        assert (
            fit_modifier_fraction_r(
                query_eff_mb=[100, 500],
                obs_eff_mb=[100, 500, 1000],
                obs_modified=[5, 30, 60],
                obs_total=[100, 100, 100],
            )
            is None
        )

    def test_quest_survival_is_none(self):
        assert quest_survival_r(n_runs=30) is None

    def test_ev_pareto_frontier_is_none(self):
        assert ev_pareto_frontier_r(candidates=[{"name": "X"}]) is None


class TestStatsEndpoints:
    def test_modifier_distribution(self):
        response = client.post(
            "/api/v1/calculators/stats/modifier-distribution",
            json={"observed_counts": {"Shiny": 100, "Pure": 50}, "effective_mb": 500},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["r_used"] is False
        assert data["effective_mb"] == 500
        assert set(data["modifier_distribution"].keys()) == set(MODIFIER_NAMES)

    def test_monte_carlo_ev(self):
        response = client.post(
            "/api/v1/calculators/stats/monte-carlo-ev",
            json={
                "samples": 1000,
                "ev_per_pan_mean": 5000.0,
                "ev_per_pan_sd": 500.0,
                "pph_mean": 120.0,
                "pph_sd": 10.0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["r_used"] is False
        assert data["p05"] <= data["mean"] <= data["p95"]

    def test_gear_recommendations_are_empty(self):
        response = client.post(
            "/api/v1/calculators/stats/gear-recommendations",
            json={"gear": [{"name": "Golden Pan", "capacity": 100}]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["r_used"] is False
        assert data["recommendations"] == []

    def test_optimize_luck_cap_falls_back(self):
        response = client.post(
            "/api/v1/calculators/stats/optimize-luck-cap",
            json={"current_luck": 5000, "modifier_boost": 200, "n_quests": 100},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["r_used"] is False
        assert data["optimal_cap"] == 5000
        assert len(data["recommendations"]) == 1
        assert data["recommendations"][0]["optimal"] is True

    def test_optimize_luck_cap_continuous_falls_back(self):
        response = client.post(
            "/api/v1/calculators/stats/optimize-luck-cap-continuous",
            json={"current_luck": 5000, "modifier_boost": 200, "lower": 0, "upper": 100000},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["r_used"] is False
        assert data["optimal_cap"] == 5000
        assert data["optimal_bonuses_per_hour"] == 0.0

    def test_modifier_fraction_has_no_curve(self):
        response = client.post(
            "/api/v1/calculators/stats/modifier-fraction",
            json={
                "query_eff_mb": [0, 250, 500],
                "obs_eff_mb": [100, 500, 1000],
                "obs_modified": [5, 30, 60],
                "obs_total": [100, 100, 100],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["r_used"] is False
        assert data["curve"] == []

    def test_quest_survival_falls_back(self):
        response = client.post(
            "/api/v1/calculators/stats/quest-survival",
            json={"n_runs": 40, "n_quests": 20, "max_time_hours": 24},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["r_used"] is False
        assert data["survival_curve"] == []
        assert data["coefficients"] == {}

    def test_ev_pareto_frontier_falls_back(self):
        response = client.post(
            "/api/v1/calculators/stats/ev-pareto-frontier",
            json={
                "candidates": [
                    {
                        "name": "Build A",
                        "ev_per_pan_mean": 5000,
                        "ev_per_pan_sd": 500,
                        "pph_mean": 100,
                        "pph_sd": 10,
                    }
                ],
                "n_samples": 3000,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["r_used"] is False
        assert data["frontier"] == []
        assert data["n_frontier"] == 0
