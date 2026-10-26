"""Export the full public dataset to frontend/public/snapshot.json for static hosting.

Only writes the file when the data actually changed since the last export,
so repeated runs with identical data produce no git diff.
"""

import argparse
import asyncio
import json
import os
from datetime import UTC, datetime

from sqlalchemy import select

import app.database as app_database
from app.models import Formula, GameVersion, Item, News, ScraperRun, WikiPage

OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "frontend", "public", "snapshot.json"
)


def _iso(value):
    return value.isoformat() if value is not None else None


def _item_row(item: Item) -> dict:
    return {
        "id": item.id,
        "type": item.type,
        "wiki_id": item.wiki_id,
        "name": item.name,
        "slug": item.slug,
        "data": item.data,
        "image_url": item.image_url,
        "description": item.description,
        "created_at": _iso(item.created_at),
        "updated_at": _iso(item.updated_at),
    }


def _formula_row(formula: Formula) -> dict:
    return {
        "id": formula.id,
        "formula_id": formula.formula_id,
        "name": formula.name,
        "description": formula.description,
        "formula": formula.formula,
        "params": formula.params,
        "confidence": formula.confidence,
        "source_url": formula.source_url,
        "patch_version": formula.patch_version,
        "created_at": _iso(formula.created_at),
    }


def _news_row(article: News) -> dict:
    return {
        "id": article.id,
        "source": article.source,
        "external_id": article.external_id,
        "title": article.title,
        "url": article.url,
        "author": article.author,
        "score": article.score,
        "published_at": _iso(article.published_at),
        "fetched_at": _iso(article.fetched_at),
        "content": article.content,
        "tags": article.tags,
    }


def _wiki_page_row(page: WikiPage) -> dict:
    return {
        "id": page.id,
        "title": page.title,
        "page_id": page.page_id,
        "last_revision_id": page.last_revision_id,
        "last_scraped": _iso(page.last_scraped),
        "content_hash": page.content_hash,
        "namespace": page.namespace,
    }


async def build_snapshot() -> dict:
    await app_database.get_engine()
    async with app_database.async_session_factory() as session:
        items = (await session.execute(select(Item))).scalars().all()
        formulas = (await session.execute(select(Formula))).scalars().all()
        news = (await session.execute(select(News))).scalars().all()
        wiki_pages = (await session.execute(select(WikiPage))).scalars().all()
        game_version = (
            await session.execute(
                select(GameVersion).order_by(GameVersion.detected_at.desc()).limit(1)
            )
        ).scalar_one_or_none()
        last_run = (
            await session.execute(
                select(ScraperRun).order_by(ScraperRun.started_at.desc()).limit(1)
            )
        ).scalar_one_or_none()

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "counts": {
            "items": len(items),
            "formulas": len(formulas),
            "news": len(news),
            "wiki_pages": len(wiki_pages),
        },
        "items": [_item_row(i) for i in items],
        "formulas": [_formula_row(f) for f in formulas],
        "news": [_news_row(n) for n in news],
        "wiki_pages": [_wiki_page_row(p) for p in wiki_pages],
        "game_version": {
            "version": game_version.version if game_version else None,
            "detected_at": _iso(game_version.detected_at) if game_version else None,
        } if game_version else None,
        "last_scrape": {
            "status": last_run.status if last_run else "never",
            "started_at": _iso(last_run.started_at) if last_run else None,
            "finished_at": _iso(last_run.finished_at) if last_run else None,
            "pages_scraped": last_run.pages_scraped if last_run else 0,
            "pages_changed": last_run.pages_changed if last_run else 0,
            "pages_errors": last_run.pages_errors if last_run else 0,
        } if last_run else None,
    }


async def export_snapshot(output_path: str = OUTPUT_PATH) -> dict:
    snapshot = await build_snapshot()

    abs_path = os.path.abspath(output_path)
    changed = True
    if os.path.exists(abs_path):
        with open(abs_path, "r", encoding="utf-8") as f:
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
