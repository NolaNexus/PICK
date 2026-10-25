"""Tests for mastery parser using live wiki fixtures."""

from pathlib import Path

from scrapers.mastery import parse_mastery

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "Mastery.wiki"


def test_mastery_parser_returns_items():
    """Mastery parser should parse mastery quests from all location tabs."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_mastery(wikitext)

    # Should have many quests across all locations
    assert len(items) >= 50, f"Expected at least 50 mastery quests, got {len(items)}"


def test_mastery_have_required_fields():
    """Every mastery item must have id, type, name, slug, data, image_url."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_mastery(wikitext)

    for item in items:
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item
        assert item["type"] == "mastery"


def test_mastery_data_structure():
    """Mastery data dict should contain location, boost_type, description, steps, rewards."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_mastery(wikitext)

    for item in items:
        data = item["data"]
        assert "location" in data
        assert "boost_type" in data
        assert "description" in data
        assert "steps" in data
        assert "rewards" in data
        assert isinstance(data["steps"], list)
        assert isinstance(data["location"], str)
        assert len(data["location"]) > 0


def test_mastery_slug_is_unique():
    """All mastery slugs should be unique."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_mastery(wikitext)

    slugs = [item["slug"] for item in items]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found"


def test_known_mastery_parsed():
    """Specific known mastery quests should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_mastery(wikitext)

    quest_names = [i["name"] for i in items]

    # Check for quests from Rubble Creek
    assert "Rubble Creek Mastery: 1" in quest_names
    assert "Rubble Creek Mastery: Complete" in quest_names

    # Check Getting Started! equivalent
    getting_started = next(i for i in items if i["name"] == "Rubble Creek Mastery: 1")
    assert getting_started["data"]["location"] == "Rubble Creek"
    assert "Rubble Creek Luck" in getting_started["data"]["boost_type"]
    # Description is empty (no QuestSub field in fixture)
    assert getting_started["data"]["description"] == ""
    assert len(getting_started["data"]["steps"]) == 2
    assert "1,000" in getting_started["data"]["rewards"]

    # Check Rubble Creek Mastery: Complete
    rcc = next(i for i in items if i["name"] == "Rubble Creek Mastery: Complete")
    assert rcc["data"]["location"] == "Rubble Creek"
    # Complete quest has no rewards field, but has step with 1.20
    assert "1.20" in rcc["data"]["steps"][0]

    # Check a quest from Fortune River
    fr1 = next(i for i in items if i["name"] == "Fortune River Mastery: 1")
    assert fr1["data"]["location"] == "Fortune River"
    assert "Fortune River Luck" in fr1["data"]["boost_type"]
    assert "Rare materials" in " ".join(fr1["data"]["steps"])

    # Check Meteor Valley mastery (has 5 levels + complete)
    meteor_quests = [i for i in items if "Meteor Valley" in i["data"]["location"]]
    assert len(meteor_quests) >= 6  # 5 levels + complete

    # Check title rewards are captured
    caldera_5 = next(i for i in items if i["name"] == "Caldera Park Mastery: 5")
    assert "Volcanic Lord" in caldera_5["data"]["rewards"]
    assert "1.25" in caldera_5["data"]["rewards"]
