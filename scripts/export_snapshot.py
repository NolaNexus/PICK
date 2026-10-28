"""Export the full public dataset to frontend/public/snapshot.json for static hosting.

Only writes the file when the data actually changed since the last export,
so repeated runs with identical data produce no git diff.
"""

import argparse
import asyncio
import copy
import json
import os
import re

import app.database as app_database
from app.services.snapshot import build_snapshot

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "snapshot.json")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "snapshot.schema.json")

# A snapshot that loses this much of the catalogue is treated as broken rather
# than as news. The scramble this prevents: a scrape whose requests were all
# refused still completes, and publishing it would erase the site.
MAX_ITEM_DROP = 0.20

# Wiki markup that should never reach the published file. The scraper renders
# it before writing, so any occurrence here is a parser that missed a case.
_MARKUP_RE = re.compile(r"\{\{|\[\[|</|&lt;|&gt;")


def _item_count(snapshot: dict) -> int:
    """The number of items in a snapshot."""
    counts = snapshot.get("counts")
    if isinstance(counts, dict):
        return int(counts.get("items") or 0)
    return len(snapshot.get("items") or [])


def _refusal_reason(existing: dict, snapshot: dict) -> str | None:
    """Why the new snapshot must not replace the existing one, if it must not."""
    before = _item_count(existing)
    after = _item_count(snapshot)

    if before and after == 0:
        return f"the new snapshot has no items and the existing one has {before}"

    if before and after < before * (1 - MAX_ITEM_DROP):
        lost = round((1 - after / before) * 100)
        return f"the item count would fall from {before} to {after} ({lost}% lost)"

    return None


def _data_quality_reason(snapshot: dict) -> str | None:
    """Why the snapshot must not be published for data-quality reasons."""
    for item in snapshot.get("items") or []:
        if not isinstance(item, dict):
            continue
        if _MARKUP_RE.search(json.dumps(item, ensure_ascii=False)):
            return "an item still carries raw wiki markup"
    return None


def _schema_reason(snapshot: dict) -> str | None:
    """Why the snapshot does not match the published contract."""
    try:
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)
        from jsonschema import Draft7Validator

        errors = sorted(Draft7Validator(schema).iter_errors(snapshot), key=lambda e: list(e.path))
    except Exception as exc:
        return f"the snapshot contract could not be checked: {exc}"
    if errors:
        error = errors[0]
        path = ".".join(str(part) for part in error.path) or "<root>"
        return f"the snapshot does not match the contract at {path}: {error.message}"
    return None


def _strip_volatile(snapshot: dict) -> dict:
    """Return a copy of the snapshot without the parts that always differ.

    Everything else is compared. The list below is the whole of what is
    allowed to differ between two runs: scrape timestamps, the per-run
    telemetry, and the merchant's last-seen stamp, because the merchant's
    stock rotates daily.
    """
    cleaned = copy.deepcopy(snapshot)

    cleaned.pop("generated_at", None)
    cleaned.pop("last_scrape", None)

    game_version = cleaned.get("game_version")
    if isinstance(game_version, dict):
        game_version.pop("detected_at", None)

    for item in cleaned.get("items") or []:
        if not isinstance(item, dict):
            continue
        data = item.get("data")
        if isinstance(data, dict):
            merchant = data.get("merchant")
            if isinstance(merchant, dict):
                merchant.pop("last_seen", None)

    return cleaned


def _sorted_rows(rows: list, key: str) -> list:
    """Return the rows ordered by a key, so the order the database used is irrelevant."""
    return sorted(rows or [], key=lambda row: str(row.get(key)) if isinstance(row, dict) else "")


def _comparable(snapshot: dict) -> str:
    """Build a stable string representation used for change detection.

    The whole snapshot is compared, apart from the volatile parts, so a
    change anywhere in the published data is a change. The rows are sorted
    first because the order the database returns them in is not guaranteed,
    and comparing positionally would report a change whenever the rows came
    back in a different order even though nothing about the data had changed.
    """
    cleaned = _strip_volatile(snapshot)

    cleaned["items"] = _sorted_rows(cleaned.get("items") or [], "slug")
    cleaned["formulas"] = _sorted_rows(cleaned.get("formulas") or [], "formula_id")
    cleaned["wiki_pages"] = _sorted_rows(cleaned.get("wiki_pages") or [], "title")

    return json.dumps(cleaned, sort_keys=True, default=str)


async def export_snapshot(
    output_path: str = OUTPUT_PATH,
    force: bool = False,
    check: bool = False,
) -> dict:
    """Build the snapshot and write it to disk only if it changed.

    Refuses to write a snapshot that would erase the catalogue. Pass
    ``force`` when the drop is real (a game update that removed items).
    ``check`` reports what would happen without touching the file.
    """
    snapshot = await _build_snapshot_async()

    abs_path = os.path.abspath(output_path)
    changed = True
    if os.path.exists(abs_path):
        with open(abs_path, encoding="utf-8") as f:
            existing = json.load(f)

        if not force:
            reason = _refusal_reason(existing, snapshot)
            if reason is None:
                reason = _data_quality_reason(snapshot)
            if reason is None:
                reason = _schema_reason(snapshot)
            if reason is not None:
                return {
                    "status": "refused",
                    "reason": reason,
                    "output": abs_path,
                    "counts": snapshot["counts"],
                }

        if _comparable(existing) == _comparable(snapshot):
            changed = False

    if changed and not check:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)

    return {
        "status": "ok",
        "changed": changed,
        "written": changed and not check,
        "output": abs_path,
        "counts": snapshot["counts"],
    }


async def _build_snapshot_async() -> dict:
    await app_database.get_engine()
    factory = await app_database.get_session_factory()
    async with factory() as session:
        return await build_snapshot(session)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Export PICK snapshot to JSON")
    parser.add_argument(
        "--output",
        default=OUTPUT_PATH,
        help="Output path for snapshot.json",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Write even when the item count drops sharply",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report whether the snapshot would change without writing it",
    )
    args = parser.parse_args()
    result = await export_snapshot(args.output, force=args.force, check=args.check)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    import sys

    sys.exit(asyncio.run(main()))
