"""Unit tests for calculator service functions."""

from app.services.calculators import (
    MODIFIER_BASE_DISTRIBUTION,
    calculate_best_pan,
    calculate_ev,
    calculate_modifier_odds,
    calculate_ttg,
    calculate_weight_gate,
    dig_time_per_dig,
    digs_per_pan,
    effective_modifier_boost,
    items_per_pan,
    modifier_distribution,
    modifier_luck,
    pans_per_hour,
    pct_ores_modified,
    quality_multiplier,
    shakes_per_second,
    weight_multiplier,
)
from app.services.r_stats import (
    fit_modifier_distribution,
    is_available,
    monte_carlo_ev,
)


class TestShakesPerSecond:
    """Test shake speed conversion with buggy zones."""

    def test_base_rate_100_percent(self):
        """At 100% shake speed, base rate is 0.1 shakes/sec."""
        assert shakes_per_second(100) == 0.1 * 0.4  # 0-400% zone: multiplier 0.4

    def test_400_percent_sweet_spot(self):
        """400% is a sweet spot."""
        result = shakes_per_second(400)
        assert result == 0.1 * 0.6  # 400-600% zone: multiplier 0.6

    def test_600_650_sweet_spot(self):
        """600-650% is a sweet spot."""
        assert shakes_per_second(600) == 0.1 * 0.65
        assert shakes_per_second(650) == 0.1 * 0.9  # boundary: 650-900% zone

    def test_900_950_sweet_spot(self):
        """900-950% is a sweet spot (multiplier 0.95)."""
        assert shakes_per_second(900) == 0.1 * 0.95
        assert shakes_per_second(950) == 0.1 * 0.9  # 950-1000%: buggy zone, same as 900%

    def test_1000_1700_buggy_zone(self):
        """1000-1700% is bugged - same speed as 900%."""
        assert shakes_per_second(1000) == 0.1 * 0.9
        assert shakes_per_second(1700) == 0.1 * 1.0  # boundary: 1700%+ zone

    def test_above_1700_percent(self):
        """1700%+ uses multiplier 1.0."""
        assert shakes_per_second(1700) == 0.1 * 1.0
        assert shakes_per_second(2000) == 0.1 * 1.0


class TestDigsPerPan:
    """Test digs per pan calculation."""

    def test_basic(self):
        """digs = ceil(capacity / (1.5 * dig_strength))."""
        assert digs_per_pan(30, 10) == 2  # ceil(30 / 15) = 2
        assert digs_per_pan(15, 10) == 1  # ceil(15 / 15) = 1
        assert digs_per_pan(16, 10) == 2  # ceil(16 / 15) = 2

    def test_zero_dig_strength(self):
        """Zero dig strength returns 1 dig minimum."""
        assert digs_per_pan(100, 0) == 1

    def test_negative_dig_strength(self):
        """Negative dig strength returns 1 dig minimum."""
        assert digs_per_pan(100, -5) == 1


class TestDigTimePerDig:
    """Test time per dig calculation."""

    def test_basic(self):
        """time = 143.9 * dig_speed^(-0.93)."""
        result = dig_time_per_dig(1000)
        expected = 143.9 * (1000 ** -0.93)
        assert abs(result - expected) < 0.01

    def test_zero_dig_speed(self):
        """Zero dig speed returns 1.0 second minimum."""
        assert dig_time_per_dig(0) == 1.0


class TestItemsPerPan:
    """Test items per pan calculation."""

    def test_basic(self):
        """items = sqrt(capacity) * 1.08."""
        result = items_per_pan(100)
        expected = (100 ** 0.5) * 1.08  # 10 * 1.08 = 10.8
        assert abs(result - expected) < 0.01

    def test_zero_capacity(self):
        """Zero capacity returns 0 items."""
        assert items_per_pan(0) == 0


class TestWeightMultiplier:
    """Test weight multiplier from size boost."""

    def test_basic(self):
        """weight_mult = 1 + size_boost / 100."""
        assert weight_multiplier(0) == 1.0
        assert weight_multiplier(100) == 2.0
        assert weight_multiplier(50) == 1.5


class TestModifierLuck:
    """Test modifier luck calculation."""

    def test_basic(self):
        """min(50, luck/1000) + modifier_boost/10."""
        assert modifier_luck(0, 0) == 0.0
        assert modifier_luck(1000, 0) == 1.0
        assert modifier_luck(50000, 0) == 50.0  # capped at 50
        assert modifier_luck(1000, 100) == 11.0  # 1.0 + 10.0


