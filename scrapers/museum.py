"""Museum scraper - parse displays and ore bonuses from the Museum wiki page."""

import re
from typing import Any


def parse_museum(wikitext: str) -> list[dict[str, Any]]:
    """Parse museum data from displays table and ore bonus tables."""
    items = []

    # Parse the displays table
    displays = _parse_displays_table(wikitext)
    items.extend(displays)

    # Parse ore bonuses by rarity
    ore_bonuses = _parse_ore_bonuses(wikitext)
    items.extend(ore_bonuses)

    # Add static museum info
    items.append(
        {
            "id": "museum-info",
            "type": "museum_info",
            "name": "Museum",
            "slug": "museum",
            "data": {
                "description": "Indoor location in Caldera Park where players place minerals into display pedestals to earn permanent stat boosts.",
                "location": "Caldera Park",
                "staff": ["Receptionist"],
                "extras": [
                    "Vault",
                    "Voting box (MVP)",
                    "Manage Museums Board",
                    "Visit Museums Globe",
                ],
                "how_it_works": [
                    "Place a mineral matching the display's rarity to grant a permanent stat bonus.",
                    "Each display holds one mineral. Bonuses stack across unlocked displays.",
                    "You can replace a mineral at any time to change the bonus.",
                ],
            },
            "image_url": None,
        }
    )

    return items


def _parse_displays_table(wikitext: str) -> list[dict[str, Any]]:
    """Parse the museum displays table."""
    items = []

    # Find the displays table
    table_match = re.search(
        r'\{\| class="wikitable".*?Displays.*?\n(.*?)\n\|\}', wikitext, re.DOTALL | re.IGNORECASE
    )
    if not table_match:
        return items

    table_body = table_match.group(1)

    # Split by rows
    rows = re.split(r"\n\|\-", table_body)

    for row in rows:
        row = row.strip()
        if not row or row.startswith("!"):
            continue

        # Parse cells (separated by ||)
        cells = [c.strip() for c in row.split("||")]
        if len(cells) < 6:
            continue

        # Cell 0: Rarity (with colored span)
        rarity_cell = cells[0]
        rarity_match = re.search(r"''([^']+)''", rarity_cell)
        if not rarity_match:
            continue
        rarity = rarity_match.group(1).strip()

        # Cell 1: Free Displays
        free_displays = _parse_int(cells[1])

        # Cell 2: Locked Displays
        locked_displays = _parse_int(cells[2])

        # Cell 3: Price (Money)
        money_price = cells[3].strip()

        # Cell 4: Price (Shards)
        shards_price = cells[4].strip()

        # Cell 5: Total Displays
        total_displays = _parse_int(cells[5])

        items.append(
            {
                "id": _slugify(f"museum-display-{rarity}"),
                "type": "museum_display",
                "name": f"{rarity} Display",
                "slug": _slugify(f"museum-display-{rarity}"),
                "data": {
                    "rarity": rarity,
                    "free_displays": free_displays,
                    "locked_displays": locked_displays,
                    "money_price": money_price,
                    "shards_price": shards_price,
                    "total_displays": total_displays,
                },
                "image_url": None,
            }
        )

    return items


def _parse_ore_bonuses(wikitext: str) -> list[dict[str, Any]]:
    """Parse ore bonuses by rarity sections."""
    items = []

    # Find all ore bonus tables - match sections like "=== Common Ores ===" followed by wikitable
    # The headers are wrapped in span tags with style attributes
    rarity_sections = re.findall(
        r"===\s*<span[^>]*>\s*''([^']+Ores)''\s*</span>\s*===\s*\n(\{\| class=\"wikitable\".*?\n\|\})",
        wikitext,
        re.DOTALL,
    )

    for rarity, table_text in rarity_sections:
        rarity = rarity.strip()

        # Parse the table
        table_match = re.search(r"\{(.*?)\n\|\}", table_text, re.DOTALL)
        if not table_match:
            continue

        table_body = table_match.group(1)
        rows = re.split(r"\n\|\-", table_body)

        for row in rows:
            row = row.strip()
            if not row or row.startswith("!"):
                continue

            cells = [c.strip() for c in row.split("||")]
            if len(cells) < 4:
                continue

            # Cell 0: Ore name (with colored span and link)
            ore_cell = cells[0]
            ore_match = re.search(r"\[\[([^\]]+)\]\]", ore_cell)
            if ore_match:
                ore_name = ore_match.group(1)
            else:
                # Try to extract from span
                ore_match = re.search(r"''([^']+)''", ore_cell)
                ore_name = ore_match.group(1) if ore_match else ""

            if not ore_name:
                continue

            # Clean ore name
            ore_name = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", ore_name)
            ore_name = ore_name.strip()

            # Cell 1: Minimum KG
            min_kg = _parse_int(cells[1].replace("||", ""))

            # Cell 2: Bonus (Stat template)
            bonus = cells[2].strip()
            bonus = re.sub(r"\{\{Stat\|([^}]+)\}\}", r"\1", bonus)
            bonus = re.sub(r"\{\{[^}]+\}\}", "", bonus).strip()

            # Cell 3: Maximum Boost
            max_boost = cells[3].strip()

            items.append(
                {
                    "id": _slugify(f"museum-ore-{ore_name}"),
                    "type": "museum_ore",
                    "name": ore_name,
                    "slug": _slugify(f"museum-ore-{ore_name}"),
                    "data": {
                        "rarity": rarity,
                        "min_kg": min_kg,
                        "bonus_stat": bonus,
                        "max_boost": max_boost,
                    },
                    "image_url": None,
                }
            )

    return items


def _parse_int(value: str) -> int:
    """Parse integer from string, handling various formats."""
    if not value:
        return 0
    # Remove currency symbols, commas, etc.
    cleaned = re.sub(r"[^\d\-]", "", value)
    try:
        return int(cleaned)
    except (ValueError, TypeError):
        return 0


def _slugify(name: str) -> str:
    return (
        name.lower()
        .replace(" ", "-")
        .replace("'", "")
        .replace("(", "")
        .replace(")", "")
        .replace("’", "")
        .replace("&", "")
        .replace("#", "")
        .replace("×", "x")
        .replace(":", "")
        .replace("/", "-")
        .replace("[", "")
        .replace("]", "")
        .replace(",", "")
        .replace(".", "")
        .replace("!", "")
        .replace(";", "")
        .replace("×", "x")
        .replace("=", "")
        .replace("?", "")
    )
