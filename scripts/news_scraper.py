"""CLI entry point for fetching Reddit news and storing in database."""

import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from app.database import async_session_factory
from app.services.news_scraper import fetch_reddit_news


async def main():
    """Fetch latest Reddit news and store in database."""
    engine = create_async_engine(
        "postgresql+asyncpg://postgres:postgres@localhost/pick",
        echo=False,
    )

    async with engine.begin():
        pass  # tables already created

    async with async_session_factory() as session:
        results = await fetch_reddit_news(session)
        print(f"Fetched {len(results)} Reddit posts")
        for r in results[:3]:
            print(f"  - {r['title'][:60]} ...")


if __name__ == "__main__":
    asyncio.run(main())