class TestEffectiveModifierBoost:
    """Test effective modifier boost with Job 1 vs Job 2."""

    def test_job1_solar_magnifier_doubles(self):
        """Solar Magnifier doubles for Job 1 (% ores modified)."""
        result = effective_modifier_boost(100, solar_magnifier=True, modifier_surge=False)
        assert result == 200.0

    def test_job1_modifier_surge_doubles(self):
        """Modifier Surge doubles for Job 1."""
        result = effective_modifier_boost(100, solar_magnifier=False, modifier_surge=True)
        assert result == 200.0

    def test_job1_both_double(self):
        """Both Solar Magnifier and Modifier Surge double for Job 1 (4x total)."""
        result = effective_modifier_boost(100, solar_magnifier=True, modifier_surge=True)
        assert result == 400.0

    def test_job2_solar_magnifier_no_effect(self):
        """Solar Magnifier does NOT affect Job 2 (which modifier)."""
        result = effective_modifier_boost(100, solar_magnifier=True, modifier_surge=False, for_which_modifier=True)
        assert result == 100.0

    def test_job2_modifier_surge_doubles(self):
        """Modifier Surge doubles for Job 2."""
        result = effective_modifier_boost(100, solar_magnifier=False, modifier_surge=True, for_which_modifier=True)
        assert result == 200.0


class TestPctOresModified:
    """Test percentage of ores modified curve."""

    def test_zero(self):
        assert pct_ores_modified(0) == 0.0

    def test_cap(self):
        """Caps at 99.4% near 1900 effective MB."""
        assert pct_ores_modified(1900) == 99.4
        assert pct_ores_modified(5000) == 99.4

    def test_monotonic(self):
        """Higher effective MB gives higher pct modified."""
        assert pct_ores_modified(100) < pct_ores_modified(500) < pct_ores_modified(1000)


class TestQualityMultiplier:
    """Test quality multiplier."""

    def test_manual(self):
        """Manual = 100% quality."""
        assert quality_multiplier() == 1.0

    def test_autopan(self):
        """Autopan = 51% quality."""
        assert quality_multiplier(autopan=True) == 0.51

    def test_autopan_mastered_shovel(self):
        """Autopan + mastered shovel = 100% quality."""
        assert quality_multiplier(autopan=True, mastered_shovel=True) == 1.0


class TestPansPerHour:
    """Test pans per hour calculation."""

    def test_basic(self):
        result = pans_per_hour(capacity=30, dig_strength=10, dig_speed=1000, shake_strength=1, shake_speed=1000)
        assert result > 0

    def test_zero_capacity(self):
        """Zero capacity still yields digs (min 1 dig per pan)."""
        result = pans_per_hour(capacity=0, dig_strength=10, dig_speed=1000, shake_strength=1, shake_speed=1000)
        assert result > 0


class TestCalculateTTG:
    """Test time to goal calculation."""

    def test_basic(self):
        result = calculate_ttg(
            goal_value=1000,
            location_ev_per_pan=10,
            capacity=30,
            dig_strength=10,
            dig_speed=1000,
            shake_strength=1,
            shake_speed=1000,
        )
        assert result["hours_to_goal"] > 0
        assert result["pans_per_hour"] > 0
        assert result["ev_per_hour"] > 0

    def test_zero_ev(self):
        """Zero EV per hour means infinite time."""
        result = calculate_ttg(
            goal_value=1000,
            location_ev_per_pan=0,
            capacity=30,
            dig_strength=10,
            dig_speed=1000,
            shake_strength=1,
            shake_speed=1000,
        )
        assert result["hours_to_goal"] == float("inf")


class TestCalculateModifierOdds:
    """Test modifier odds calculation."""

    def test_basic(self):
        result = calculate_modifier_odds(panel_modifier_boost=100)
        assert "effective_modifier_boost_job1" in result
        assert "effective_modifier_boost_job2" in result
        assert "pct_ores_modified" in result
        assert "modifier_distribution" in result


