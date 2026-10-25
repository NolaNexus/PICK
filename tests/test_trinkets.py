"""Tests for trinkets parser using live wiki fixtures."""

from pathlib import Path

from scrapers.trinkets import parse_trinkets

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "Trinkets.wiki"


def test_trinkets_parser_returns_items():
    """Trinkets parser should parse all trinkets from the wikitable."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_trinkets(wikitext)

    # Should have 5 trinkets
    assert len(items) == 5, f"Expected 5 trinkets, got {len(items)}"


def test_trinkets_have_required_fields():
    """Every trinket item must have id, type, name, slug, data, image_url."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_trinkets(wikitext)

    for item in items:
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item
        assert item["type"] == "trinket"


def test_trinkets_data_structure():
    """Trinket data dict should contain perk, obtainment, location, color."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_trinkets(wikitext)

    for item in items:
        data = item["data"]
        assert "perk" in data
        assert "obtainment" in data
        assert "location" in data
        assert "color" in data


def test_trinkets_slug_is_unique():
    """All trinket slugs should be unique."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_trinkets(wikitext)

    slugs = [item["slug"] for item in items]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found"


def test_known_trinket_parsed():
    """A specific known trinket should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_trinkets(wikitext)

    trinket_names = [i["name"] for i in items]
    assert "Beach Umbrella" in trinket_names, "Expected Beach Umbrella"

    beach = next(i for i in items if i["name"] == "Beach Umbrella")
    assert beach["data"]["color"] == "#EC722C"
    assert "luck" in beach["data"]["perk"].lower()
    assert "Sand Dollars" in beach["data"]["obtainment"]
    assert "Seashell Isle" in beach["data"]["location"]

    duplicator = next(i for i in items if i["name"] == "Duplicator")
    assert duplicator["data"]["color"] == "#5fd2ff"
    assert "Mythic" in duplicator["data"]["perk"]
    assert "Crafting_Mastery" in duplicator["data"]["obtainment"]
