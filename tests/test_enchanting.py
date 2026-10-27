"""Tests for enchanting parser using live wiki fixtures."""

from pathlib import Path

from scrapers.enchanting import parse_enchanting

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "Enchanting.wiki"


def test_enchanting_parser_returns_items():
    """Enchanting parser should parse enchantments from both Pans and Shovels tabs."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_enchanting(wikitext)

    # Should have pan enchantments (23) + shovel enchantments (15) = 38 total
    assert len(items) == 38, f"Expected 38 enchantments, got {len(items)}"


def test_enchanting_have_required_fields():
    """Every enchantment item must have id, type, name, slug, data, image_url."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_enchanting(wikitext)

    for item in items:
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item
        assert item["type"] == "enchantment"


def test_enchanting_data_structure():
    """Enchantment data dict should contain all expected fields."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_enchanting(wikitext)

    for item in items:
        data = item["data"]
        assert "applies_to" in data
        assert "effects" in data
        assert "source" in data
        assert "rarity" in data
        assert data["applies_to"] in ("pan", "shovel")
        assert data["rarity"] in ("common", "uncommon", "rare", "mythic", "unknown")


def test_enchanting_slug_is_unique():
    """All enchantment slugs should be unique."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_enchanting(wikitext)

    slugs = [item["slug"] for item in items]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found"


def test_pan_enchantments_parsed():
    """Pan enchantments should have correct applies_to and chances."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_enchanting(wikitext)

    pan_items = [i for i in items if i["data"]["applies_to"] == "pan"]
    assert len(pan_items) >= 20, f"Expected at least 20 pan enchantments, got {len(pan_items)}"

    # Check a known pan enchantment
    forceful = next((i for i in pan_items if i["name"] == "Forceful"), None)
    assert forceful is not None, "Expected Forceful pan enchantment"
    assert forceful["data"]["aurorite_chance"] == "20%"
    assert forceful["data"]["aetherite_chance"] == "0%"
    assert forceful["data"]["aetherium_chance"] == "0%"
    assert forceful["data"]["rarity"] == "common"


def test_shovel_enchantments_parsed():
    """Shovel enchantments should have correct applies_to and chances."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_enchanting(wikitext)

    shovel_items = [i for i in items if i["data"]["applies_to"] == "shovel"]
    assert len(shovel_items) >= 15, (
        f"Expected at least 15 shovel enchantments, got {len(shovel_items)}"
    )

    # Check a known shovel enchantment
    crystal_touch = next((i for i in shovel_items if i["name"] == "Crystal Touch"), None)
    assert crystal_touch is not None, "Expected Crystal Touch shovel enchantment"
    assert crystal_touch["data"]["aetherite_chance"] == "0%"
    assert crystal_touch["data"]["aetherium_chance"] == "8.40%"
    assert crystal_touch["data"]["sol_chance"] == "Locked"
    assert crystal_touch["data"]["rarity"] == "common"
