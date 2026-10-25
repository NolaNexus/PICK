"""Tests for museum parser using live wiki fixtures."""

from pathlib import Path

from scrapers.museum import parse_museum

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "Museum.wiki"


def test_museum_parser_returns_items():
    """Museum parser should parse displays, ore bonuses, and static info."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_museum(wikitext)

    # Should have displays (8 rarities) + many ore bonuses + 1 info item
    assert len(items) >= 100, f"Expected at least 100 items, got {len(items)}"


def test_museum_have_required_fields():
    """Every museum item must have id, type, name, slug, data, image_url."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_museum(wikitext)

    for item in items:
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item


def test_museum_data_structure():
    """Museum data dict should contain relevant fields."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_museum(wikitext)

    for item in items:
        data = item["data"]
        assert isinstance(data, dict)


def test_museum_slug_is_unique():
    """All museum slugs should be unique."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_museum(wikitext)

    slugs = [item["slug"] for item in items]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found"


def test_displays_parsed():
    """Display rarities should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_museum(wikitext)

    displays = [i for i in items if i["type"] == "museum_display"]
    # There are 7 rarities in the table (Common, Uncommon, Rare, Epic, Legendary, Mythic, Exotic)
    assert len(displays) == 7, f"Expected 7 display rarities, got {len(displays)}"

    display_rarities = [d["data"]["rarity"] for d in displays]
    expected_rarities = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic", "Exotic"]
    for r in expected_rarities:
        assert r in display_rarities, f"Expected {r} display"

    # Check Common display
    common = next(d for d in displays if d["data"]["rarity"] == "Common")
    assert common["data"]["free_displays"] == 1
    assert common["data"]["locked_displays"] == 2
    assert "1,000,000" in common["data"]["money_price"]
    assert "400" in common["data"]["shards_price"]
    assert common["data"]["total_displays"] == 3

    # Check Exotic display (special case)
    exotic = next(d for d in displays if d["data"]["rarity"] == "Exotic")
    assert exotic["data"]["free_displays"] == 0
    assert exotic["data"]["locked_displays"] == 1
    assert "N/A" in exotic["data"]["money_price"]
    assert "10,000" in exotic["data"]["shards_price"]
    assert exotic["data"]["total_displays"] == 1


def test_ore_bonuses_parsed():
    """Ore bonuses should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_museum(wikitext)

    ore_bonuses = [i for i in items if i["type"] == "museum_ore"]
    assert len(ore_bonuses) >= 80, f"Expected at least 80 ore bonuses, got {len(ore_bonuses)}"

    # Check specific ores
    ore_names = [o["name"] for o in ore_bonuses]
    assert "Amethyst" in ore_names
    assert "Gold" in ore_names
    assert "Coral" in ore_names
    assert "Emerald" in ore_names
    assert "Aetherite" in ore_names
    assert "Mythril" in ore_names

    # Check Gold ore details
    gold = next(o for o in ore_bonuses if o["name"] == "Gold")
    assert gold["data"]["rarity"] == "Common Ores"
    assert gold["data"]["min_kg"] == 40
    assert gold["data"]["bonus_stat"] == "Sell Boost"
    assert "0.05" in gold["data"]["max_boost"]

    # Check Aetherite details
    aetherite = next(o for o in ore_bonuses if o["name"] == "Aetherite")
    assert aetherite["data"]["rarity"] == "Legendary Ores"
    assert aetherite["data"]["min_kg"] == 20
    assert aetherite["data"]["bonus_stat"] == "Dig Speed"
    assert "0.3" in aetherite["data"]["max_boost"]


def test_museum_info_item():
    """Static museum info item should be present."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_museum(wikitext)

    info = next((i for i in items if i["slug"] == "museum"), None)
    assert info is not None, "Expected museum info item"
    assert info["type"] == "museum_info"
    assert "Caldera Park" in info["data"]["location"]
    assert "Receptionist" in info["data"]["staff"]
    assert "Vault" in info["data"]["extras"]
    assert len(info["data"]["how_it_works"]) == 3
