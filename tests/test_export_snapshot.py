"""Tests for the static snapshot export's change detection.

The export runs on a schedule, so it must only rewrite the file when the
rendered content actually changed. Scrape timestamps change on every run and
must not count as a change.

The comparison is an exclusion list: the whole snapshot is compared apart from
the parts that are allowed to differ. That way a field added to the snapshot
later is picked up without anyone remembering to add it here, and a mistake
fails loud (an unnecessary commit) rather than quiet (a stale site).
"""

from scripts.export_snapshot import _comparable


def _snapshot(**overrides) -> dict:
    base = {
        "schema_version": 5,
        "taxonomy": [
            {"type": "mineral", "area": "minerals", "group": None, "label": "Mineral"},
        ],
        "generated_at": "2026-10-27T08:36:31.586710+00:00",
        "counts": {"items": 1, "formulas": 0, "wiki_pages": 0},
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


def _relic(index: int = 2) -> dict:
    return {
        "id": index,
        "type": "relic",
        "wiki_id": 11,
        "name": "Cosmic Resonator",
        "slug": "relic-cosmic-resonator",
        "data": {"rarity": "cosmic"},
        "image_url": None,
        "description": "A relic.",
        "created_at": "2026-10-27T08:35:44.004304+00:00",
        "updated_at": "2026-10-27T08:35:44.004350+00:00",
    }


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


def test_scrape_telemetry_is_not_a_change():
    """Per-run counters differ every time and must not force a rewrite."""
    first = _snapshot()
    second = _snapshot()
    second["last_scrape"]["status"] = "partial"
    second["last_scrape"]["pages_scraped"] = 111
    second["last_scrape"]["pages_changed"] = 7
    second["last_scrape"]["pages_errors"] = 2

    assert _comparable(first) == _comparable(second)


def test_item_content_change_is_detected():
    """A changed item value is a real change."""
    first = _snapshot()
    second = _snapshot()
    second["items"][0]["data"] = {"rarity": "rare"}

    assert _comparable(first) != _comparable(second)


def test_item_order_is_not_a_change():
    """The database does not promise an order, so the rows are sorted first.

    Without this, a run that returned the same items in a different order
    would look like a change and commit the file for no reason.
    """
    first = _snapshot()
    second = _snapshot()
    second["items"] = list(reversed(second["items"]))

    assert _comparable(first) == _comparable(second)


def test_adding_an_item_is_a_change():
    """A new item in the catalogue is real news."""
    first = _snapshot()
    second = _snapshot()
    second["items"].append(_relic())

    assert _comparable(first) != _comparable(second)


def test_removing_an_item_is_a_change():
    """Losing an item from the catalogue is real news."""
    first = _snapshot()
    second = _snapshot()
    second["items"] = []

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


def test_a_taxonomy_change_is_a_change():
    """The taxonomy travels with the snapshot, so a change to it must publish.

    This was the hole the exclusion list closed: the taxonomy used to be
    missing from the comparison altogether, so relabelling a type changed the
    file but was never published.
    """
    first = _snapshot()
    second = _snapshot()
    second["taxonomy"] = [
        {"type": "mineral", "area": "minerals", "group": None, "label": "Mineral (Rock)"},
    ]

    assert _comparable(first) != _comparable(second)


def test_a_new_top_level_key_is_a_change():
    """A field nobody thought to list is compared by default.

    This is the property that makes the exclusion list safe: a new part of
    the payload is picked up without anyone remembering to add it here.
    """
    first = _snapshot()
    second = _snapshot()
    second["game_version"]["patch"] = "1.2.3"

    assert _comparable(first) != _comparable(second)


def test_a_new_item_field_is_a_change():
    """A new field on an item is compared too, for the same reason."""
    first = _snapshot()
    second = _snapshot()
    second["items"][0]["rarity_tier"] = "uncommon"

    assert _comparable(first) != _comparable(second)


def test_a_wiki_page_change_is_a_change():
    """The tracked wiki pages are part of the published data."""
    first = _snapshot()
    second = _snapshot()
    second["wiki_pages"] = [
        {
            "id": 1,
            "title": "Minerals",
            "page_id": 7,
            "last_revision_id": 100,
            "last_scraped": "2026-10-27T08:00:00+00:00",
            "content_hash": "abc",
            "namespace": 0,
        }
    ]
    second["counts"] = {"items": 1, "formulas": 0, "wiki_pages": 1}

    assert _comparable(first) != _comparable(second)


def test_a_formula_change_is_a_change():
    """The formulas the site lists are part of the published data."""
    first = _snapshot()
    second = _snapshot()
    second["formulas"] = [
        {
            "id": 1,
            "formula_id": "f-1",
            "name": "Golden Rule",
            "description": None,
            "formula": "x * 2",
            "params": None,
            "confidence": 1.0,
            "source_url": None,
            "patch_version": None,
            "created_at": "2026-10-27T08:00:00+00:00",
        }
    ]
    second["counts"] = {"items": 1, "formulas": 1, "wiki_pages": 0}

    assert _comparable(first) != _comparable(second)


def test_a_schema_version_change_is_a_change():
    """A new schema version means the file has to be rewritten."""
    first = _snapshot(schema_version=2)
    second = _snapshot(schema_version=3)

    assert _comparable(first) != _comparable(second)


def test_the_comparison_does_not_mutate_the_snapshot():
    """The snapshot that gets written must be the one the database built."""
    snapshot = _snapshot()
    snapshot["items"][0]["data"] = {"merchant": {"stock": 1, "last_seen": "2026-10-27T08:00:00"}}

    _comparable(snapshot)

    assert snapshot["items"][0]["data"]["merchant"]["last_seen"] == "2026-10-27T08:00:00"
    assert snapshot["generated_at"] == "2026-10-27T08:36:31.586710+00:00"
    assert snapshot["last_scrape"]["pages_scraped"] == 26
