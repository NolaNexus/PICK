"""Core scraper service - orchestrates wiki page scraping and change detection."""

import hashlib
import logging
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select, update

from app.services.item_data import normalize_item_data
from app.services.enrichment import enrich_items_from_pages
from app.services.reconcile import reconcile_items, type_prefixed_slug
from app.utils.mw_api import MediaWikiClient
from scrapers import PARSER_VERSION, PARSERS, TRACKED_PAGES
from scrapers.types import ParsedItem
from scrapers.wikitext import render_item_data, render_text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


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

        # Extract the latest version header (e.g. "== October 2026 ==").
        # The heading must be exactly level 2: "== Title ==". A level-3
        # heading such as "=== Changelog ===" must not match, otherwise the
        # page title is stored as the game version.
        version_match = re.search(r"(?m)^(==)\s+([^=].*?)\s+\1\s*$", wikitext)
        if not version_match:
            logger.warning("Could not parse version from Changelog")
            return False

        latest_version = version_match.group(2).strip()

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
            # Changelog was already fetched by check_for_game_update.
            return await _run_scrape(db, incremental=False, skip_titles={"Changelog"})
    finally:
        await client.close()

    return await _run_scrape(db, incremental=True)


async def run_full_scrape(db: "AsyncSession") -> dict:
    """Run a full wiki scrape of all tracked pages (bypass recentchanges)."""
    return await _run_scrape(db, incremental=False)


async def _run_scrape(
    db: "AsyncSession",
    incremental: bool,
    skip_titles: set[str] | None = None,
) -> dict:
    """Run the wiki scrape cycle."""
    from app.models import ScraperRun

    skip_titles = skip_titles or set()
    run = ScraperRun(status="running")
    db.add(run)
    await db.flush()

    client = MediaWikiClient()
    pages_scraped = 0
    pages_ok = 0
    pages_changed = 0
    pages_errors = 0
    error_log = []
    enriched: dict = {}

    try:
        if incremental:
            try:
                changes = await client.get_recent_changes(days=1)
                titles_to_scrape = [
                    change.get("title", "")
                    for change in changes
                    if change.get("title", "") in TRACKED_PAGES
                ]
            except Exception as e:
                # The list of recent changes is an optimisation. When the wiki
                # cannot be asked for it, every page is scraped instead of
                # losing the run.
                logger.warning("Could not list recent changes (%s); scraping every page", e)
                error_log.append(f"recent changes: {e}")
                titles_to_scrape = list(TRACKED_PAGES)
            else:
                if not titles_to_scrape:
                    # Nothing was reported as changed. That is possible when
                    # the wiki is busy, and it would leave the site stale, so
                    # every page is scraped instead.
                    logger.warning("The wiki reported no recent changes; scraping every page")
                    titles_to_scrape = list(TRACKED_PAGES)
        else:
            # Full scrape: iterate all tracked pages
            titles_to_scrape = TRACKED_PAGES

        titles_to_scrape = [title for title in titles_to_scrape if title not in skip_titles]

        for title in titles_to_scrape:
            try:
                changed = await scrape_page(db, client, title)
                # Pages without a parser are never fetched, so they do not
                # count as a page the run reached.
                if PARSERS.get(title):
                    pages_ok += 1
                if changed:
                    pages_changed += 1
                pages_scraped += 1
            except Exception as e:
                pages_errors += 1
                error_log.append(f"{title}: {e}")
                logger.error("Failed to scrape %s: %s", title, e)

        # The items that have a page of their own fill in the fields the index
        # pages left empty. This runs after the index pages so it can fill
        # them, and before reconciliation so a new item is merged like any
        # other.
        try:
            enriched = await enrich_items_from_pages(db, client)
        except Exception as e:
            pages_errors += 1
            error_log.append(f"enrichment: {e}")
            logger.exception("Item enrichment failed")
            enriched = {}

    finally:
        await client.close()

    try:
        reconciled = await reconcile_items(db)
    except Exception as e:
        pages_errors += 1
        error_log.append(f"reconcile: {e}")
        logger.exception("Item reconciliation failed")
        reconciled = {}

    # Normalise the stored payload once, after every page has been merged, so
    # the database never keeps a field the site does not read.
    from app.models import Item

    for item in (await db.execute(select(Item).where(Item.is_active.is_(True)))).scalars().all():
        normalized = normalize_item_data(item.data, item.type)
        if normalized != (item.data or {}):
            item.data = normalized
            item.updated_at = datetime.now(UTC)

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
        "pages_ok": pages_ok,
        "pages_changed": pages_changed,
        "pages_errors": pages_errors,
        "enriched": enriched,
        "reconciled": reconciled,
    }


