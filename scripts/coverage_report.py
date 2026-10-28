"""Report what the site is missing from the wiki.

The scraper only stores the items a parser recognises. When a page lists more
rows than the parser returns, or an item has a page of its own that no index
page mentions, items are missing from the site without anything failing.

The report uses the wiki's page list, its categories and the rows of the
tracked pages to find them. It is a report: gaps never fail the run, because
classifying a page is a heuristic and the wiki itself can be unavailable.
"""

import argparse
import asyncio
import json
import os
import re
import sys
from typing import Any

from app.utils.mw_api import MediaWikiClient
from scrapers import PARSERS, TRACKED_PAGES  # type: ignore
from scrapers.pages import (
    categories_of,
    is_index_page,
    is_item_page,
    item_type_hint,
    split_tables,
)
from scrapers.wikitext import title_key

ALLOWLIST_PATH = os.path.join(os.path.dirname(__file__), "coverage_allowlist.json")

# A wikitable row separator.
_ROW_SEPARATOR = re.compile(r"^\s*\|\-", re.MULTILINE)


def load_allowlist(path: str = ALLOWLIST_PATH) -> set[str]:
    """Read the pages that are known not to hold item data."""
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return set()

    return {title_key(page) for page in payload.get("pages", [])}


def count_table_rows(wikitext: str) -> int:
    """Count the data rows of the tables in a page."""
    rows = 0
    for table in split_tables(wikitext):
        # The header row is separated with '!', so only '|-' rows count.
        rows += len(_ROW_SEPARATOR.findall(table))
    return rows


async def build_report(
    client: MediaWikiClient,
    tracked: list[str],
    check_untracked: bool,
    allowlist: set[str],
) -> dict[str, Any]:
    """Build the coverage report."""
    pages: list[dict[str, Any]] = []
    errors: list[str] = []
    missing_items: list[dict[str, Any]] = []

    # The names we already have, so a page can be matched to its item.
    known_names = await _scraped_names(client)

    for title in tracked:
        parser = PARSERS.get(title)
        try:
            info = await client.get_page_info(title)
        except Exception as exc:
            errors.append(f"{title}: {exc}")
            continue

        wikitext = info.get("wikitext", "")
        rows = count_table_rows(wikitext)
        tables = len(split_tables(wikitext))

        if parser is None:
            pages.append(
                {
                    "page": title,
                    "status": "no parser",
                    "table_rows": rows,
                    "items": 0,
                    "missing": max(rows - tables, 0),
                }
            )
            continue

        try:
            items = parser(wikitext)
        except Exception as exc:
            errors.append(f"{title}: parser failed: {exc}")
            continue

        # Every table contributes a header row, which is not an item.
        expected = max(rows - tables, 0)
        missing = max(expected - len(items), 0)

        pages.append(
            {
                "page": title,
                "status": "tracked",
                "table_rows": rows,
                "items": len(items),
                "missing": missing,
            }
        )

    untracked: list[dict[str, Any]] = []
    if check_untracked:
        try:
            all_pages = await client.get_all_pages()
        except Exception as exc:
            errors.append(f"could not list the wiki pages: {exc}")
            all_pages = []

        tracked_keys = {title_key(title) for title in tracked}
        candidates = [
            title
            for title in all_pages
            if title_key(title) not in tracked_keys and title_key(title) not in allowlist
        ]

        # The content is fetched in batches, so a few hundred pages cost a
        # handful of requests.
        contents = await client.get_pages_with_content(candidates)

        for title, wikitext in contents.items():
            if is_index_page(wikitext) and not is_item_page(wikitext):
                untracked.append({"page": title, "table_rows": count_table_rows(wikitext)})
                continue

            if is_item_page(wikitext):
                item_type = item_type_hint(wikitext, title)
                if item_type and title_key(title) not in known_names:
                    missing_items.append(
                        {
                            "page": title,
                            "type": item_type,
                            "categories": sorted(categories_of(wikitext)),
                        }
                    )

    return {
        "pages": pages,
        "untracked": untracked,
        "missing_items": missing_items,
        "unmatched_places": await _unmatched_places(),
        "errors": errors,
    }


