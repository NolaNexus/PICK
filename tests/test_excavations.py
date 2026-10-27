"""Tests for excavations parser using live wiki fixtures."""

from pathlib import Path

from scrapers.excavations import parse_excavations

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "Excavations.wiki"


def test_excavations_parser_returns_items():
    """Excavations parser should parse sites, levels, and rewards."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_excavations(wikitext)

    # Should have 6 sites + 15 levels + multiple rewards
    assert len(items) >= 50, f"Expected at least 50 items, got {len(items)}"


def test_excavations_have_required_fields():
    """Every excavation item must have id, type, name, slug, data, image_url."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_excavations(wikitext)

    for item in items:
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item
        assert item["type"] in ("excavation_site", "excavation_level", "excavation_reward")


def test_sites_parsed():
    """Excavation sites should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_excavations(wikitext)

    sites = [i for i in items if i["type"] == "excavation_site"]
    assert len(sites) == 6, f"Expected 6 sites, got {len(sites)}"

    site_names = [s["name"] for s in sites]
    assert "Volcanic Ruins (A-Site)" in site_names
    assert "Magma Temple (B-Site)" in site_names
    assert "Frozen Fortress (C-Site)" in site_names
    assert "Lost City (D-Site)" in site_names
    assert "Mysterious Meteor (E-Site)" in site_names
    assert "Alien Wreckage (F-Site)" in site_names

    # Check site data
    volcanic = next(s for s in sites if s["name"] == "Volcanic Ruins (A-Site)")
    assert volcanic["data"]["region"] == "Caldera Park"
    assert "$50,000,000" in volcanic["data"]["permit_cost"]
    assert "4 to 8" in volcanic["data"]["items_range"]


def test_levels_parsed():
    """Excavation levels should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_excavations(wikitext)

    levels = [i for i in items if i["type"] == "excavation_level"]
    assert len(levels) == 15, f"Expected 15 levels, got {len(levels)}"

    level_nums = [level["data"]["level"] for level in levels]
    assert level_nums == list(range(1, 16))

    # Check level 1
    level_1 = next(level for level in levels if level["data"]["level"] == 1)
    assert level_1["data"]["items_a_site"] == "4–8 (+0)"
    assert "10h" in level_1["data"]["durations"]


def test_rewards_parsed():
    """Excavation rewards should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_excavations(wikitext)

    rewards = [i for i in items if i["type"] == "excavation_reward"]
    assert len(rewards) >= 30, f"Expected at least 30 rewards, got {len(rewards)}"

    # Check specific rewards
    reward_names = [r["name"] for r in rewards]
    assert "Divine Enchant Book" in reward_names
    assert "Solar Magnifier" in reward_names

    # Check Volcanic Ruins rewards
    volcanic_rewards = [r for r in rewards if r["data"]["site"] == "Volcanic Ruins"]
    assert len(volcanic_rewards) == 6

    # Check Alien Wreckage rewards
    alien_rewards = [r for r in rewards if r["data"]["site"] == "Alien Wreckage"]
    assert len(alien_rewards) == 9


def test_slug_is_unique():
    """All excavation slugs should be unique."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_excavations(wikitext)

    slugs = [item["slug"] for item in items]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found"
