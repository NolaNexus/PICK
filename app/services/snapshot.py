"""Shared snapshot serialization used by the API export endpoint and the CLI export script."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Formula, GameVersion, Item, News, ScraperRun, WikiPage


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


async def build_snapshot(db: AsyncSession) -> dict:
    """Build the full public dataset snapshot dict from the database."""
    items = (await db.execute(select(Item).where(Item.is_active.is_(True)))).scalars().all()
    formulas = (await db.execute(select(Formula))).scalars().all()
    news = (await db.execute(select(News))).scalars().all()
    wiki_pages = (await db.execute(select(WikiPage))).scalars().all()
    game_version = (
        await db.execute(select(GameVersion).order_by(GameVersion.detected_at.desc()).limit(1))
    ).scalar_one_or_none()
    last_run = (
        await db.execute(select(ScraperRun).order_by(ScraperRun.started_at.desc()).limit(1))
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
        }
        if game_version
        else None,
        "last_scrape": {
            "status": last_run.status if last_run else "never",
            "started_at": _iso(last_run.started_at) if last_run else None,
            "finished_at": _iso(last_run.finished_at) if last_run else None,
            "pages_scraped": last_run.pages_scraped if last_run else 0,
            "pages_changed": last_run.pages_changed if last_run else 0,
            "pages_errors": last_run.pages_errors if last_run else 0,
        }
        if last_run
        else None,
    }
