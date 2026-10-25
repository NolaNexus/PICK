"""Tests for mutations parser using live wiki fixtures."""

from pathlib import Path

from scrapers.mutations import parse_mutations

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "Mutations.wiki"


def test_mutations_parser_returns_items():
    """Mutations parser should parse chances, effects, and catalysts."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_mutations(wikitext)

    # Should have chance items (30), effects (7), catalysts (67) = 104 total
    assert len(items) >= 100, f"Expected at least 100 items, got {len(items)}"


def test_mutations_have_required_fields():
    """Every mutation item must have id, type, name, slug, data, image_url."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_mutations(wikitext)

    for item in items:
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item


def test_chance_items_structure():
    """Mutation chance items should have event, mutation, and chances_by_catalysts."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_mutations(wikitext)

    chance_items = [i for i in items if i["type"] == "mutation_chance"]
    assert len(chance_items) >= 30, f"Expected at least 30 chance items, got {len(chance_items)}"

    for item in chance_items:
        data = item["data"]
        assert "event" in data
        assert "mutation" in data
        assert "chances_by_catalysts" in data
        assert isinstance(data["chances_by_catalysts"], dict)
        assert len(data["chances_by_catalysts"]) > 0


def test_effect_items_structure():
    """Mutation effect items should have multiplier and additives."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_mutations(wikitext)

    effect_items = [i for i in items if i["type"] == "mutation_effect"]
    # Fixture has 7 effects: Silver, Gold, Diamond, Granite, Overclocked, Festive, Prismatic
    assert len(effect_items) == 7, f"Expected 7 effect items, got {len(effect_items)}"

    for item in effect_items:
        data = item["data"]
        assert "multiplier" in data
        assert "additives" in data
        assert isinstance(data["multiplier"], float)
        assert isinstance(data["additives"], dict)


def test_catalyst_items_structure():
    """Catalyst items should have rarity, equipment, and mineral."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_mutations(wikitext)

    catalyst_items = [i for i in items if i["type"] == "mutation_catalyst"]
    assert len(catalyst_items) >= 10, f"Expected at least 10 catalyst items, got {len(catalyst_items)}"

    for item in catalyst_items:
        data = item["data"]
        assert "rarity" in data
        assert "equipment" in data
        assert "mineral" in data
        assert isinstance(data["rarity"], str)
        assert len(data["equipment"]) > 0
        assert len(data["mineral"]) > 0


def test_known_mutation_parsed():
    """Specific known mutations should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_mutations(wikitext)

    # Check chance items
    prismatic_chance = next(i for i in items if i["name"] == "Prismatic (Without Events)")
    assert "Prismatic" in prismatic_chance["data"]["mutation"]
    assert "Without Events" in prismatic_chance["data"]["event"]
    # Fixture catalyst counts start at 2, not 1
    assert 2 in prismatic_chance["data"]["chances_by_catalysts"]
    assert 15 in prismatic_chance["data"]["chances_by_catalysts"]
    assert abs(prismatic_chance["data"]["chances_by_catalysts"][2] - 1.1) < 0.01

    # Check event-specific mutations
    festive_chance = next(i for i in items if "Festive" in i["name"] and "Candy Canes" in i["name"])
    assert "Festive" in festive_chance["data"]["mutation"]
    assert "Candy Canes" in festive_chance["data"]["event"]

    # Check effect items
    prismatic_effect = next(i for i in items if i["name"] == "Prismatic" and i["type"] == "mutation_effect")
    assert prismatic_effect["data"]["multiplier"] == 1.6

    gold_effect = next(i for i in items if i["name"] == "Gold")
    assert gold_effect["data"]["multiplier"] == 1.2

    # Check catalyst items
    gold_ring = next(i for i in items if i["name"] == "Gold Ring" and i["type"] == "mutation_catalyst")
    assert gold_ring["data"]["rarity"] == "Common"
    assert gold_ring["data"]["mineral"] == "Gold"

    smoke_ring = next(i for i in items if i["name"] == "Smoke Ring")
    assert smoke_ring["data"]["rarity"] == "Uncommon"
    assert smoke_ring["data"]["mineral"] == "Smoky Quartz"


def test_slug_is_unique():
    """All mutation slugs should be unique."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_mutations(wikitext)

    slugs = [item["slug"] for item in items]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found"
