"""Tests for the shared stat modifier schema."""

from scrapers.stats import (
    parse_equipment_stats,
    parse_modifier,
    parse_modifier_list,
    parse_multiplier,
    parse_range,
)


class TestParseRange:
    def test_single_value(self):
        assert parse_range("5") == (5.0, 5.0)

    def test_en_dash_range(self):
        assert parse_range("0.3 – 0.8") == (0.3, 0.8)

    def test_hyphen_range(self):
        assert parse_range("0 - 5") == (0.0, 5.0)

    def test_reversed_range_is_ordered(self):
        assert parse_range("5 – 0") == (0.0, 5.0)

    def test_percentage(self):
        assert parse_range("30%") == (30.0, 30.0)

    def test_unparseable(self):
        assert parse_range("none") == (None, None)
        assert parse_range("") == (None, None)


class TestParseModifier:
    def test_flat_stat(self):
        modifier = parse_modifier("+50 Luck")
        assert modifier == {"stat": "Luck", "amount": 50.0, "unit": "flat"}

    def test_percent_stat(self):
        modifier = parse_modifier("+20% Dig Speed")
        assert modifier == {"stat": "Dig Speed", "amount": 20.0, "unit": "percent"}

    def test_multiplier_stat(self):
        modifier = parse_modifier("+1.5x Capacity")
        assert modifier == {"stat": "Capacity", "amount": 1.5, "unit": "multiplier"}

    def test_negative_stat_is_a_penalty(self):
        modifier = parse_modifier("-10% Shake Speed")
        assert modifier is not None
        assert modifier["amount"] == -10.0

    def test_unknown_stat_is_not_emitted(self):
        assert parse_modifier("+50 Wibble") is None

    def test_prose_without_a_number_is_not_emitted(self):
        assert parse_modifier("increases your digging power") is None

    def test_known_stat_with_value(self):
        modifier = parse_modifier("0.3 – 0.8", stat="Luck")
        assert modifier is not None
        assert modifier["stat"] == "Luck"
        assert modifier["amount"] == 0.3
        assert modifier["amount_max"] == 0.8

    def test_short_stat_names_are_recognised(self):
        modifier = parse_modifier("5", stat="Dig Str")
        assert modifier is not None
        assert modifier["stat"] == "Dig Strength"


class TestParseModifierList:
    def test_multiple_stats(self):
        modifiers = parse_modifier_list("+20% Dig Speed, +60% Shake Speed")
        assert [m["stat"] for m in modifiers] == ["Dig Speed", "Shake Speed"]

    def test_duplicates_are_dropped(self):
        modifiers = parse_modifier_list("+20% Luck, +20% Luck")
        assert len(modifiers) == 1

    def test_prose_phrase(self):
        modifiers = parse_modifier_list("Gain 20% more luck during the night")
        assert len(modifiers) == 1
        assert modifiers[0]["stat"] == "Luck"
        assert modifiers[0]["amount"] == 20.0
        assert modifiers[0]["unit"] == "percent"

    def test_condition_is_captured(self):
        modifiers = parse_modifier_list("+20% Luck during the night")
        assert modifiers[0].get("condition") == "during the night"

    def test_empty_text(self):
        assert parse_modifier_list("") == []
        assert parse_modifier_list("None") == []


class TestParseEquipmentStats:
    def test_stat_and_value_pairs(self):
        modifiers = parse_equipment_stats(
            {"stat1": "Luck", "val1": "0.3 – 0.8", "stat2": "Capacity", "val2": "0 – 5"}
        )
        assert len(modifiers) == 2
        assert modifiers[0]["stat"] == "Luck"
        assert modifiers[0]["amount"] == 0.3
        assert modifiers[0]["amount_max"] == 0.8
        assert modifiers[1]["stat"] == "Capacity"

    def test_stage_six_variant_is_marked(self):
        modifiers = parse_equipment_stats(
            {"stat1": "Luck", "val1": "0.3 – 0.8", "s6val1": "0.3 – 0.9"}
        )
        assert len(modifiers) == 2
        assert modifiers[1]["stage"] == 6
        assert modifiers[1]["amount_max"] == 0.9

    def test_no_stats(self):
        assert parse_equipment_stats({"slot": "pan"}) == []


class TestParseMultiplier:
    def test_multiplier(self):
        modifier = parse_multiplier("0.13×", "Luck")
        assert modifier == {"stat": "Luck", "amount": 0.13, "unit": "multiplier"}

    def test_ascii_x(self):
        modifier = parse_multiplier("1.05x", "Luck")
        assert modifier is not None
        assert modifier["amount"] == 1.05

    def test_unknown_stat(self):
        assert parse_multiplier("1.05x", "Wibble") is None

    def test_no_multiplier(self):
        assert parse_multiplier("none", "Luck") is None
