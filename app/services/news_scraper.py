"""Reddit news scraper - fetch posts from configured subreddit and upsert into DB."""

import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select

from app.config import settings
from app.models import News

logger = logging.getLogger(__name__)

REDDIT_API_URL = "https://oauth.reddit.com"
REDDIT_PUBLIC_API_URL = "https://www.reddit.com"
REDDIT_AUTH_URL = "https://www.reddit.com/api/v1/access_token"
REDDIT_USER_AGENT = settings.reddit_user_agent


def _infer_tags(title: str, content: str) -> list[str]:
    """Infer tags for a news post based on title and content keywords."""
    tags = []
    text = (title + " " + content).lower()
    keyword_map = {
        "patch": ["patch", "update", "version", "changelog", "hotfix"],
        "event": ["event", "limited", "seasonal", "holiday", "special"],
        "announcement": ["announcement", "release", "launch", "news"],
        "guide": ["guide", "tutorial", "tips", "how to"],
        "discussion": ["discussion", "question", "help", "advice"],
    }
    for tag, keywords in keyword_map.items():
        if any(kw in text for kw in keywords):
            tags.append(tag)
    if not tags:
        tags.append("general")
    return tags


async def _get_access_token(client: httpx.AsyncClient) -> str | None:
    """Obtain OAuth2 access token via client credentials grant.

    Returns None if Reddit client credentials are not configured.
    """
    client_id = settings.reddit_client_id
    client_secret = settings.reddit_client_secret
    if not client_id or not client_secret:
        logger.warning(
            "Reddit client_id/client_secret not configured; skipping OAuth2 auth"
        )
        return None

    auth = (client_id, client_secret)
    data = {"grant_type": "client_credentials"}
    headers = {"User-Agent": REDDIT_USER_AGENT}

    try:
        resp = await client.post(
            REDDIT_AUTH_URL, data=data, auth=auth, headers=headers, timeout=30.0
        )
        resp.raise_for_status()
        token_data = resp.json()
        return token_data.get("access_token")
    except Exception as e:
        logger.error("Failed to obtain Reddit access token: %s", e)
        return None


async def fetch_reddit_news(
    db: Any,
    subreddit: str | None = None,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Fetch latest Reddit posts from the configured subreddit and upsert into DB.

    Args:
        db: Async SQLAlchemy session.
        subreddit: Subreddit name (defaults to settings.reddit_subreddit).
        limit: Number of posts to fetch (max 100).

    Returns:
        List of newly inserted news article dicts.
    """
    subreddit = subreddit or settings.reddit_subreddit
    params = {"limit": min(limit, 100), "raw_json": 1}
    headers = {"User-Agent": REDDIT_USER_AGENT}

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        token = await _get_access_token(client)

        if token:
            # Authenticated: use OAuth endpoint
            client.headers["Authorization"] = f"Bearer {token}"
            base_url = REDDIT_API_URL
        else:
            # Unauthenticated: use public endpoint
            base_url = REDDIT_PUBLIC_API_URL

        url = f"{base_url}/r/{subreddit}/new.json"

        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401 and token is None:
                logger.error(
                    "Reddit API returned 401 Unauthorized. Configure REDDIT_CLIENT_ID "
                    "and REDDIT_CLIENT_SECRET in .env for OAuth2 authentication."
                )
            raise
        except httpx.HTTPError as e:
            logger.error("Failed to fetch Reddit posts from r/%s: %s", subreddit, e)
            raise

    children = data.get("data", {}).get("children", [])
    logger.info("Fetched %d Reddit posts from r/%s", len(children), subreddit)

    inserted: list[dict[str, Any]] = []

    for child in children:
        post = child.get("data", {})
        post_id = post.get("id")
        if not post_id:
            continue

        title = post.get("title", "")
        post_url = post.get("url", "")
        author = post.get("author", "")
        score = post.get("score", 0)
        created_utc = post.get("created_utc", 0)
        content = post.get("selftext", "")
        flair = post.get("link_flair_text", "")

        published_at = (
            datetime.fromtimestamp(created_utc, tz=UTC) if created_utc else datetime.now(UTC)
        )
        tags = _infer_tags(title, content + " " + (flair or ""))

        existing = await db.execute(
            select(News).where(News.external_id == post_id)
        )
        existing_article = existing.scalar_one_or_none()

        if existing_article:
            existing_article.score = score
            existing_article.tags = tags
            existing_article.fetched_at = datetime.now(UTC)
            db.add(existing_article)
            continue

        article = News(
            source="reddit",
            external_id=post_id,
            title=title,
            url=post_url,
            author=author,
            score=score,
            published_at=published_at,
            content=content,
            tags=tags,
        )
        db.add(article)
        inserted.append(
            {
                "id": post_id,
                "title": title,
                "url": post_url,
                "author": author,
                "score": score,
                "tags": tags,
            }
        )

    await db.commit()
    logger.info("Inserted %d new Reddit news articles", len(inserted))
    return inserted
