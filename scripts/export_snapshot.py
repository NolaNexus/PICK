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


async def export_snapshot(output_path: str = OUTPUT_PATH) -> dict:
    """Build the snapshot and write it to disk only if it changed."""
    snapshot = await _build_snapshot_async()

    abs_path = os.path.abspath(output_path)
    changed = True
    if os.path.exists(abs_path):
        with open(abs_path, encoding="utf-8") as f:
            existing = json.load(f)
        if existing == snapshot:
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
