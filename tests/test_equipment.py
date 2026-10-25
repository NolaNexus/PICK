"""Tests for equipment parser using live wiki fixtures."""

from pathlib import Path

from scrapers.equipment import parse_equipment

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "Equipment.wiki"


def test_equipment_parser_returns_correct_count():
    """Equipment parser should parse exactly 68 equipment items from fixture."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_equipment(wikitext)

    assert len(items) == 68, f"Expected 68 equipment items, got {len(items)}"


def test_equipment_have_required_fields():
    """Every equipment item must have id, type, name, slug, data, image_url."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_equipment(wikitext)

    for item in items:
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item
        assert item["type"] == "equipment"


def test_equipment_data_structure():
    """Equipment data dict should contain all expected fields."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_equipment(wikitext)

    for item in items:
        data = item["data"]
        assert "image" in data
        assert "slot" in data
        assert "description" in data
        assert "recipe" in data
        assert "stats" in data
        assert "price" in data
        assert "rarity" in data


def test_equipment_slug_is_unique():
    """All equipment slugs should be unique."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_equipment(wikitext)

    slugs = [item["slug"] for item in items]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found"


def test_equipment_has_rarity_tiers():
    """Equipment items should carry a rarity tier extracted from tabber labels."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_equipment(wikitext)

    rarities = {item["data"]["rarity"] for item in items}
    assert "Common" in rarities
    assert "Uncommon" in rarities


def test_known_equipment_parsed():
    """A specific known equipment item (e.g., Gold Ring) should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_equipment(wikitext)

    equipment_names = [i["name"] for i in items]
    assert "Gold Ring" in equipment_names, "Expected Gold Ring in parsed results"
