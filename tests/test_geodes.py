"""Tests for geodes parser using live wiki fixtures."""

from pathlib import Path

from scrapers.geodes import parse_geodes

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "Geodes.wiki"


def test_geodes_parser_returns_correct_count():
    """Geodes parser should parse all geode variants from fixture."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_geodes(wikitext)

    # Should have around 35+ geode variants
    assert len(items) >= 30, f"Expected at least 30 geodes, got {len(items)}"


def test_geodes_have_required_fields():
    """Every geode item must have id, type, name, slug, data, image_url."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_geodes(wikitext)

    for item in items:
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item
        assert item["type"] == "geode"


def test_geodes_data_structure():
    """Geode data dict should contain location and description."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_geodes(wikitext)

    for item in items:
        data = item["data"]
        assert "location" in data
        assert "description" in data
        assert isinstance(data["location"], str)
        assert len(data["location"]) > 0


def test_geodes_slug_is_unique():
    """All geode slugs should be unique."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_geodes(wikitext)

    slugs = [item["slug"] for item in items]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found"


def test_known_geode_parsed():
    """A specific known geode (e.g., Rubble Creek Geode) should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_geodes(wikitext)

    geode_names = [i["name"] for i in items]
    assert "Rubble Creek Geode" in geode_names, "Expected Rubble Creek Geode in parsed results"

    rubble = next(i for i in items if i["name"] == "Rubble Creek Geode")
    assert rubble["data"]["location"] == "Rubble Creek Sands"

    # Check geothermal-only geode
    void_geode = next((i for i in items if i["name"] == "The Void Geode"), None)
    assert void_geode is not None, "Expected The Void Geode"
    assert void_geode["data"].get("requires_geothermal") is True


def test_one_geode_per_location():
    """There is exactly one geode type per location."""
    items = parse_geodes(FIXTURE_PATH.read_text())

    locations = [item["data"]["location"] for item in items]
    assert len(locations) == len(set(locations)), "More than one geode per location"
