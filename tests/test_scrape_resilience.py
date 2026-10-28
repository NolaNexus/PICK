"""The scrape survives the wiki refusing to answer.

The wiki is not called. Every page comes from the fixtures in
``tests/fixtures``, so the test says the same thing whether the wiki is
reachable, slow, rate-limited or gone. That matters: a GitHub runner is
answered with ``403 Forbidden`` for every request, and a test that asks the
real wiki fails there while passing at home.
"""

from pathlib import Path

import pytest

from app.services import scraper as scraper_service
from app.services.scraper import run_daily_scrape
from app.utils.mw_api import MediaWikiClient
from scrapers import PARSERS, TRACKED_PAGES

FIXTURE_DIR = Path(__file__).parent / "fixtures"

# Every page needs its own page id, exactly like the wiki gives each page its
# own. Two pages sharing an id violates ix_wiki_pages_page_id.
PAGE_IDS = {title: index for index, title in enumerate(sorted(TRACKED_PAGES), start=1)}

# Pages without a parser are counted as scraped but never fetched. PARSERS
# holds a None entry for those, so test the value, not the key.
FETCHED_PAGES = {title for title in TRACKED_PAGES if PARSERS.get(title)}

# The pages the client was asked to read, in order. run_daily_scrape creates
# one client to check for a game update and another to scrape, so the record
# has to live outside the instance.
_requested: list[str] = []


def _fixture_path(title: str) -> Path:
    """The fixture file for a page.

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

    wanted = title.replace(" ", "_").lower()
    for path in FIXTURE_DIR.glob("*.wiki"):
        if path.stem.lower() == wanted:
            return path

    pytest.fail(f"no fixture for {title}; add tests/fixtures/{title}.wiki")


def _fixture(title: str) -> str:
    """The wikitext of a page, read from the fixtures."""
    return _fixture_path(title).read_text()


class _FixtureClient(MediaWikiClient):
    """A client that answers from the fixtures and never touches the network."""

    async def get_page_info(self, title: str) -> dict:
        _requested.append(title)

        # The Changelog is read to detect a new game version. Returning it
        # empty keeps check_for_game_update from starting a full scrape, so
        # the incremental path - the one under test - is the one that runs.
        if title == "Changelog":
            return {"page_id": PAGE_IDS.get(title, 1), "revision_id": 1, "wikitext": ""}

        return {
            "page_id": PAGE_IDS[title],
            "revision_id": 1,
            "wikitext": _fixture(title),
        }

    async def get_recent_changes(self, days: int = 1, limit: int = 500, namespace: int = 0):
        return [{"title": title} for title in TRACKED_PAGES]

    async def get_pages_with_content(self, titles: list[str]) -> dict[str, str]:
        contents = {}
        for title in titles:
            path = FIXTURE_DIR / "item_pages" / f"{title.replace(' ', '_')}.wiki"
            if path.exists():
                contents[title] = path.read_text()
        return contents

    async def get_category_members(self, category: str, limit: int = 500) -> list[str]:
        return []

    async def get_image_urls(self, file_names: list[str]) -> dict[str, str]:
        return {name: f"https://example.test/{name}" for name in file_names}

    async def close(self):
        return None


class _BrokenClient(_FixtureClient):
    """A client whose recent-changes listing always fails."""

    async def get_recent_changes(self, days: int = 1, limit: int = 500, namespace: int = 0):
        raise RuntimeError("the wiki is not answering")


class _EmptyClient(_FixtureClient):
    """A client that reports no changes at all."""

    async def get_recent_changes(self, days: int = 1, limit: int = 500, namespace: int = 0):
        return []


@pytest.fixture(autouse=True)
def _clear_request_log():
    _requested.clear()
    yield
    _requested.clear()


@pytest.mark.asyncio
async def test_a_broken_change_listing_falls_back_to_every_page(db_session, monkeypatch):
    """A wiki that cannot list changes is scraped in full instead of failing."""
    monkeypatch.setattr(scraper_service, "MediaWikiClient", _BrokenClient)

    result = await run_daily_scrape(db_session)

    assert result["status"] == "success"
    assert result["pages_scraped"] == len(TRACKED_PAGES)
    # Every tracked page was read, not a subset.
    assert set(_requested) == FETCHED_PAGES | {"Changelog"}


@pytest.mark.asyncio
async def test_an_empty_change_listing_falls_back_to_every_page(db_session, monkeypatch):
    """A wiki that reports no changes is scraped in full rather than doing nothing."""
    monkeypatch.setattr(scraper_service, "MediaWikiClient", _EmptyClient)

    result = await run_daily_scrape(db_session)

    assert result["status"] == "success"
    assert result["pages_scraped"] == len(TRACKED_PAGES)
    assert set(_requested) == FETCHED_PAGES | {"Changelog"}
