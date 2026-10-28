"""The scrape survives the wiki refusing to answer.

The wiki is not called. Every page comes from the fixtures in
``tests/fixtures``, so the test says the same thing whether the wiki is
reachable, slow, rate-limited or gone.
"""

from pathlib import Path

import pytest

from app.services import scraper as scraper_service
from app.services.scraper import run_daily_scrape
from app.utils.mw_api import MediaWikiClient
from scrapers import TRACKED_PAGES

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _fixture_path(title: str) -> Path | None:
    """The fixture file for a page, if there is one.

    The fixtures are named after the files the wiki pages are saved under, so
    ``Treasure Chest`` is ``Treasure_Chest.wiki`` and ``Minerals`` is
    ``minerals.wiki``.
    """
    candidates = [
        FIXTURE_DIR / f"{title}.wiki",
        FIXTURE_DIR / f"{title.replace(' ', '_')}.wiki",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    # Fall back to a case-insensitive match.
    wanted = title.replace(" ", "_").lower()
    for path in FIXTURE_DIR.glob("*.wiki"):
        if path.stem.lower() == wanted:
            return path
    return None


def _fixture(title: str) -> str:
    """The wikitext of a page, read from the fixtures."""
    path = _fixture_path(title)
    if path is None:
        pytest.skip(f"no fixture for {title}")
    return path.read_text()


class _OfflineClient(MediaWikiClient):
    """A client that answers from the fixtures and never touches the network.

    ``recent_changes`` is what the test overrides. Everything else the scrape
    needs is answered from a fixture, so the run is the same offline as it is
    against the real wiki.
    """

    async def get_page_info(self, title: str) -> dict:
        return {
            "page_id": abs(hash(title)) % 10000,
            "revision_id": 1,
            "wikitext": _fixture(title),
        }

    async def get_recent_changes(self, days: int = 1, limit: int = 500, namespace: int = 0):
        return [{"title": title} for title in TRACKED_PAGES]

    async def get_pages_with_content(self, titles: list[str]) -> dict[str, str]:
        contents = {}
        for title in titles:
            path = _fixture_path(title)
            if path is not None:
                contents[title] = path.read_text()
        return contents

    async def get_category_members(self, category: str, limit: int = 500) -> list[str]:
        return []

    async def get_image_urls(self, file_names: list[str]) -> dict[str, str]:
        return {name: f"https://example.test/{name}" for name in file_names}

    async def close(self):
        return None


class _BrokenClient(_OfflineClient):
    """A client whose recent-changes listing always fails."""

    async def get_recent_changes(self, days: int = 1, limit: int = 500, namespace: int = 0):
        raise RuntimeError("the wiki is not answering")


class _EmptyClient(_OfflineClient):
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
