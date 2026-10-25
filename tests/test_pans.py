"""Tests for pans parser using live wiki fixtures."""

from pathlib import Path

from scrapers.pans import parse_pans

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "pans.wiki"


def test_pans_parser_returns_correct_count():
    """Pans parser should parse exactly 23 pans from fixture."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_pans(wikitext)

    assert len(items) == 23, f"Expected 23 pans, got {len(items)}"


def test_pans_have_required_fields():
    """Every pan item must have id, type, name, slug, data, image_url."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_pans(wikitext)

    for item in items:
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item
        assert item["type"] == "pan"


def test_pans_data_structure():
    """Pan data dict should contain all expected fields."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_pans(wikitext)

    for item in items:
        data = item["data"]
        assert "image" in data
        assert "description" in data
        assert "price" in data
        assert "luck" in data
        assert "capacity" in data
        assert "strength" in data
        assert "speed" in data
        assert "location" in data
        assert isinstance(data["luck"], float)
        assert isinstance(data["capacity"], float)
        assert isinstance(data["strength"], float)
        assert isinstance(data["speed"], float)


def test_pans_slug_is_unique():
    """All pan slugs should be unique."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_pans(wikitext)

    slugs = [item["slug"] for item in items]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found"


def test_known_pan_parsed():
    """A specific known pan (e.g., Rusty Pan) should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_pans(wikitext)

    pan_names = [i["name"] for i in items]
    assert "Rusty Pan" in pan_names, "Expected Rusty Pan in parsed results"
