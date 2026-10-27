"""Tests for the Treasure Map parser using the live wiki fixture."""

from pathlib import Path

from scrapers.treasure_map import parse_treasure_maps

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "Treasure_Map.wiki"


def test_treasure_maps_are_per_location():
    """One map row per map type, all unique."""
    maps = parse_treasure_maps(FIXTURE_PATH.read_text())

    assert len(maps) == 8
    assert len({m["slug"] for m in maps}) == len(maps)
    assert all(m["type"] == "treasure_map" for m in maps)


def test_treasure_map_fields():
    """Maps carry their location and drop/inventory rules."""
    maps = parse_treasure_maps(FIXTURE_PATH.read_text())
    by_location = {m["data"]["location"]: m for m in maps}

    fortune = by_location["Fortune River"]
    assert fortune["name"] == "Fortune River Treasure Map"
    assert fortune["data"]["base_drop_chance_percent"] == 0.2
    assert fortune["data"]["drop_chance_scales_inversely_with_digspeed"] is True
    assert fortune["data"]["max_inventory"] == 5
    assert fortune["data"]["max_inventory_with_treasure_hunter"] == 10


def test_treasure_map_locations_match_page():
    """All eight documented map types are parsed."""
    maps = parse_treasure_maps(FIXTURE_PATH.read_text())
    locations = {m["data"]["location"] for m in maps}

    assert locations == {
        "Fortune River",
        "Fortune River Delta",
        "Sunset Beach",
        "Volcanic Sands",
        "Windswept Beach",
        "Frostbite River",
        "Rotwood Swamp",
        "Starfall River",
    }
