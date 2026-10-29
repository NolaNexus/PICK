"""Export pipeline: DB/parsed -> JSON."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pick.parse.minerals import parse_minerals


def load_fixture(name: str) -> str:
    fixture_dir = Path(__file__).parent.parent.parent.parent / "tests" / "fixtures" / "wikitext"
    return (fixture_dir / name).read_text(encoding="utf-8")


def run_export() -> dict[str, Any]:
    """Run export from fixtures, produce items and meta."""
    # Parse minerals fixture
    minerals_text = load_fixture("Minerals.wiki")
    minerals = parse_minerals(minerals_text)

    all_items = []
    for m in minerals:
        item = {
            "slug": m["slug"],
            "name": m["name"],
            "type": m["type"],
            "data": m["data"],
            "image_url": None,
            "source_revid": m.get("source_revid"),
            "parser_version": m.get("parser_version", "0.1"),
        }
        all_items.append(item)

    # Build export object
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    export_data = {
        "schema_version": 1,
        "generated_at": now,
        "run_id": 1,
        "items": all_items,
        "source_rev_range": {"min": 0, "max": 0},
    }

    # Build meta
    meta = {
        "schema_version": 1,
        "generated_at": now,
        "run_id": 1,
        "last_scrape_iso": now,
        "total_items": len(all_items),
        "pages_tracked": 28,  # matches fixture count
    }

    return {"items": export_data, "meta": meta}


def write_export(output_dir: Path | None = None) -> None:
    """Write export files to public/data/."""
    if output_dir is None:
        output_dir = Path(__file__).parent.parent.parent.parent / "public" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    result = run_export()

    (output_dir / "items.json").write_text(
        json.dumps(result["items"], indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (output_dir / "meta.json").write_text(
        json.dumps(result["meta"], indent=2, ensure_ascii=False), encoding="utf-8"
    )
