"""The export must refuse to replace a good snapshot with a broken one.

A scrape whose requests were all refused still completes, and publishing that
result would erase the catalogue. These cases pin the refusal down.
"""

from scripts.export_snapshot import MAX_ITEM_DROP, _refusal_reason


def snapshot(items: int) -> dict:
    return {"counts": {"items": items}, "items": [{} for _ in range(items)]}


def test_refuses_an_empty_snapshot_over_a_full_one():
    reason = _refusal_reason(snapshot(853), snapshot(0))
    assert reason is not None
    assert "no items" in reason


def test_refuses_a_large_drop():
    lost = int(853 * MAX_ITEM_DROP) + 1
    reason = _refusal_reason(snapshot(853), snapshot(853 - lost))
    assert reason is not None
    assert "item count would fall" in reason


def test_allows_a_small_drop():
    kept = 853 - int(853 * MAX_ITEM_DROP) + 1
    assert _refusal_reason(snapshot(853), snapshot(kept)) is None


def test_allows_a_larger_snapshot():
    assert _refusal_reason(snapshot(100), snapshot(120)) is None


def test_allows_the_first_export():
    assert _refusal_reason({"counts": {"items": 0}, "items": []}, snapshot(853)) is None


def test_allows_an_unchanged_empty_snapshot():
    assert _refusal_reason(snapshot(0), snapshot(0)) is None
