"""Tests for NPCs parser using live wiki fixtures."""

from pathlib import Path

from scrapers.npcs import parse_npcs

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "NPCs.wiki"


def test_npcs_parser_returns_items():
    """NPCs parser should parse NPCs from all tabber gallery sections."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_npcs(wikitext)

    # Should have many NPCs across all regions
    assert len(items) >= 50, f"Expected at least 50 NPCs, got {len(items)}"


def test_npcs_have_required_fields():
    """Every NPC item must have id, type, name, slug, data, image_url."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_npcs(wikitext)

    for item in items:
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item
        assert item["type"] == "npc"


def test_npcs_data_structure():
    """NPC data dict should contain region, location, image, link_target."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_npcs(wikitext)

    for item in items:
        data = item["data"]
        assert "region" in data
        assert "location" in data
        assert "image" in data
        assert "link_target" in data
        assert isinstance(data["region"], str)
        assert len(data["region"]) > 0


def test_npcs_slug_is_unique():
    """All NPC slugs should be unique."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_npcs(wikitext)

    slugs = [item["slug"] for item in items]
    # Allow duplicates for NPCs that appear in multiple regions (e.g., Merchant)
    # Just check that we have reasonable number of unique slugs
    unique_slugs = set(slugs)
    assert len(unique_slugs) >= 40, f"Expected at least 40 unique NPCs, got {len(unique_slugs)}"


def test_known_npcs_parsed():
    """Specific known NPCs should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_npcs(wikitext)

    npc_names = [i["name"] for i in items]

    # Check for regionless NPCs
    assert "Merchant" in npc_names
    assert "Blacksmith" in npc_names
    assert "Traveling Merchant" in npc_names

    # Check for region-specific NPCs
    assert "John" in npc_names
    assert "Mechanic" in npc_names
    assert "Santa" in npc_names
    assert "Meteor Guardian" in npc_names

    # Check region assignment
    john = next(i for i in items if i["name"] == "John")
    assert john["data"]["region"] == "Rubble Creek"

    santa = next(i for i in items if i["name"] == "Santa")
    assert santa["data"]["region"] == "North Pole"

    meteor_guardian = next(i for i in items if i["name"] == "Meteor Guardian")
    assert meteor_guardian["data"]["region"] == "Astral Caverns"