async def _resolve_image_urls(
    client: MediaWikiClient,
    parsed_items: list[tuple[ParsedItem, str]],
) -> dict[str, str]:
    """Resolve the image file names of a page to their URLs.

    A failure to reach the wiki for the images is not fatal: the items are
    stored without a picture rather than not at all.
    """
    names = {
        name for item_data, _ in parsed_items if (name := _image_name(item_data.get("data", {})))
    }
    if not names:
        return {}

    try:
        return await client.get_image_urls(sorted(names))
    except Exception as exc:  # pragma: no cover - depends on the wiki
        logger.warning("Could not resolve image URLs: %s", exc)
        return {}


def _image_name(data: dict[str, Any]) -> str:
    """Return the image file name of an item, if it has one."""
    if not isinstance(data, dict):
        return ""

    for key in ("image", "icon"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""


async def scrape_page(
    db: "AsyncSession",
    client: MediaWikiClient,
    title: str,
    parser: Callable[[str], list[ParsedItem]] | None = None,
) -> bool:
    """Scrape a single page, upsert items if content changed."""
    from app.models import Item, WikiPage

    parser = parser or PARSERS.get(title)
    if not parser:
        logger.warning("No parser for %s", title)
        return False

    page_info = await client.get_page_info(title)
    wikitext = page_info.get("wikitext", "")
    if not wikitext:
        logger.warning("No wikitext for %s", title)
        return False

    # The hash covers the page content and the parsing rules. A change to a
    # parser or to the shared wikitext renderer therefore re-parses the page,
    # instead of leaving the stored data in the old shape.
    content_hash = hashlib.sha256(f"{PARSER_VERSION}:{wikitext}".encode()).hexdigest()
    page_id = page_info.get("page_id")
    revision_id = page_info.get("revision_id") or 0  # Default to 0 if None

    # Query by title (unique column), not by primary key
    page_result = await db.execute(select(WikiPage).where(WikiPage.title == title))
    wiki_page = page_result.scalar_one_or_none()
    if wiki_page and wiki_page.content_hash == content_hash:
        logger.debug("No change for %s", title)
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

    # Slugs are namespaced by item type. The same name can legitimately exist
    # under different types (a "Dredge Master" NPC and a "Dredge Master" quest,
    # "Museum" as a location and as its museum_info record, "The Void" as a
    # location and as an event), and `items.slug` is globally unique. Deriving
    # the slug from type + parser slug keeps it deterministic and idempotent:
    # every scrape resolves to the same rows regardless of page order.
    parsed_items: list[tuple[ParsedItem, str]] = []
    seen_slugs: set[str] = set()
    for item_data in items:
        base_slug = (
            item_data.get("slug")
            or item_data.get("id")
            or item_data["name"].lower().replace(" ", "-")
        )
        slug = type_prefixed_slug(item_data["type"], base_slug)
        if slug in seen_slugs:
            logger.warning("Duplicate slug %r on %s; keeping first occurrence", slug, title)
            continue
        seen_slugs.add(slug)
        parsed_items.append((item_data, slug))

    slugs = [slug for _, slug in parsed_items]
    existing_items: dict[str, Item] = {}
    if slugs:
        items_result = await db.execute(select(Item).where(Item.slug.in_(slugs)))
        existing_items = {item.slug: item for item in items_result.scalars().all()}

    # The wiki only stores the name of an image file, so the names are
    # resolved to their URLs in one batch for the whole page.
    image_urls = await _resolve_image_urls(client, parsed_items)

    for item_data, slug in parsed_items:
        item = existing_items.get(slug)

        # Item data is public API and is read as plain text, so the wiki
        # markup is resolved once, here, instead of in every parser.
        description = item_data.get("description")
        if isinstance(description, str):
            description = render_text(description)
        item_data = {
            **item_data,
            "data": normalize_item_data(
                render_item_data(item_data.get("data", {}) or {}),
                item_data.get("type"),
            ),
            "description": description,
        }

        image_url = image_urls.get(_image_name(item_data.get("data", {})))
        if image_url:
            item_data["image_url"] = image_url

        if item is None:
            item = Item(
                type=item_data["type"],
                name=item_data["name"],
                slug=slug,
                data=item_data.get("data", {}),
                image_url=item_data.get("image_url"),
                description=item_data.get("description"),
                wiki_page=wiki_page,
                is_active=True,
            )
            db.add(item)
        else:
            item.type = item_data["type"]
            item.name = item_data["name"]
            item.data = item_data.get("data", {})
            item.image_url = item_data.get("image_url")
            item.description = item_data.get("description")
            item.wiki_page = wiki_page
            item.is_active = True
            item.updated_at = datetime.now(UTC)

    # Soft-delete items from this page that no longer exist on the wiki page.
    # Do not wipe a page when a parser unexpectedly yields no items.
    if slugs:
        await db.execute(
            update(Item)
            .where(
                Item.source_page_id == wiki_page.id,
                Item.slug.notin_(slugs),
            )
            .values(is_active=False)
        )
    else:
        logger.warning("Parser returned no items for %s; keeping existing items active", title)

    wiki_page.last_revision_id = revision_id
    wiki_page.content_hash = content_hash
    wiki_page.last_scraped = datetime.now(UTC)

    await db.commit()
    return True
