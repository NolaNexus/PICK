"""Tests for the static snapshot export's change detection.

The export runs on a schedule, so it must only rewrite the file when the
rendered content actually changed. Scrape timestamps change on every run and
must not count as a change.
"""

from scripts.export_snapshot import _comparable, _comparable_item_data


def _snapshot(**overrides) -> dict:
    base = {
        "generated_at": "2026-10-27T08:36:31.586710+00:00",
        "counts": {"items": 1, "formulas": 0, "news": 0, "wiki_pages": 0},
        "items": [
            {
                "id": 1,
                "type": "mineral",
                "wiki_id": 10,
                "name": "Quartz",
                "slug": "mineral-quartz",
                "data": {"rarity": "common"},
                "image_url": None,
                "description": "A common mineral.",
                "created_at": "2026-10-27T08:35:44.004304+00:00",
                "updated_at": "2026-10-27T08:35:44.004350+00:00",
            }
        ],
        "formulas": [],
        "news": [],
        "wiki_pages": [],
        "game_version": {"version": "October 2026", "detected_at": None},
        "last_scrape": {
            "status": "success",
            "started_at": "2026-10-27T08:35:44.010648+00:00",
            "finished_at": "2026-10-27T08:35:50.748850+00:00",
            "pages_scraped": 26,
            "pages_changed": 0,
            "pages_errors": 0,
        },
    }
    base.update(overrides)
    return base


def test_timestamps_alone_are_not_a_change():
    """A new scrape timestamp must not be treated as new data."""
    first = _snapshot()
    second = _snapshot(
        generated_at="2026-10-27T20:30:01.586710+00:00",
    )
    second["items"][0]["created_at"] = "2026-10-27T20:29:53.923138+00:00"
    second["items"][0]["updated_at"] = "2026-10-27T20:29:53.923171+00:00"
    second["last_scrape"]["started_at"] = "2026-10-27T20:29:53.928706+00:00"
    second["last_scrape"]["finished_at"] = "2026-10-27T20:30:01.439051+00:00"
    second["game_version"]["detected_at"] = "2026-10-27T20:29:53.920656+00:00"

    assert _comparable(first) == _comparable(second)


def test_item_content_change_is_detected():
    """A changed item value is a real change."""
    first = _snapshot()
    second = _snapshot()
    second["items"][0]["data"] = {"rarity": "rare"}

    assert _comparable(first) != _comparable(second)


def test_merchant_last_seen_is_ignored():
    """The merchant stock rotates daily, so its timestamp is not a change."""
    first = _snapshot()
    second = _snapshot()
    first["items"][0]["data"] = {"merchant": {"stock": 1, "last_seen": "2026-10-27T08:00:00"}}
    second["items"][0]["data"] = {"merchant": {"stock": 1, "last_seen": "2026-10-27T20:00:00"}}

    assert _comparable(first) == _comparable(second)


def test_merchant_stock_change_is_detected():
    """A merchant stock change is real data and must be detected."""
    first = _snapshot()
    second = _snapshot()
    first["items"][0]["data"] = {"merchant": {"stock": 1, "last_seen": "2026-10-27T08:00:00"}}
    second["items"][0]["data"] = {"merchant": {"stock": 3, "last_seen": "2026-10-27T20:00:00"}}

    assert _comparable(first) != _comparable(second)


def test_comparable_item_data_leaves_other_data_untouched():
    """Item data without a merchant block is returned unchanged."""
    data = {"rarity": "common"}
    assert _comparable_item_data(data) == data
    assert _comparable_item_data(None) is None


def test_a_schema_version_change_is_a_change():
    """A new schema version means the file has to be rewritten."""
    first = _snapshot(schema_version=2)
    second = _snapshot(schema_version=3)

    assert _comparable(first) != _comparable(second)
