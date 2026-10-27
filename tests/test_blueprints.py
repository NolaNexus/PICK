"""Tests for blueprints parser using live wiki fixtures."""

from pathlib import Path

from scrapers.blueprints import parse_blueprints

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "Blueprint.wiki"


def test_blueprints_parser_returns_items():
    """Blueprints parser should parse blueprints from tabber sections."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_blueprints(wikitext)

    # Should have multiple blueprints (around 20+)
    assert len(items) >= 10, f"Expected at least 10 blueprints, got {len(items)}"


def test_blueprints_have_required_fields():
    """Every blueprint item must have id, type, name, slug, data, image_url."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_blueprints(wikitext)

    for item in items:
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item
        assert item["type"] == "blueprint"


def test_blueprints_data_structure():
    """Blueprint data dict should contain description, image, quest_giver, quest_name, quest_steps."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_blueprints(wikitext)

    for item in items:
        data = item["data"]
        assert "description" in data
        assert "image" in data
        assert "quest_giver" in data
        assert "quest_name" in data
        assert "quest_steps" in data
        assert isinstance(data["quest_steps"], list)


def test_blueprints_slug_is_unique():
    """All blueprint slugs should be unique."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_blueprints(wikitext)

    slugs = [item["slug"] for item in items]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found"


def test_known_blueprint_parsed():
    """A specific known blueprint (e.g., Accretion Disk) should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_blueprints(wikitext)

    bp_names = [i["name"] for i in items]
    assert "Accretion Disk" in bp_names, "Expected Accretion Disk in parsed results"

    accretion = next(i for i in items if i["name"] == "Accretion Disk")
    assert accretion["data"]["quest_giver"] == "Meteor Guardian"
    assert "Galactic Guardian" in accretion["data"]["quest_name"]
    assert len(accretion["data"]["quest_steps"]) > 0


def test_quest_template_fields_are_split():
    """The {{Quest}} template fields must be split into separate keys.

    The template writes its fields as "|QuestSub = value", with spaces around
    the equals sign. A separator that does not allow them collapses the whole
    template into one unusable string.
    """
    wikitext = FIXTURE_PATH.read_text()
    items = parse_blueprints(wikitext)

    accretion = next(i for i in items if i["name"] == "Accretion Disk")
    step = accretion["data"]["quest_steps"][0]

    assert step["Quest"] == "Galactic Guardian"
    assert step["QuestSub"] == "Restore the valley's protective blessing."
    assert step["QuestStep1"] == "Collect 1 [[Celestium]]."
    assert step["QuestStep2"] == "Collect 100 [[Sunstone]]."
    assert step["QuestStep3"] == "Collect 25000 Materials from Meteor Valley."
    assert "Rewards" in step

    # The raw template arguments must not survive as one blob.
    assert "QuestSub =" not in step["Quest"]
