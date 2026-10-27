"""Tests for the Treasure Chest parser using the live wiki fixture."""

from pathlib import Path

from scrapers.treasure_chest import parse_treasure_chests

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "Treasure_Chest.wiki"


def test_treasure_chests_are_per_location():
    """One chest row per location, all unique."""
    chests = parse_treasure_chests(FIXTURE_PATH.read_text())

    assert len(chests) == 8
    assert len({c["slug"] for c in chests}) == len(chests)
    assert all(c["type"] == "treasure_chest" for c in chests)


def test_treasure_chest_rules():
    """Chests always apply Treasured, with Size Boost but not Luck."""
    chests = parse_treasure_chests(FIXTURE_PATH.read_text())

    for chest in chests:
        data = chest["data"]
        assert data["modifier"] == "Treasured"
        assert data["size_boost_applies"] is True
        assert data["luck_applies"] is False
        assert data["obtained_from"] == "treasure_map"


def test_treasure_chest_loot_pool():
    """Loot pools keep the random ore entry and specific relics."""
    chests = parse_treasure_chests(FIXTURE_PATH.read_text())
    by_location = {c["data"]["location"]: c for c in chests}

    delta = by_location["Fortune River Delta"]
    names = [entry.get("name") for entry in delta["data"]["loot"] if entry["kind"] == "item"]
    ores = [entry for entry in delta["data"]["loot"] if entry["kind"] == "ore"]

    assert "Cosmic Resonator" in names
    assert "Rain Stone" in names
    assert len(ores) == 1
    assert ores[0]["location"] == "Fortune River Delta"
