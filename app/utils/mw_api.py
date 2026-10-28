"""MediaWiki API client for fetching wikitext, recentchanges, and metadata."""

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

WIKIPEDIA_API_URL = settings.mediawiki_api_url

# How many file names are looked up in one request.
IMAGE_BATCH_SIZE = 50


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

    async def get_all_pages(self, limit: int = 500) -> list[str]:
        """List the titles of every page in the wiki's main namespace."""
        client = await self._get_client()
        titles: list[str] = []
        continuation: str | None = None

        while True:
            params: dict[str, Any] = {
                "action": "query",
                "list": "allpages",
                "aplimit": str(limit),
                "apnamespace": "0",
                "format": "json",
                "formatversion": "2",
            }
            if continuation:
                params["apcontinue"] = continuation

            resp = await client.get("/", params=params)
            resp.raise_for_status()
            data = resp.json()

            for page in data.get("query", {}).get("allpages", []):
                title = page.get("title")
                if title:
                    titles.append(title)

            continuation = data.get("continue", {}).get("apcontinue")
            if not continuation:
                break

        logger.info("Listed %d wiki pages", len(titles))
        return titles

    async def get_image_urls(self, file_names: list[str]) -> dict[str, str]:
        """Resolve wiki file names to their URLs.

        The names are looked up in batches, so a page with many items only
        costs a couple of requests. Names that do not exist are left out.
        """
        if not file_names:
            return {}

        client = await self._get_client()
        wanted = [name for name in dict.fromkeys(file_names) if name]
        resolved: dict[str, str] = {}

        for start in range(0, len(wanted), IMAGE_BATCH_SIZE):
            batch = wanted[start : start + IMAGE_BATCH_SIZE]
            params = {
                "action": "query",
                "titles": "|".join(f"File:{name}" for name in batch),
                "prop": "imageinfo",
                "iiprop": "url",
                "format": "json",
                "formatversion": "2",
            }
            resp = await client.get("/", params=params)
            resp.raise_for_status()
            data = resp.json()

            for page in data.get("query", {}).get("pages", []):
                title = page.get("title", "")
                if not title.startswith("File:"):
                    continue
                info = page.get("imageinfo") or []
                if not info:
                    continue
                url = info[0].get("url")
                if url:
                    resolved[title[5:]] = url

        logger.info("Resolved %d of %d image names", len(resolved), len(wanted))
        return resolved
