"""Tests for traveling merchant parser using live wiki fixtures."""

from pathlib import Path

from scrapers.traveling_merchant import parse_traveling_merchant

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "Traveling_Merchant.wiki"


def test_traveling_merchant_parser_returns_items():
    """Traveling Merchant parser should parse items from the stock table."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_traveling_merchant(wikitext)

    # Should have multiple items (around 20+)
    assert len(items) >= 15, f"Expected at least 15 merchant items, got {len(items)}"


def test_traveling_merchant_have_required_fields():
    """Every merchant item must have id, type, name, slug, data, image_url."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_traveling_merchant(wikitext)

    for item in items:
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item
        assert item["type"] in {"merchant_item", "enchant_book"}


def test_traveling_merchant_classifies_known_categories():
    """Enchant books are their own category; everything else is a listing.

    Potions are not classified here: the Potions wiki page is their canonical
    source, so the merchant row is a generic listing that reconciliation
    merges into the potion.
    """
    items = parse_traveling_merchant(FIXTURE_PATH.read_text())

    by_name = {item["name"]: item for item in items}
    assert by_name["Blessed Enchant Book"]["type"] == "enchant_book"
    assert by_name["Blitz Potion"]["type"] == "merchant_item"
    assert by_name["Cosmic Resonator"]["type"] == "merchant_item"


def test_traveling_merchant_data_structure():
    """Merchant item data dict should contain all expected fields."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_traveling_merchant(wikitext)

    for item in items:
        data = item["data"]
        assert "chance_percent" in data
        assert "price_cash" in data
        assert "price_shards" in data
        assert "stock" in data
        assert isinstance(data["chance_percent"], float)
        assert isinstance(data["price_cash"], float)
        assert isinstance(data["price_shards"], int)
        assert isinstance(data["stock"], int)


def test_traveling_merchant_slug_is_unique():
    """All merchant item slugs should be unique."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_traveling_merchant(wikitext)

    slugs = [item["slug"] for item in items]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found"


def test_known_merchant_item_parsed():
    """A specific known item (e.g., Traveler's Backpack) should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_traveling_merchant(wikitext)

    item_names = [i["name"] for i in items]
    assert "Traveler's Backpack" in item_names, "Expected Traveler's Backpack in parsed results"

    backpack = next(i for i in items if i["name"] == "Traveler's Backpack")
    assert backpack["data"]["price_cash"] == 1000000000.0
    assert backpack["data"]["price_shards"] == 500
    assert backpack["data"]["stock"] == 10
    assert abs(backpack["data"]["chance_percent"] - 11.0) < 0.1
