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
    """Every NPC carries its locations, image and link target."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_npcs(wikitext)

    for item in items:
        data = item["data"]
        assert isinstance(data["locations"], list)
        assert data["locations"]
        assert "image" in data
        assert "link_target" in data


def test_npcs_slug_is_unique():
    """All NPC slugs should be unique across the whole page."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_npcs(wikitext)

    slugs = [item["slug"] for item in items]
    unique_slugs = set(slugs)
    assert len(unique_slugs) == len(slugs), (
        f"Duplicate NPC slugs: {sorted({s for s in slugs if slugs.count(s) > 1})}"
    )


def test_unique_npc_slug_is_name_only():
    """An NPC that exists in one location gets a name-based slug."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_npcs(wikitext)

    john = next(i for i in items if i["name"] == "John")
    assert john["slug"] == "john"
    assert john["data"]["locations"] == ["Rubble Creek"]

    regionless = next(i for i in items if i["name"] == "Merchant")
    assert regionless["slug"] == "global-merchant"


def test_repeated_npcs_are_grouped_by_name():
    """A flavour NPC that appears in several locations is one entry."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_npcs(wikitext)

    residents = [i for i in items if i["name"] == "Resident"]
    assert len(residents) == 1, "Resident should be one NPC with several locations"

    resident = residents[0]
    assert resident["slug"] == "resident"
    assert resident["data"]["locations"] == ["Fortune River", "Seashell Isle"]
    assert set(resident["data"]["portraits"]) == {"Fortune River", "Seashell Isle"}


def test_town_services_stay_per_location():
    """Each town's merchant/blacksmith/alchemist/trader is a distinct NPC."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_npcs(wikitext)

    merchants = [i for i in items if i["name"] == "Merchant"]
    assert len(merchants) == 8
    assert len({m["slug"] for m in merchants}) == 8
    assert all("region" in m["data"] for m in merchants)


def test_same_name_in_one_location_stay_distinct():
    """Two tourists sharing a name and a location are still two NPCs."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_npcs(wikitext)

    tourists = [i for i in items if i["name"] == "Two Tourists"]
    assert len(tourists) == 2
    assert len({t["slug"] for t in tourists}) == 2


def test_npcs_with_same_name_in_different_regions_are_distinct():
    """Merchant exists in many regions and each must produce its own item."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_npcs(wikitext)

    merchants = [i for i in items if i["name"] == "Merchant"]
    assert len(merchants) >= 3, f"Expected several Merchants, got {len(merchants)}"

    regions = {m["data"]["region"] for m in merchants}
    assert len(regions) == len(merchants), "Merchants should each be in a distinct region"
    assert len({m["slug"] for m in merchants}) == len(merchants)


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
