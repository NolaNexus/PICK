"""Export the full public dataset to frontend/public/snapshot.json for static hosting.

Only writes the file when the data actually changed since the last export,
so repeated runs with identical data produce no git diff.
"""

import argparse
import asyncio
import json
import os

import app.database as app_database
from app.services.snapshot import build_snapshot

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "snapshot.json")

# Scrape timestamps change on every run even when the wiki content is
# identical. They are ignored when deciding whether the file needs rewriting,
# so an unchanged wiki does not trigger a commit and a site redeploy.
VOLATILE_ITEM_FIELDS = ("created_at", "updated_at")


def _comparable_item_data(data):
    """Return item data without the merchant's last-seen timestamp."""
    if not isinstance(data, dict):
        return data
    merchant = data.get("merchant")
    if not isinstance(merchant, dict) or "last_seen" not in merchant:
        return data
    return {**data, "merchant": {k: v for k, v in merchant.items() if k != "last_seen"}}


def _comparable(snapshot: dict) -> str:
    """Build a stable string representation used for change detection.

    Only the content that the site renders is compared: scrape timestamps are
    dropped because they change on every run.
    """
    items = [
        {
            "id": item.get("id"),
            "type": item.get("type"),
            "wiki_id": item.get("wiki_id"),
            "name": item.get("name"),
            "slug": item.get("slug"),
            "data": _comparable_item_data(item.get("data")),
            "image_url": item.get("image_url"),
            "description": item.get("description"),
        }
        for item in snapshot.get("items", [])
    ]
    formulas = [
        {
            "formula_id": formula.get("formula_id"),
            "name": formula.get("name"),
            "description": formula.get("description"),
            "formula": formula.get("formula"),
            "params": formula.get("params"),
            "confidence": formula.get("confidence"),
            "source_url": formula.get("source_url"),
            "patch_version": formula.get("patch_version"),
        }
        for formula in snapshot.get("formulas", [])
    ]
    wiki_pages = [
        {
            "title": page.get("title"),
            "page_id": page.get("page_id"),
            "last_revision_id": page.get("last_revision_id"),
            "content_hash": page.get("content_hash"),
            "namespace": page.get("namespace"),
        }
        for page in snapshot.get("wiki_pages", [])
    ]
    game_version = snapshot.get("game_version") or {}
    last_scrape = snapshot.get("last_scrape") or {}

    comparable = {
        "schema_version": snapshot.get("schema_version"),
        "counts": snapshot.get("counts"),
        "items": items,
        "formulas": formulas,
        "wiki_pages": wiki_pages,
        "game_version": game_version.get("version"),
        "last_scrape": {
            "status": last_scrape.get("status"),
            "pages_scraped": last_scrape.get("pages_scraped"),
            "pages_changed": last_scrape.get("pages_changed"),
            "pages_errors": last_scrape.get("pages_errors"),
        },
    }
    return json.dumps(comparable, sort_keys=True, default=str)


async def export_snapshot(output_path: str = OUTPUT_PATH) -> dict:
    """Build the snapshot and write it to disk only if it changed."""
    snapshot = await _build_snapshot_async()

    abs_path = os.path.abspath(output_path)
    changed = True
    if os.path.exists(abs_path):
        with open(abs_path, encoding="utf-8") as f:
            existing = json.load(f)
        if _comparable(existing) == _comparable(snapshot):
            changed = False

    if changed:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)

    return {
        "status": "ok",
        "changed": changed,
        "output": abs_path,
        "counts": snapshot["counts"],
    }


async def _build_snapshot_async() -> dict:
    await app_database.get_engine()
    async with app_database.async_session_factory() as session:
        return await build_snapshot(session)


async def main():
    parser = argparse.ArgumentParser(description="Export PICK snapshot to JSON")
    parser.add_argument(
        "--output",
        default=OUTPUT_PATH,
        help="Output path for snapshot.json",
    )
    args = parser.parse_args()
    result = await export_snapshot(args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
