"""CLI entry point for running the daily wiki scraper."""

import argparse
import asyncio
import sys

import app.database as app_database
from app.services.scraper import run_daily_scrape, run_full_scrape


async def main(full: bool = False) -> int:
    """Run the scraper and report whether it produced anything.

    A run that scrapes no pages is a failure, not a success. The wiki can
    answer every request with an error (a blocked address, for instance) and
    the scrape still completes, so without this check the pipeline would
    publish the empty database over the real data.
    """
    from app.models import Base

    engine = await app_database.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = await app_database.get_session_factory()
    async with factory() as session:
        if full:
            result = await run_full_scrape(session)
        else:
            result = await run_daily_scrape(session)
        print(f"Scrape complete: {result}")

    if result["pages_ok"] == 0:
        print(
            "Scrape reached no page; refusing to report success. "
            "Nothing will be published from this run.",
            file=sys.stderr,
        )
        return 1

    return 0


def run() -> int:
    """The console script entry point.

    ``main`` is a coroutine, so a console script cannot call it directly: it
    would get a coroutine back and never run it. This runs it and turns the
    result into an exit code.
    """
    return asyncio.run(main(full="--full" in sys.argv[1:]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the PICK wiki scraper")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full scrape of all tracked pages (bypass recentchanges)",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(main(full=args.full)))
