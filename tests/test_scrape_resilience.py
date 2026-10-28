"""The scrape survives the wiki refusing to answer."""

import pytest

from app.services import scraper as scraper_service
from app.services.scraper import run_daily_scrape
from app.utils.mw_api import MediaWikiClient


class _BrokenClient(MediaWikiClient):
    """A client whose recent-changes listing always fails."""

    async def get_recent_changes(self, days: int = 1, limit: int = 500, namespace: int = 0):
        raise RuntimeError("the wiki is not answering")


class _EmptyClient(MediaWikiClient):
    """A client that reports no changes at all."""

    async def get_recent_changes(self, days: int = 1, limit: int = 500, namespace: int = 0):
        return []


@pytest.mark.asyncio
async def test_a_broken_change_listing_falls_back_to_every_page(db_session, monkeypatch):
    """A wiki that cannot list changes is scraped in full instead of failing."""
    monkeypatch.setattr(scraper_service, "MediaWikiClient", _BrokenClient)

    result = await run_daily_scrape(db_session)

    assert result["status"] == "success"
    # Every tracked page was scraped rather than none.
    assert result["pages_scraped"] > 20


@pytest.mark.asyncio
async def test_an_empty_change_listing_falls_back_to_every_page(db_session, monkeypatch):
    """A wiki that reports no changes is scraped in full rather than doing nothing."""
    monkeypatch.setattr(scraper_service, "MediaWikiClient", _EmptyClient)

    result = await run_daily_scrape(db_session)

    assert result["status"] == "success"
    assert result["pages_scraped"] > 20
