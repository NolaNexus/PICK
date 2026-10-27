"""CLI entry point for fetching Reddit news and storing in database."""

import asyncio

import app.database as app_database
from app.services.news_scraper import fetch_reddit_news


async def main():
    """Fetch latest Reddit news and store in database."""
    from app.models import Base

    engine = await app_database.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with app_database.async_session_factory() as session:
        results = await fetch_reddit_news(session)
        print(f"News scrape complete: {len(results)} new articles")
        for r in results[:3]:
            print(f"  - {r['title'][:60]} ...")


if __name__ == "__main__":
    asyncio.run(main())
