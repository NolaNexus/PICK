"""Webhook endpoints for external integrations (MediaWiki, etc.)."""

import hashlib
import hmac
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.services.scraper import scrape_page
from app.utils.mw_api import MediaWikiClient

router = APIRouter(tags=["webhooks"])

logger = logging.getLogger(__name__)


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature from MediaWiki webhook."""
    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/wiki-edit")
async def wiki_edit_webhook(
    request: Request,
    db: AsyncSession = Depends(get_session),  # noqa: B008
    x_mediawiki_signature: str | None = Header(None, alias="X-MediaWiki-Signature"),
):
    """
    Handle MediaWiki edit webhook.

    Expected payload format (from MediaWiki WebHooks extension):
    {
        "wiki": "prospecting",
        "title": "Pans",
        "user": "Username",
        "comment": "Updated stats",
        "timestamp": "2024-01-15T12:34:56Z",
        "url": "https://prospecting.miraheze.org/wiki/Pans?diff=12345"
    }
    """
    # Verify webhook secret if configured
    webhook_secret = getattr(settings, "webhook_secret", None)
    if webhook_secret:
        if not x_mediawiki_signature:
            raise HTTPException(status_code=401, detail="Missing signature header")

        payload = await request.body()
        if not verify_webhook_signature(payload, x_mediawiki_signature, webhook_secret):
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse JSON payload
    try:
        data = await request.json()
    except Exception as e:
        logger.warning("Invalid JSON in webhook: %s", e)
        raise HTTPException(status_code=400, detail="Invalid JSON") from None

    title = data.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="Missing 'title' in payload")

    # Check if this is a tracked page
    from scrapers.registry import TRACKED_PAGES
    if title not in TRACKED_PAGES:
        logger.info("Ignoring webhook for untracked page: %s", title)
        return {"status": "ignored", "reason": "not_tracked"}

    # Trigger targeted scrape
    client = MediaWikiClient()
    try:
        changed = await scrape_page(db, client, title)
        return {
            "status": "ok",
            "page": title,
            "changed": changed,
        }
    except Exception as e:
        logger.error("Failed to scrape %s via webhook: %s", title, e)
        raise HTTPException(status_code=500, detail=f"Scrape failed: {e}") from None
    finally:
        await client.close()
