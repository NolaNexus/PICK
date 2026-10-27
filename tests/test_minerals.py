"""Tests for the minerals parser using the live wiki fixture."""

from pathlib import Path

from scrapers.minerals import parse_minerals

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "minerals.wiki"


def test_mineral_slugs_are_unique():
    """Tabber and global template passes must not emit duplicate minerals."""
    items = parse_minerals(FIXTURE_PATH.read_text())

    slugs = [item["slug"] for item in items]
    assert len(slugs) == len(set(slugs)), "Duplicate mineral slugs found"
    assert len(items) >= 100


def test_mineral_items_have_expected_shape():
    """Every parsed mineral has the fields required by the scraper upsert."""
    items = parse_minerals(FIXTURE_PATH.read_text())

    for item in items:
        assert item["type"] == "mineral"
        assert item["slug"]
        assert item["name"]
        assert isinstance(item["data"], dict)
        assert "tier" in item["data"]

    coral = next(item for item in items if item["slug"] == "coral")
    assert coral["data"]["tier"] == "Uncommon"
