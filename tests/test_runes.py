"""Tests for runes parser using live wiki fixtures."""

from pathlib import Path

from scrapers.runes import parse_runes

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "Runes.wiki"


def test_runes_parser_returns_items():
    """Runes parser should parse runes from the wikitable."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_runes(wikitext)

    # Should have around 20+ runes
    assert len(items) >= 15, f"Expected at least 15 runes, got {len(items)}"


def test_runes_have_required_fields():
    """Every rune item must have id, type, name, slug, data, image_url."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_runes(wikitext)

    for item in items:
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item
        assert item["type"] == "rune"


def test_runes_data_structure():
    """Rune data dict should contain description, location, icon, color."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_runes(wikitext)

    for item in items:
        data = item["data"]
        assert "description" in data
        assert "location" in data
        assert "icon" in data
        assert "color" in data
        assert isinstance(data["description"], str)
        assert isinstance(data["location"], str)


def test_runes_slug_is_unique():
    """All rune slugs should be unique."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_runes(wikitext)

    slugs = [item["slug"] for item in items]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found"


def test_known_rune_parsed():
    """A specific known rune (e.g., Abyssal) should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_runes(wikitext)

    rune_names = [i["name"] for i in items]
    assert "Abyssal" in rune_names, "Expected Abyssal in parsed results"

    abyssal = next(i for i in items if i["name"] == "Abyssal")
    assert "night" in abyssal["data"]["description"].lower()
    assert "Abyssal Depth" in abyssal["data"]["location"]
    assert abyssal["data"]["color"] == "6A5ACD"
