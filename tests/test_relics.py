"""Tests for relics parser using live wiki fixtures."""

from pathlib import Path

from scrapers.relics import parse_relics

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "Relics.wiki"


def test_relics_parser_returns_items():
    """Relics parser should parse relics from tabber sections."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_relics(wikitext)

    # Should have multiple relics (around 15+)
    assert len(items) >= 10, f"Expected at least 10 relics, got {len(items)}"


def test_relics_have_required_fields():
    """Every relic item must have id, type, name, slug, data, image_url."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_relics(wikitext)

    for item in items:
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item
        assert item["type"] == "relic"


def test_relics_data_structure():
    """Relic data dict should contain description, obtainment, usage, image."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_relics(wikitext)

    for item in items:
        data = item["data"]
        assert "description" in data
        assert "obtainment" in data
        assert "usage" in data
        assert "image" in data
        assert isinstance(data["description"], str)
        assert isinstance(data["obtainment"], str)
        assert isinstance(data["usage"], str)


def test_relics_slug_is_unique():
    """All relic slugs should be unique."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_relics(wikitext)

    slugs = [item["slug"] for item in items]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found"


def test_known_relic_parsed():
    """A specific known relic (e.g., Cosmic Resonator) should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_relics(wikitext)

    relic_names = [i["name"] for i in items]
    assert "Cosmic Resonator" in relic_names, "Expected Cosmic Resonator in parsed results"

    cosmic = next(i for i in items if i["name"] == "Cosmic Resonator")
    assert "Geode Shower" in cosmic["data"]["usage"] or "geode" in cosmic["data"]["usage"].lower()
    assert len(cosmic["data"]["obtainment"]) > 0
