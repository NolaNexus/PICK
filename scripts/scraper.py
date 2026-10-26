"""CLI entry point for running the daily wiki scraper."""

import argparse
import asyncio

import app.database as app_database
from app.services.scraper import run_daily_scrape, run_full_scrape


async def main(full: bool = False):
    """Run the daily scraper cycle."""
    from app.models import Base

    engine = await app_database.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with app_database.async_session_factory() as session:
        if full:
            result = await run_full_scrape(session)
        else:
            result = await run_daily_scrape(session)
        print(f"Scrape complete: {result}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the PICK wiki scraper")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full scrape of all tracked pages (bypass recentchanges)",
    )
    args = parser.parse_args()
    asyncio.run(main(full=args.full))
