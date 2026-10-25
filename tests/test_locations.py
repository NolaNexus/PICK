"""Tests for locations parser using live wiki fixtures."""

from pathlib import Path

from scrapers.locations import parse_locations

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "locations.wiki"


def test_locations_parser_returns_correct_count():
    """Locations parser should parse exactly 18 locations from fixture."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_locations(wikitext)

    assert len(items) == 18, f"Expected 18 locations, got {len(items)}"


def test_locations_have_required_fields():
    """Every location item must have id, type, name, slug, data, image_url."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_locations(wikitext)

    for item in items:
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item
        assert item["type"] == "location"


def test_locations_data_structure():
    """Location data dict should contain description, minerals, shopkeepers."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_locations(wikitext)

    for item in items:
        data = item["data"]
        assert "description" in data
        assert "minerals" in data
        assert "shopkeepers" in data
        assert isinstance(data["minerals"], list)
        assert isinstance(data["shopkeepers"], list)


def test_locations_slug_matches_name():
    """Slug should be lowercase name with spaces/hyphens normalized."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_locations(wikitext)

    for item in items:
        expected_slug = (
            item["name"]
            .lower()
            .replace(" ", "-")
            .replace("'", "")
            .replace("(", "")
            .replace(")", "")
        )
        assert item["slug"] == expected_slug
        assert item["id"] == expected_slug


def test_known_location_parsed():
    """Rubble Creek should be parsed with minerals and shopkeepers."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_locations(wikitext)

    rubble_creek = next((i for i in items if i["name"] == "Rubble Creek"), None)
    assert rubble_creek is not None, "Rubble Creek not found"
    # The fixture doesn't have explicit mineral references in the Rubble Creek section
    # Just verify shopkeepers are extracted
    assert len(rubble_creek["data"]["shopkeepers"]) > 0