async def _unmatched_places() -> list[str]:
    """Return the places minerals name that no area holds.

    A place without an area cannot be filtered by area, so it is worth
    knowing about.
    """
    try:
        from sqlalchemy import select

        import app.database as app_database
        from app.models import Item

        await app_database.get_engine()
        factory = await app_database.get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(Item.name, Item.data).where(
                    Item.is_active.is_(True),
                    Item.type == "mineral",
                )
            )
            rows = result.all()
    except Exception:
        return []

    places: set[str] = set()
    for _name, data in rows:
        if not isinstance(data, dict):
            continue
        if data.get("areas"):
            continue
        locations = data.get("locations")
        if isinstance(locations, list):
            for location in locations:
                if isinstance(location, str) and location.strip():
                    places.add(location.strip())

    return sorted(places)


async def _scraped_names(client: MediaWikiClient) -> set[str]:
    """Return the names of the items the site already has.

    The names are read from the database when it is reachable. Without it the
    report can still say which pages hold items, but not which are missing.
    """
    try:
        from sqlalchemy import select

        import app.database as app_database
        from app.models import Item

        await app_database.get_engine()
        factory = await app_database.get_session_factory()
        async with factory() as session:
            result = await session.execute(select(Item.name).where(Item.is_active.is_(True)))
            names = {title_key(name) for name in result.scalars().all() if name}
        return names
    except Exception:
        return set()


def render_markdown(report: dict[str, Any]) -> str:
    """Render the report as Markdown."""
    lines: list[str] = []
    lines.append("## Item coverage")
    lines.append("")

    # A page is either missing rows or has no parser at all, never both.
    gaps = [page for page in report["pages"] if page["missing"] > 0]
    no_parser = [
        page for page in report["pages"] if page["status"] == "no parser" and page["missing"] == 0
    ]

    if not gaps and not no_parser:
        lines.append("Every tracked page is fully captured.")
    else:
        lines.append("| Page | Table rows | Items | Missing |")
        lines.append("| --- | ---: | ---: | ---: |")
        for page in sorted(gaps + no_parser, key=lambda p: -p["missing"]):
            lines.append(
                f"| {page['page']} | {page['table_rows']} | {page['items']} | {page['missing']} |"
            )

    if report.get("missing_items"):
        lines.append("")
        lines.append("### Items that have a page but are not on the site")
        lines.append("")
        lines.append("| Page | Type | Categories |")
        lines.append("| --- | --- | --- |")
        for item in sorted(report["missing_items"], key=lambda i: (i["type"], i["page"])):
            categories = ", ".join(item.get("categories", []))
            lines.append(f"| {item['page']} | {item['type']} | {categories} |")

    if report["untracked"]:
        lines.append("")
        lines.append("### Pages that look like item lists but are not tracked")
        lines.append("")
        for page in report["untracked"]:
            lines.append(f"- {page['page']} ({page['table_rows']} table rows)")

    if report.get("unmatched_places"):
        lines.append("")
        lines.append("### Places with no area")
        lines.append("")
        lines.append("Minerals name these places, but no area holds them:")
        lines.append("")
        for place in report["unmatched_places"]:
            lines.append(f"- {place}")

    if report["errors"]:
        lines.append("")
        lines.append("### Errors")
        lines.append("")
        for error in report["errors"]:
            lines.append(f"- {error}")

    return "\n".join(lines)


def has_gaps(report: dict[str, Any]) -> bool:
    """Return True when the report found something missing."""
    if report.get("missing_items"):
        return True
    if report.get("untracked"):
        return True
    return any(page["missing"] > 0 for page in report.get("pages", []))


async def main() -> int:
    parser = argparse.ArgumentParser(description="Report the scraper's page coverage")
    parser.add_argument(
        "--no-untracked",
        action="store_true",
        help="Skip the scan for untracked pages that look like item lists",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the report as JSON instead of Markdown",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with a failure when a gap is found",
    )
    args = parser.parse_args()

    client = MediaWikiClient()
    try:
        report = await build_report(
            client,
            TRACKED_PAGES,
            not args.no_untracked,
            load_allowlist(),
        )
    finally:
        await client.close()

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_markdown(report))

    # The report is written to the job summary when it runs in GitHub Actions.
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write(render_markdown(report))
            summary.write("\n")

    if args.strict and has_gaps(report):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
