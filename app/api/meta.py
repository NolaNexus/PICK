from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models import Formula, GameVersion, Item, News, ScraperRun

router = APIRouter()


@router.get("", tags=["meta"])
async def meta(db: AsyncSession = Depends(get_session)):  # noqa: B008
    """Application metadata and database statistics."""
    # Get item counts by type
    item_types_result = await db.execute(
        select(Item.type, func.count(Item.id)).group_by(Item.type)
    )
    item_counts = {row[0]: row[1] for row in item_types_result.all()}

    # Get total counts
    total_items_result = await db.execute(select(func.count(Item.id)))
    total_items = total_items_result.scalar() or 0

    total_formulas_result = await db.execute(select(func.count(Formula.id)))
    total_formulas = total_formulas_result.scalar() or 0

    total_news_result = await db.execute(select(func.count(News.id)))
    total_news = total_news_result.scalar() or 0

    # Get last scraper run
    last_run_result = await db.execute(
        select(ScraperRun).order_by(ScraperRun.started_at.desc()).limit(1)
    )
    last_run = last_run_result.scalar_one_or_none()

    # Get current game version
    current_version_result = await db.execute(
        select(GameVersion).order_by(GameVersion.detected_at.desc()).limit(1)
    )
    current_version = current_version_result.scalar_one_or_none()

    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "wiki_url": settings.mediawiki_api_url,
        "database": {
            "total_items": total_items,
            "total_formulas": total_formulas,
            "total_news": total_news,
            "items_by_type": item_counts,
        },
        "last_scrape": {
            "status": last_run.status if last_run else "never",
            "started_at": last_run.started_at if last_run else None,
            "finished_at": last_run.finished_at if last_run else None,
            "pages_scraped": last_run.pages_scraped if last_run else 0,
            "pages_changed": last_run.pages_changed if last_run else 0,
            "pages_errors": last_run.pages_errors if last_run else 0,
        } if last_run else None,
        "current_game_version": {
            "version": current_version.version if current_version else None,
            "detected_at": current_version.detected_at if current_version else None,
            "triggered_full_scrape": current_version.triggered_full_scrape if current_version else 0,
        } if current_version else None,
    }
