"""Tests for the calculator statistics helper and the /calculators/stats endpoint.

These used to be R-backed. R was never installed in the container or in CI, so
the pure-Python behaviour covered here is the behaviour the site has always
served; the R code path has been removed, along with the endpoints that could
only ever return an empty result.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.services.stats import fit_modifier_distribution

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


class TestStatsEndpoints:
    def test_modifier_distribution(self):
        response = client.post(
            "/api/v1/calculators/stats/modifier-distribution",
            json={"observed_counts": {"Shiny": 100, "Pure": 50}, "effective_mb": 500},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["effective_mb"] == 500
        assert set(data["modifier_distribution"].keys()) == set(MODIFIER_NAMES)

    def test_the_removed_endpoints_are_gone(self):
        """The endpoints that could only return an empty result are removed.

        They are gone rather than answering with an empty list, so a caller
        cannot mistake "the model does not exist" for "nothing to report".
        """
        removed = [
            "/api/v1/calculators/stats/monte-carlo-ev",
            "/api/v1/calculators/stats/gear-recommendations",
            "/api/v1/calculators/stats/hunt-locations",
            "/api/v1/calculators/stats/exotic-locations",
            "/api/v1/calculators/stats/optimize-luck-cap",
            "/api/v1/calculators/stats/optimize-luck-cap-continuous",
            "/api/v1/calculators/stats/modifier-fraction",
            "/api/v1/calculators/stats/quest-survival",
            "/api/v1/calculators/stats/ev-pareto-frontier",
        ]
        for path in removed:
            response = client.post(path, json={})
            assert response.status_code == 404, path
