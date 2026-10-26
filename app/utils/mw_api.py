"""MediaWiki API client for fetching wikitext, recentchanges, and metadata."""

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

WIKIPEDIA_API_URL = settings.mediawiki_api_url


class MediaWikiClient:
    """Async client for the MediaWiki API with rate-limit and maxlag handling."""

    def __init__(self, base_url: str = WIKIPEDIA_API_URL, timeout: float = 30.0):
        self.base_url = base_url
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"User-Agent": settings.reddit_user_agent},
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_wikitext(self, title: str) -> str:
        """Fetch raw wikitext for a page by title."""
        client = await self._get_client()
        params = {
            "action": "parse",
            "page": title,
            "prop": "wikitext",
            "format": "json",
            "formatversion": "2",
        }
        resp = await client.get("/", params=params)
        resp.raise_for_status()
        data = resp.json()
        # formatversion=2 returns wikitext as a string, not a dict
        wikitext = data.get("parse", {}).get("wikitext", "")
        if isinstance(wikitext, dict):
            return wikitext.get("*", "")
        return wikitext or ""

    async def get_page_info(self, title: str) -> dict[str, Any]:
        """Fetch page ID, revision ID, and wikitext for a title."""
        client = await self._get_client()
        params = {
            "action": "parse",
            "page": title,
            "prop": "wikitext",
            "format": "json",
            "formatversion": "2",
        }
        resp = await client.get("/", params=params)
        resp.raise_for_status()
        data = resp.json()
        wikitext = data.get("parse", {}).get("wikitext", "")
        if isinstance(wikitext, dict):
            wikitext = wikitext.get("*", "")
        return {
            "page_id": data.get("parse", {}).get("pageid"),
            "revision_id": data.get("parse", {}).get("revid"),
            "wikitext": wikitext or "",
        }

    async def get_recent_changes(
        self,
        days: int = 1,
        limit: int = 500,
        namespace: int = 0,
    ) -> list[dict[str, Any]]:
        """Fetch recent changes in the main namespace for the past N days."""
        client = await self._get_client()
        params = {
            "action": "query",
            "list": "recentchanges",
            "rcprop": "title|ids|timestamp|user|comment|pagecount",
            "rcnamespace": str(namespace),
            "rcdays": str(days),
            "rclimit": str(limit),
            "format": "json",
            "formatversion": "2",
        }
        resp = await client.get("/", params=params)
        resp.raise_for_status()
        data = resp.json()
        changes = data.get("query", {}).get("recentchanges", [])
        logger.info("Fetched %d recent changes from wiki", len(changes))
        return changes

