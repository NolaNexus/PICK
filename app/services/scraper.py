"""Core scraper service - orchestrates wiki page scraping and change detection."""

import hashlib
import logging
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.utils.mw_api import MediaWikiClient
from scrapers import PARSERS  # type: ignore

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Pages to track from the wiki
TRACKED_PAGES = [
    "Pans",
    "Shovels",
    "Minerals",
    "Sluices",
    "Equipment",
    "Enchanting",
    "Locations",
    "Traveling_Merchant",
    "NPCs",
    "Events",
    "Quests",
    "Museum",
    "Excavations",
    "Relics",
    "Geodes",
    "Runes",
    "Mastery",
    "Mutations",
    "Treasure_Map",
    "Stat_Systems_Guide",
    "Blueprint",
    "Trinkets",
    "Modifiers",
    "Codes",
    "Changelog",
    "Guides",
]


async def check_for_game_update(db: "AsyncSession", client: MediaWikiClient) -> bool:
    """Check Changelog page for new game version.

    Returns True if a new version is detected and full scrape should be triggered.
    """
    from app.models import GameVersion

    try:
        page_info = await client.get_page_info("Changelog")
        wikitext = page_info.get("wikitext", "")
        if not wikitext:
            logger.warning("No wikitext for Changelog")
            return False

        # Extract latest version header (e.g., "== October 2026 ==")
        # Pattern matches == Month Year == or similar version headers
        version_match = re.search(r"==\s*([^=]+)\s*==", wikitext)
        if not version_match:
            logger.warning("Could not parse version from Changelog")
            return False

        latest_version = version_match.group(1).strip()

        # Check if we've seen this version before
        existing = await db.execute(
            select(GameVersion).where(GameVersion.version == latest_version)
        )
        if existing.scalar_one_or_none():
            return False  # Already seen this version

        # New version detected - store it
        game_version = GameVersion(
            version=latest_version,
            raw_header=version_match.group(0),
            triggered_full_scrape=1,
        )
        db.add(game_version)
        await db.commit()

        logger.info("New game version detected: %s", latest_version)
        return True

    except Exception as e:
        logger.error("Failed to check for game update: %s", e)
        return False


async def run_daily_scrape(db: "AsyncSession") -> dict:
    """Run the daily wiki scrape cycle (incremental via recentchanges).

    First checks for game updates via Changelog. If a new version is detected,
    runs a full scrape instead of incremental.
    """
    client = MediaWikiClient()
    try:
        new_version = await check_for_game_update(db, client)
        if new_version:
            logger.info("Game update detected, running full scrape")
            return await _run_scrape(db, incremental=False)
    finally:
        await client.close()

    return await _run_scrape(db, incremental=True)


async def run_full_scrape(db: "AsyncSession") -> dict:
    """Run a full wiki scrape of all tracked pages (bypass recentchanges)."""
    return await _run_scrape(db, incremental=False)


async def _run_scrape(db: "AsyncSession", incremental: bool) -> dict:
    """Run the wiki scrape cycle."""
    from app.models import ScraperRun

    run = ScraperRun(status="running")
    db.add(run)
    await db.flush()

    client = MediaWikiClient()
    pages_scraped = 0
    pages_changed = 0
    pages_errors = 0
    error_log = []

    try:
        if incremental:
            changes = await client.get_recent_changes(days=1)
            titles_to_scrape = [
                change.get("title", "") for change in changes
                if change.get("title", "") in TRACKED_PAGES
            ]
        else:
            # Full scrape: iterate all tracked pages
            titles_to_scrape = TRACKED_PAGES

        for title in titles_to_scrape:
            try:
                changed = await scrape_page(db, client, title)
                if changed:
                    pages_changed += 1
                pages_scraped += 1
            except Exception as e:
                pages_errors += 1
                error_log.append(f"{title}: {e}")
                logger.error("Failed to scrape %s: %s", title, e)

    finally:
        await client.close()

    run.finished_at = datetime.now(UTC)
    run.status = "success" if pages_errors == 0 else "partial"
    run.pages_scraped = pages_scraped
    run.pages_changed = pages_changed
    run.pages_errors = pages_errors
    run.error_log = "\n".join(error_log) if error_log else None

    await db.commit()
    return {
        "status": run.status,
        "pages_scraped": pages_scraped,
        "pages_changed": pages_changed,
        "pages_errors": pages_errors,
    }


async def scrape_page(
    db: "AsyncSession",
    client: MediaWikiClient,
    title: str,
) -> bool:
    """Scrape a single page, upsert items if content changed."""
    from app.models import Item, WikiPage

    page_info = await client.get_page_info(title)
    wikitext = page_info.get("wikitext", "")
    if not wikitext:
        logger.warning("No wikitext for %s", title)
        return False

    content_hash = hashlib.sha256(wikitext.encode("utf-8")).hexdigest()
    page_id = page_info.get("page_id")
    revision_id = page_info.get("revision_id")

    wiki_page = await db.get(WikiPage, title)
    if wiki_page and wiki_page.content_hash == content_hash:
        logger.debug("No change for %s", title)
        return False

    parser = PARSERS.get(title)
    if not parser:
        logger.warning("No parser for %s", title)
        return False

    items = parser(wikitext)

    if wiki_page is None:
        wiki_page = WikiPage(
            title=title,
            page_id=page_id,
            last_revision_id=revision_id,
            content_hash=content_hash,
        )
        db.add(wiki_page)
        await db.flush()

    for item_data in items:
        slug = item_data.get("slug") or item_data["name"].lower().replace(" ", "-")
        existing = await db.execute(
            select(Item).where(Item.slug == slug)
        )
        item = existing.scalar_one_or_none()

        if item is None:
            item = Item(
                type=item_data["type"],
                wiki_id=item_data.get("wiki_id"),
                name=item_data["name"],
                slug=slug,
                data=item_data.get("data", {}),
                image_url=item_data.get("image_url"),
                description=item_data.get("description"),
                wiki_page=wiki_page,
            )
            db.add(item)
        else:
            item.type = item_data["type"]
            item.wiki_id = item_data.get("wiki_id")
            item.name = item_data["name"]
            item.data = item_data.get("data", {})
            item.image_url = item_data.get("image_url")
            item.description = item_data.get("description")
            item.updated_at = datetime.now(UTC)

    wiki_page.last_revision_id = revision_id
    wiki_page.content_hash = content_hash
    wiki_page.last_scraped = datetime.now(UTC)

    await db.commit()
    return True
