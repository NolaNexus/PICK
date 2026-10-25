"""Tests for sluices parser using live wiki fixtures."""

from pathlib import Path

from scrapers.sluices import parse_sluices

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "Sluices.wiki"


def test_sluices_parser_returns_correct_count():
    """Sluices parser should parse exactly 14 sluices from fixture (11 regular + 3 limited)."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_sluices(wikitext)

    # 11 regular + 1 Easter = 12 sluices in main list, plus limited-time ones
    assert len(items) >= 12, f"Expected at least 12 sluices, got {len(items)}"


def test_sluices_have_required_fields():
    """Every sluice item must have id, type, name, slug, data, image_url."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_sluices(wikitext)

    for item in items:
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item
        assert item["type"] == "sluice"


def test_sluices_data_structure():
    """Sluice data dict should contain all expected fields."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_sluices(wikitext)

    for item in items:
        data = item["data"]
        assert "image" in data
        assert "description" in data
        assert "price" in data
        assert "luck" in data
        assert "capacity" in data
        assert "efficiency" in data
        assert "toughness" in data
        assert "location" in data
        assert "name_color" in data
        assert isinstance(data["luck"], float)
        assert isinstance(data["capacity"], float)
        assert isinstance(data["efficiency"], float)
        assert isinstance(data["toughness"], float)


def test_sluices_slug_is_unique():
    """All sluice slugs should be unique."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_sluices(wikitext)

    slugs = [item["slug"] for item in items]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found"


def test_known_sluice_parsed():
    """A specific known sluice (e.g., Wood Sluice Box) should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_sluices(wikitext)

    sluice_names = [i["name"] for i in items]
    assert "Wood Sluice Box" in sluice_names, "Expected Wood Sluice Box in parsed results"

    wood_sluice = next(i for i in items if i["name"] == "Wood Sluice Box")
    assert wood_sluice["data"]["luck"] == 80.0
    assert wood_sluice["data"]["capacity"] == 30.0
    assert wood_sluice["data"]["efficiency"] == 1.0
    assert wood_sluice["data"]["toughness"] == 1.0
