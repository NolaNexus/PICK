"""Tests for modifiers parser using live wiki fixtures."""

from pathlib import Path

from scrapers.modifiers import parse_modifiers

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "Modifiers.wiki"


def test_modifiers_parser_returns_items():
    """Modifiers parser should parse all modifier sections."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_modifiers(wikitext)

    # Should have around 20+ modifiers
    assert len(items) >= 20, f"Expected at least 20 modifiers, got {len(items)}"


def test_modifiers_have_required_fields():
    """Every modifier item must have id, type, name, slug, data, image_url."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_modifiers(wikitext)

    for item in items:
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item
        assert item["type"] == "modifier"


def test_modifiers_data_structure():
    """Modifier data dict should contain all expected fields."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_modifiers(wikitext)

    for item in items:
        data = item["data"]
        assert "sell_price_multiplier" in data
        assert "color" in data
        assert "description" in data
        assert "image" in data
        assert "tools" in data
        assert "equipment" in data
        assert "location_boosts" in data
        assert "event_boosts" in data
        assert "museum_bonus" in data
        assert "chance" in data


def test_modifiers_slug_is_unique():
    """All modifier slugs should be unique."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_modifiers(wikitext)

    slugs = [item["slug"] for item in items]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found"


def test_known_modifier_parsed():
    """A specific known modifier (e.g., Perfect) should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_modifiers(wikitext)

    modifier_names = [i["name"] for i in items]
    assert "Perfect" in modifier_names, "Expected Perfect in parsed results"

    perfect = next(i for i in items if i["name"] == "Perfect")
    assert perfect["data"]["sell_price_multiplier"] == 24.0
    assert perfect["data"]["color"] == "#00ffe1"
    assert "halo" in perfect["data"]["description"].lower()
    assert perfect["data"]["image"] == "File:Modifier Perfect.png"
    assert perfect["data"]["chance"] == "0.003736% (~1 in 26764)"

    # Check Voidtorn (has special tools)
    voidtorn = next((i for i in items if i["name"] == "Voidtorn"), None)
    assert voidtorn is not None, "Expected Voidtorn"
    assert voidtorn["data"]["tools"] is not None
    assert "Galactic" in voidtorn["data"]["tools"]

    # Check event modifier (Halloween)
    ghostly = next((i for i in items if i["name"] == "Ghostly"), None)
    assert ghostly is not None, "Expected Ghostly"
    assert ghostly["data"]["event_boosts"] is not None
    assert "Halloween" in ghostly["data"]["event_boosts"]
