"""CLI entry point for fetching Reddit news and storing in database."""

import asyncio

import app.database as app_database
from app.services.news_scraper import fetch_reddit_news


async def main():
    """Fetch latest Reddit news and store in database."""
    engine = await app_database.get_engine()
    async with engine.begin():
        pass  # tables already created

    async with app_database.async_session_factory() as session:
        results = await fetch_reddit_news(session)
        for r in results[:3]:
            print(f"  - {r['title'][:60]} ...")


if __name__ == "__main__":
    asyncio.run(main())
