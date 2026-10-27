"""Tests for the potions parser using the live wiki fixture."""

from pathlib import Path

from scrapers.potions import parse_potions

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "Potions.wiki"


def _items():
    return parse_potions(FIXTURE_PATH.read_text())


def test_potions_parser_returns_every_potion():
    """The Potions page lists every potion in the game."""
    items = _items()
    assert len(items) == 20, f"Expected 20 potions, got {len(items)}"


def test_potions_have_required_fields():
    """Every potion must have id, type, name, slug, data and image_url."""
    for item in _items():
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item
        assert item["type"] == "potion"


def test_potion_slugs_are_unique():
    """All potion slugs should be unique."""
    slugs = [item["slug"] for item in _items()]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found"


def test_potion_names_have_no_markup():
    """Names must be plain text."""
    for item in _items():
        assert not item["name"].startswith("|")
        assert "'''" not in item["name"]
        assert "[[" not in item["name"]


def test_every_potion_names_the_merchant_that_sells_it():
    """Each potion records where it can be bought."""
    for item in _items():
        assert item["data"]["sold_by"], f"{item['name']} has no merchant"


def test_cash_priced_potion():
    """A potion sold for cash records its cash cost."""
    items = {item["name"]: item for item in _items()}
    basic = items["Basic Luck Potion"]

    assert basic["data"]["cost_cash"] == 50000.0
    assert basic["data"]["cost_shards"] is None if "cost_shards" in basic["data"] else True
    assert basic["data"]["cost_text"] == "$50,000"
    assert basic["data"]["sold_by"] == "Fortune River Town Alchemist"


def test_shard_priced_potion():
    """A potion sold for shards records its shard cost."""
    items = {item["name"]: item for item in _items()}
    greater = items["Greater Luck Potion"]

    assert greater["data"]["cost_shards"] == 30.0
    assert "cost_cash" not in greater["data"]


def test_potion_sold_for_both_currencies():
    """A potion sold for cash and shards records both."""
    items = {item["name"]: item for item in _items()}
    instability = items["Instability Potion"]

    assert instability["data"]["cost_cash"] == 200000000.0
    assert instability["data"]["cost_shards"] == 150.0


def test_potion_duration_is_parsed():
    """The duration of a potion is read from the effect column."""
    items = {item["name"]: item for item in _items()}
    assert items["Basic Luck Potion"]["data"]["duration_min"] == 10
    assert items["Blitz Potion"]["data"]["duration_min"] == 20


def test_potion_effects_become_modifiers():
    """The effect column is turned into structured stat modifiers."""
    items = {item["name"]: item for item in _items()}
    basic = items["Basic Luck Potion"]

    modifiers = basic["data"]["modifiers"]
    assert len(modifiers) == 1
    assert modifiers[0]["stat"] == "Luck"
    assert modifiers[0]["amount"] == 5.0
    assert modifiers[0]["unit"] == "flat"
    assert modifiers[0]["duration_min"] == 10


def test_potion_with_several_effects():
    """A potion granting several stats has several modifiers."""
    items = {item["name"]: item for item in _items()}
    cosmic = items["Cosmic Potion"]

    stats = {m["stat"]: m for m in cosmic["data"]["modifiers"]}
    assert stats["Luck"]["amount"] == 250.0
    assert stats["Luck"]["unit"] == "flat"
    assert stats["Dig Speed"]["amount"] == 20.0
    assert stats["Dig Speed"]["unit"] == "percent"


def test_potion_description_and_image():
    """The description and image are read from the row."""
    items = {item["name"]: item for item in _items()}
    basic = items["Basic Luck Potion"]

    assert basic["data"]["description"] == "A simple potion that slightly increases your luck."
    assert basic["data"]["image"] == "Basic Luck Potion.png"


def test_curly_apostrophe_in_name():
    """A name with a curly apostrophe is kept as it is and slugged cleanly."""
    items = {item["slug"]: item for item in _items()}
    assert "merchants-potion" in items
    assert items["merchants-potion"]["name"] == "Merchant’s Potion"


def test_known_potions_are_present():
    """The potions from every merchant section are found."""
    names = {item["name"] for item in _items()}
    for expected in [
        "Basic Luck Potion",
        "Volcanic Luck Potion",
        "Cryonic Brew",
        "Witches Brew",
        "Cosmic Potion",
        "Traveler's Mix",
        "Merchant’s Potion",
        "Instability Potion",
        "Quake Potion",
        "Blitz Potion",
    ]:
        assert expected in names, f"Expected {expected} in the parsed potions"
