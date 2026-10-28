"""Report how much of each wiki page the scraper actually captures.

The scraper only stores the items a parser recognises. When a page lists more
rows than the parser returns, some items are missing from the site without
anything failing.

This script compares the rows in each tracked page's tables with the number of
items the parser produced, and looks for pages that look like item lists but
are not tracked at all.

It is a report: gaps never fail the run, because counting rows in a wiki
table is a heuristic and the wiki itself can be unavailable.
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

# A wikitable row separator.
_ROW_SEPARATOR = re.compile(r"^\s*\|\-", re.MULTILINE)

# A table that holds the header row of a list.
_TABLE_START = re.compile(r"\{\|", re.MULTILINE)

# A column header that names the thing in the row.
_ITEM_HEADER = re.compile(r"!\s*(?:style=\"[^\"]*\"\s*\|\s*)?item\b", re.IGNORECASE)


def count_table_rows(wikitext: str) -> int:
    """Count the data rows of the tables in a page."""
    rows = 0
    for table in _split_tables(wikitext):
        # The header row is separated with '!', so only '|-' rows count.
        rows += len(_ROW_SEPARATOR.findall(table))
    return rows


def _split_tables(wikitext: str) -> list[str]:
    """Split a page into its wikitables."""
    tables: list[str] = []
    start = None
    depth = 0

    for index, char in enumerate(wikitext):
        if char == "{" and wikitext[index : index + 2] == "{|":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                tables.append(wikitext[start : index + 1])
                start = None

    return tables


def looks_like_item_list(wikitext: str) -> bool:
    """Return True when a page holds a table that lists items."""
    for table in _split_tables(wikitext):
        if _ITEM_HEADER.search(table):
            return True
    return False


async def build_report(
    client: MediaWikiClient,
    tracked: list[str],
    check_untracked: bool,
) -> dict[str, Any]:
    """Build the coverage report."""
    pages: list[dict[str, Any]] = []
    errors: list[str] = []

    for title in tracked:
        parser = PARSERS.get(title)
        try:
            info = await client.get_page_info(title)
        except Exception as exc:
            errors.append(f"{title}: {exc}")
            continue

        wikitext = info.get("wikitext", "")
        rows = count_table_rows(wikitext)
        tables = len(_split_tables(wikitext))

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

        known = {title.lower() for title in tracked}
        for title in all_pages:
            if title.lower() in known:
                continue
            try:
                info = await client.get_page_info(title)
            except Exception:
                continue

            wikitext = info.get("wikitext", "")
            if not looks_like_item_list(wikitext):
                continue

            untracked.append({"page": title, "table_rows": count_table_rows(wikitext)})

    return {"pages": pages, "untracked": untracked, "errors": errors}


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

    if report["untracked"]:
        lines.append("")
        lines.append("### Pages that look like item lists but are not tracked")
        lines.append("")
        for page in report["untracked"]:
            lines.append(f"- {page['page']} ({page['table_rows']} table rows)")

    if report["errors"]:
        lines.append("")
        lines.append("### Errors")
        lines.append("")
        for error in report["errors"]:
            lines.append(f"- {error}")

    return "\n".join(lines)


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
    args = parser.parse_args()

    client = MediaWikiClient()
    try:
        report = await build_report(client, TRACKED_PAGES, not args.no_untracked)
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

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
