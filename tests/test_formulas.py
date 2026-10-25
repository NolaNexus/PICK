"""Tests for formulas parser (Stat_Systems_Guide) using live wiki fixtures."""

from pathlib import Path

from scrapers.formulas import parse_formulas

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "Stat_Systems_Guide.wiki"


def test_formulas_parser_returns_items():
    """Formulas parser should parse formulas from all tabs."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_formulas(wikitext)

    # Should have multiple formula items
    assert len(items) >= 20, f"Expected at least 20 formulas, got {len(items)}"


def test_formulas_have_required_fields():
    """Every formula item must have id, type, name, slug, data, image_url."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_formulas(wikitext)

    for item in items:
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item
        assert item["type"] == "formula"


def test_formulas_data_structure():
    """Formula data dict should contain category, formula, description, components."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_formulas(wikitext)

    for item in items:
        data = item["data"]
        assert "category" in data
        assert "formula" in data
        assert "description" in data
        assert "components" in data
        assert isinstance(data["components"], dict)


def test_formulas_slug_is_unique():
    """All formula slugs should be unique."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_formulas(wikitext)

    slugs = [item["slug"] for item in items]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found"


def test_golden_rule_parsed():
    """The Golden Rule formula should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_formulas(wikitext)

    golden_rule = next((i for i in items if i["slug"] == "golden-rule"), None)
    assert golden_rule is not None, "Expected Golden Rule formula"
    assert golden_rule["data"]["formula"] == "Total = (Base + Flats) × (1 + Boosts) × Events"
    assert "boosts add together" in golden_rule["data"]["description"].lower()
    assert "Base" in golden_rule["data"]["components"]
    assert "Flats" in golden_rule["data"]["components"]
    assert "Boosts" in golden_rule["data"]["components"]
    assert "Events" in golden_rule["data"]["components"]


def test_boost_catalogue_parsed():
    """Boost catalogue entries should be parsed."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_formulas(wikitext)

    # Should have multiple boost entries
    boost_items = [i for i in items if i["data"]["category"] == "boost"]
    assert len(boost_items) >= 5, f"Expected at least 5 boost entries, got {len(boost_items)}"

    # Check for known boosts
    boost_names = [i["name"] for i in boost_items]
    assert "Luck Totem" in boost_names
    assert "Strength Totem" in boost_names
    assert "Friendship Totem" in boost_names


def test_stat_formulas_parsed():
    """Stat-specific formulas should be parsed."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_formulas(wikitext)

    # Check for Luck formulas
    luck_items = [i for i in items if "luck" in i["data"]["category"]]
    assert len(luck_items) >= 2

    # Check for Capacity formulas
    cap_items = [i for i in items if "capacity" in i["data"]["category"]]
    assert len(cap_items) >= 1

    # Check for Dig Strength formulas
    ds_items = [i for i in items if "dig_strength" in i["data"]["category"]]
    assert len(ds_items) >= 1


def test_modifier_price_table_parsed():
    """Modifier price multiplier table should be parsed."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_formulas(wikitext)

    price_table = next((i for i in items if i["slug"] == "modifier-price-table"), None)
    assert price_table is not None, "Expected modifier price table"
    assert "modifiers" in price_table["data"]["components"]
    modifiers = price_table["data"]["components"]["modifiers"]
    assert len(modifiers) >= 10, f"Expected at least 10 modifiers, got {len(modifiers)}"

    mod_names = [m["name"] for m in modifiers]
    assert "Perfect" in mod_names
    assert "Treasured" in mod_names
    assert "Voidtorn" in mod_names
    assert "Cosmic" in mod_names


def test_museum_display_parsed():
    """Museum display formula should be parsed."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_formulas(wikitext)

    museum = next((i for i in items if i["slug"] == "museum-display-formula"), None)
    assert museum is not None, "Expected museum display formula"
    assert "rarity_scale" in museum["data"]["components"]
    assert "display = ore_base + modifier_rider" in museum["data"]["formula"]
