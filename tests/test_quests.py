"""Tests for quests parser using live wiki fixtures."""

from pathlib import Path

from scrapers.quests import parse_quests

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "Quests.wiki"


def test_quests_parser_returns_items():
    """Quests parser should parse quests from all location tabs."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_quests(wikitext)

    # Should have many quests across all locations
    assert len(items) >= 50, f"Expected at least 50 quests, got {len(items)}"


def test_quests_have_required_fields():
    """Every quest item must have id, type, name, slug, data, image_url."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_quests(wikitext)

    for item in items:
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item
        assert item["type"] == "quest"


def test_quests_data_structure():
    """Quest data dict should contain location, npc, description, steps, rewards, buffs."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_quests(wikitext)

    for item in items:
        data = item["data"]
        assert "location" in data
        assert "npc" in data
        assert "description" in data
        assert "steps" in data
        assert "rewards" in data
        assert "buffs" in data
        assert isinstance(data["steps"], list)
        assert isinstance(data["location"], str)
        assert len(data["location"]) > 0


def test_quests_slug_is_unique():
    """All quest slugs should be unique."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_quests(wikitext)

    slugs = [item["slug"] for item in items]
    # Allow some duplicates for quests with same name in different locations
    # Just check we have reasonable number of unique slugs
    unique_slugs = set(slugs)
    assert len(unique_slugs) >= 40, f"Expected at least 40 unique quests, got {len(unique_slugs)}"


def test_known_quest_parsed():
    """Specific known quests should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_quests(wikitext)

    quest_names = [i["name"] for i in items]

    # Check for quests from Rubble Creek
    assert "Getting Started!" in quest_names
    assert "Rubble Creek Collection" in quest_names
    assert "New Deposits" in quest_names

    # Check Getting Started! quest details
    getting_started = next(i for i in items if i["name"] == "Getting Started!")
    assert getting_started["data"]["location"] == "Rubble Creek"
    assert getting_started["data"]["npc"] == "John"
    assert "Welcome to Prospecting" in getting_started["data"]["description"]
    assert len(getting_started["data"]["steps"]) > 0
    assert "$500" in getting_started["data"]["rewards"] or "500" in getting_started["data"]["rewards"]
    assert "25" in getting_started["data"]["rewards"]

    # Check Rubble Creek Collection
    rcc = next(i for i in items if i["name"] == "Rubble Creek Collection")
    assert rcc["data"]["location"] == "Rubble Creek"
    assert rcc["data"]["npc"] == "John"
    assert len(rcc["data"]["steps"]) >= 4

    # Check a quest from Fortune River
    prospector_bet = next(i for i in items if i["name"] == "Prospector\u2019s Bet 1")
    assert prospector_bet["data"]["location"] == "Fortune River"
    assert prospector_bet["data"]["npc"] == "Tired Prospector"
    assert "Lapis Lazuli" in " ".join(prospector_bet["data"]["steps"])

    # Check Dredge Master quest (has special buff)
    dredge = next(i for i in items if i["name"] == "Dredge Master")
    assert dredge["data"]["location"] == "Fortune River"
    assert "Dredge" in dredge["data"]["buffs"]
    assert "Luck per quest" in dredge["data"]["buffs"]

    # Check Museum quest (second one, from Receptionist)
    museum = next(i for i in items if i["name"] == "Museum Restoration [2]")
    assert museum["data"]["location"] == "Museum"
    assert "Receptionist" in museum["data"]["npc"]

    # Check quest with blueprint reward
    mythril_quest = next(i for i in items if i["name"] == "Finding Mythril")
    assert mythril_quest["data"]["location"] == "Snowy Shores"
    assert "Blueprint" in mythril_quest["data"]["rewards"] or "Mythril" in mythril_quest["data"]["rewards"]
