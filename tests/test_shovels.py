"""Tests for shovels parser using live wiki fixtures."""

from pathlib import Path

from scrapers.shovels import parse_shovels

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "shovels.wiki"


def test_shovels_parser_returns_correct_count():
    """Shovels parser should parse exactly 24 shovels from fixture."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_shovels(wikitext)

    assert len(items) == 24, f"Expected 24 shovels, got {len(items)}"


def test_shovels_have_required_fields():
    """Every shovel item must have id, type, name, slug, data, image_url."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_shovels(wikitext)

    for item in items:
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item
        assert item["type"] == "shovel"


def test_shovels_data_structure():
    """Shovel data dict should contain all expected fields."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_shovels(wikitext)

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


def test_shovels_slug_is_unique():
    """All shovel slugs should be unique."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_shovels(wikitext)

    slugs = [item["slug"] for item in items]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found"


def test_known_shovel_parsed():
    """A specific known shovel (e.g., Rusty Shovel) should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_shovels(wikitext)

    shovel_names = [i["name"] for i in items]
    assert "Rusty Shovel" in shovel_names, "Expected Rusty Shovel in parsed results"
