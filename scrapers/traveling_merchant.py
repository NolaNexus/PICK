"""Traveling Merchant scraper - parse items sold table from the Traveling Merchant wiki page."""

import re
from typing import Any

import mwparserfromhell


def parse_traveling_merchant(wikitext: str) -> list[dict[str, Any]]:
    """Parse traveling merchant items from wikitext containing the items sold table."""
    tree = mwparserfromhell.parse(wikitext)
    items = []

    # Find all tables
    for table in tree.filter_tags():
        if str(table.tag).strip() != "table":
            continue

        table_text = str(table)
        # Check if this is the merchant stock table
        if "Merchant Stock Info" not in table_text:
            continue

        # Parse rows from the table - each row has 5 cells across 5 lines
        rows = _parse_table_rows(table_text)

        for row in rows:
            if len(row) < 5:
                continue

            item_name = _clean_item_name(row[0])
            if not item_name:
                continue

            chance_str = _extract_cell_value(row[1])
            price_str = row[2]
            shard_str = row[3]
            stock_str = _extract_cell_value(row[4])

            # Parse chance (0 if "-" or removed)
            if chance_str == "-":
                chance_val = 0.0
            else:
                chance_val = _parse_float(chance_str.replace("%", ""))

            price = _parse_currency(price_str)
            shard_price = _parse_shards(shard_str)
            stock_count = _parse_int(stock_str)

            items.append(
                {
                    "id": _slugify(item_name),
                    "type": _classify_item_type(item_name),
                    "name": item_name,
                    "slug": _slugify(item_name),
                    "data": {
                        "chance_percent": chance_val,
                        "price_cash": price,
                        "price_shards": shard_price,
                        "stock": stock_count,
                        "description": "",
                        "image": "",
                    },
                    "image_url": None,
                }
            )

    return items


def _classify_item_type(name: str) -> str:
    """Classify a merchant stock item by the game's item categories.

    Enchant books permanently enchant the player's pan and potions grant timed
    boosts, so they are their own categories. Everything else is a generic
    merchant listing that reconciliation may merge into an existing item.
    """
    lowered = name.lower()
    if lowered.endswith("enchant book"):
        return "enchant_book"
    if lowered.endswith("potion"):
        return "potion"
    return "merchant_item"


def _extract_cell_value(cell: str) -> str:
    """Extract the value from a wiki table cell like 'style="..." | value'."""
    # Find the last | in the cell and return everything after it
    parts = cell.split("|")
    if len(parts) > 1:
        return parts[-1].strip()
    return cell.strip()


def _parse_table_rows(table_text: str) -> list[list[str]]:
    """Parse wikitable rows where each cell is on its own line."""
    rows = []
    current_row = []

    # Split by lines
    lines = table_text.split("\n")

    for line in lines:
        stripped = line.strip()

        # New row marker
        if stripped.startswith("|-"):
            if current_row:
                rows.append(current_row)
                current_row = []
            continue

        # Header cell - skip
        if stripped.startswith("!"):
            continue

        # Data cell
        if stripped.startswith("|"):
            # Extract content after |
            content = stripped[1:].strip()
            current_row.append(content)
            continue

    # Don't forget last row
    if current_row:
        rows.append(current_row)

    return rows


def _clean_item_name(name: str) -> str:
    """Clean item name from wiki markup."""
    # Extract from [[Name]] or [[Name|Display]]
    link_match = re.search(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", name)
    if link_match:
        name = link_match.group(1)
    else:
        # Remove {{Template}} markup but keep the name
        name = re.sub(r"\{\{([^}|]+)(?:\|[^}]*)?\}\}", r"\1", name)
    # Remove ''(Removed...)'' notes
    name = re.sub(r"\s*''\([^)]+\)''", "", name)
    # Clean up
    name = name.strip()
    return name


def _parse_currency(text: str) -> float:
    """Parse currency value from various formats."""
    # Try data-sort-value first
    sort_match = re.search(r'data-sort-value="([^"]+)"', text)
    if sort_match:
        try:
            return float(sort_match.group(1).replace(",", ""))
        except (ValueError, TypeError):
            pass

    # Try {{$|...}} format
    template_match = re.search(r"\{\{\$?\|([^}]+)\}\}", text)
    if template_match:
        try:
            return float(template_match.group(1).replace(",", ""))
        except (ValueError, TypeError):
            pass

    # Try plain number
    try:
        return float(text.replace(",", "").replace("$", "").strip())
    except (ValueError, TypeError):
        return 0.0


def _parse_shards(text: str) -> int:
    """Parse meteor shards price."""
    # Try data-sort-value
    sort_match = re.search(r'data-sort-value="([^"]+)"', text)
    if sort_match:
        try:
            val = sort_match.group(1)
            if val == "Unknown":
                return 0
            return int(val.replace(",", ""))
        except (ValueError, TypeError):
            pass

    # Try {{Meteor Shards|...}} format
    template_match = re.search(r"\{\{Meteor Shards\|([^}]+)\}\}", text)
    if template_match:
        try:
            return int(template_match.group(1).replace(",", ""))
        except (ValueError, TypeError):
            pass

    # Try plain number
    try:
        return int(text.replace(",", "").strip())
    except (ValueError, TypeError):
        return 0


def _parse_int(value: str) -> int:
    try:
        return int(value.strip())
    except (ValueError, TypeError):
        return 0


def _parse_float(value: Any) -> float:
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0


def _slugify(name: str) -> str:
    return (
        name.lower()
        .replace(" ", "-")
        .replace("'", "")
        .replace("(", "")
        .replace(")", "")
        .replace("’", "")
    )