class TestCalculateBestPan:
    """Test best pan recommendation."""

    def test_filters_by_capacity(self):
        pans = [
            {"name": "Small Pan", "data": {"capacity": 5, "dig_strength": 1, "shake_strength": 1, "shake_speed": 1000, "luck": 1, "size_boost": 0, "modifier_boost": 0}},
            {"name": "Large Pan", "data": {"capacity": 50, "dig_strength": 5, "shake_strength": 2, "shake_speed": 1000, "luck": 2, "size_boost": 0, "modifier_boost": 0}},
        ]
        result = calculate_best_pan(
            pans=pans,
            dig_strength=0,
            shake_strength=0,
            shake_speed=0,
            target_capacity=30,
        )
        names = [r["pan"]["name"] for r in result["recommendations"]]
        assert "Small Pan" not in names
        assert "Large Pan" in names

    def test_returns_top_5(self):
        pans = [
            {"name": f"Pan {i}", "data": {"capacity": i * 10, "dig_strength": i, "shake_strength": i, "shake_speed": 1000, "luck": i, "size_boost": 0, "modifier_boost": 0}}
            for i in range(1, 11)
        ]
        result = calculate_best_pan(
            pans=pans,
            dig_strength=0,
            shake_strength=0,
            shake_speed=0,
        )
        assert len(result["recommendations"]) <= 5


class TestCalculateEV:
    """Test expected value calculation."""

    def test_basic(self):
        result = calculate_ev(
            location_drop_table=[],
            luck=100,
            modifier_boost=50,
            quality=1.0,
            autopan=False,
            mastered_shovel=False,
            solar_magnifier=False,
            modifier_surge=False,
        )
        assert "ev_per_pan" in result
        assert "items_per_pan" in result
        assert "quality_multiplier" in result
        assert "effective_modifier_boost" in result
        assert "modifier_distribution" in result
        assert "pct_modified" in result


class TestCalculateWeightGate:
    """Test weight gate calculation."""

    def test_meets_requirement(self):
        result = calculate_weight_gate(
            available_ores=[{"name": "Gold", "rarity": "Common", "kg": 10}],
            size_boost=0,
            ore_database={("Gold", "Common"): {"min_kg": 5}},
        )
        assert len(result) == 1
        assert result[0]["meets_requirement"] is True
        assert result[0]["effective_kg"] == 10.0

    def test_fails_requirement(self):
        result = calculate_weight_gate(
            available_ores=[{"name": "Gold", "rarity": "Common", "kg": 3}],
            size_boost=0,
            ore_database={("Gold", "Common"): {"min_kg": 5}},
        )
        assert result[0]["meets_requirement"] is False


class TestRStatsBridge:
    """Tests for the R statistical bridge (graceful fallback when R absent)."""

    def test_is_available_boolean(self):
        assert isinstance(is_available(), bool)

    def test_fit_modifier_distribution_fallback_sums(self):
        counts = {
            "Shiny": 100,
            "Pure": 50,
            "Glowing": 20,
            "Iridescent": 5,
            "Perfect": 1,
        }
        result = fit_modifier_distribution(counts, effective_mb=500)
        assert set(result.keys()) == {
            "Perfect", "Treasured", "Lunar", "Voidtorn", "Mutated", "Cosmic",
            "Iridescent", "Irradiated", "Crystalline", "Scorching", "Glowing",
            "Pure", "Shiny",
        }
        assert all(v >= 0 for v in result.values())

    def test_modifier_distribution_with_observed_counts(self):
        counts = {"Shiny": 100, "Pure": 50, "Glowing": 10}
        default = modifier_distribution(500)
        fitted = modifier_distribution(500, observed_counts=counts)
        assert set(fitted.keys()) == set(default.keys())
        assert all(v >= 0 for v in fitted.values())

    def test_modifier_distribution_zero_mb(self):
        assert modifier_distribution(0, observed_counts={"Shiny": 10}) == dict.fromkeys(MODIFIER_BASE_DISTRIBUTION, 0.0)

    def test_monte_carlo_ev_fallback(self):
        result = monte_carlo_ev(
            samples=1000,
            ev_per_pan_mean=500.0,
            ev_per_pan_sd=50.0,
            pph_mean=100.0,
            pph_sd=10.0,
        )
        assert "mean" in result
        assert "p05" in result
        assert "p95" in result
        assert result["p05"] <= result["mean"] <= result["p95"]


class TestModifierDistributionImport:
    """Ensure MODIFIER_BASE_DISTRIBUTION is importable for tests."""

    def test_base_distribution_keys(self):
        from app.services.calculators import MODIFIER_BASE_DISTRIBUTION
        assert "Shiny" in MODIFIER_BASE_DISTRIBUTION
        assert "Perfect" in MODIFIER_BASE_DISTRIBUTION

