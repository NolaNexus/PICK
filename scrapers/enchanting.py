"""Enchanting scraper - parse <tabber> Pans/Shovels tables from the Enchanting wiki page."""

import re
from typing import Any

from scrapers.stats import parse_modifier_list
from scrapers.types import ParsedItem


def parse_enchanting(wikitext: str) -> list[ParsedItem]:
    """Parse enchantment data from tabber sections (Pans + Shovels)."""
    items: list[ParsedItem] = []

    # Find tabber sections
    tabber_pattern = r"<tabber>(.*?)</tabber>"
    tabber_match = re.search(tabber_pattern, wikitext, re.DOTALL)
    if not tabber_match:
        return items

    tabber_content = tabber_match.group(1)

    # Parse each tab: |-| TabName = content
    tab_pattern = r"\|\-\|\s*([^=]+)\s*=(.*?)(?=\|\-\||$)"
    tab_matches = re.finditer(tab_pattern, tabber_content, re.DOTALL)

    for tab_match in tab_matches:
        tab_name = tab_match.group(1).strip()
        tab_content = tab_match.group(2).strip()

        if not tab_name:
            continue

        # Determine applies_to based on tab name
        applies_to = (
            "pan"
            if "pan" in tab_name.lower()
            else "shovel"
            if "shovel" in tab_name.lower()
            else "unknown"
        )

        # Parse the wikitable in this tab
        table_items = _parse_enchantment_table(tab_content, applies_to)
        items.extend(table_items)

    return items


def _parse_enchantment_table(table_content: str, applies_to: str) -> list[ParsedItem]:
    """Parse a single enchantment wikitable."""
    items: list[ParsedItem] = []

    # Find the wikitable - handle "wikitable sortable" and other variations
    table_match = re.search(r"\{\| class=\"wikitable[^\"]*\"(.*?)\|\}", table_content, re.DOTALL)
    if not table_match:
        return items

    table_body = table_match.group(1)

    # Split by rows (|-) - each row starts with |-
    rows = re.split(r"\n\|\-", table_body)

    for row in rows:
        row = row.strip()
        if not row or row.startswith("!"):
            continue

        item = _parse_enchantment_row(row, applies_to)
        if item:
            items.append(item)

    return items


def _parse_enchantment_row(row: str, applies_to: str) -> ParsedItem | None:
    """Parse a single enchantment row from the table.

    Each row has cells on separate lines, each starting with |.
    The cell content may contain | characters in HTML/style attributes.
    """
    # Split by lines and collect cells that start with |
    lines = row.split("\n")
    cells: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            # Extract content after the first |
            content = stripped[1:].strip()
            cells.append(content)

    # Pans table has 6 columns, Shovels has 5
    min_cells = 6 if applies_to == "pan" else 5
    if len(cells) < min_cells:
        return None

    # Cell 0: Enchant name template
    name_cell = cells[0]
    name_match = re.search(r"\{\{Enchant\|([^}|]+)", name_cell)
    if not name_match:
        return None
    name = name_match.group(1).strip()

    # Cell 1: Effects
    effects = cells[1].strip()
    # Clean up HTML/classes
    effects = re.sub(r'class="[^"]*"', "", effects)
    effects = re.sub(r'style="[^"]*"', "", effects)
    effects = re.sub(r"\{\{Stat\|([^}]+)\}\}", r"\1", effects)
    effects = re.sub(r"<[^>]+>", "", effects)
    effects = effects.strip()

    # The stats the enchantment grants, e.g. "+25 Capacity".
    modifiers = parse_modifier_list(effects)

    if applies_to == "pan":
        # Pans: Aurorite, Aetherite, Aetherium, Source
        chance1 = _parse_chance(cells[2])  # Aurorite
        chance2 = _parse_chance(cells[3])  # Aetherite
        chance3 = _parse_chance(cells[4])  # Aetherium
        source = cells[5].strip()
        aurorite_chance = chance1
        aetherite_chance = chance2
        aetherium_chance = chance3
        sol_chance = None
    else:
        # Shovels: Aetherite, Aetherium, SoL
        chance1 = _parse_chance(cells[2])  # Aetherite
        chance2 = _parse_chance(cells[3])  # Aetherium
        chance3 = _parse_chance(cells[4])  # SoL
        source = ""
        aurorite_chance = None
        aetherite_chance = chance1
        aetherium_chance = chance2
        sol_chance = chance3

    # Clean source
    source = re.sub(r"<[^>]+>", "", source)
    source = re.sub(r"\{\{[^}]+\}\}", "", source)
    source = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", source)
    source = source.strip()

    # Determine rarity from enchant name
    rarity = _determine_rarity(name)

    data: dict[str, Any] = {
        "applies_to": applies_to,
        "effects": effects,
        "aurorite_chance": aurorite_chance,
        "aetherite_chance": aetherite_chance,
        "aetherium_chance": aetherium_chance,
        "sol_chance": sol_chance,
        "source": source,
        "rarity": rarity,
    }
    if modifiers:
        data["modifiers"] = modifiers

    return {
        "id": _slugify(name),
        "type": "enchantment",
        "name": name,
        "slug": _slugify(name),
        "data": data,
        "image_url": None,
    }


def _parse_chance(text: str) -> str:
    """Parse chance value from table cell."""
    # Remove HTML and extract the percentage
    text = re.sub(r'style="[^"]*"', "", text)
    text = re.sub(r"<span[^>]*>.*?</span>", "", text)
    text = re.sub(r"<!--.*?-->", "", text)
    text = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", text)
    text = text.strip()

    # Extract percentage
    pct_match = re.search(r"([\d.]+%)", text)
    if pct_match:
        return pct_match.group(1)

    # Check for "Locked" or "Not locked"
    if "locked" in text.lower():
        return "Locked"

    return text


def _determine_rarity(name: str) -> str:
    """Determine enchantment rarity from name."""
    # Common enchants
    common = {
        "Forceful",
        "Strong",
        "Swift",
        "Lucky",
        "Boosting",
        "Crystal Touch",
        "Excavating",
        "Geothermal",
        "Toughened",
        "Well Balanced",
        "Treasure Hunter",
    }
    # Uncommon enchants
    uncommon = {
        "Destructive",
        "Gigantic",
        "Glowing",
        "Greedy",
        "Unstable",
        "Non Euclidean",
        "Overdrive",
        "Rhythmic",
        "Synergized",
        "Wormhole",
    }
    # Rare enchants
    rare = {"Blessed", "Midas", "Titanic", "Mastered", "Mythical", "Tempered", "Void Touched"}
    # Mythic/Exotic
    mythic = {
        "Cosmic",
        "Divine",
        "Infernal",
        "Prismatic",
        "Cursed",
        "Devouring",
        "Hyperspeed",
        "Irregular",
        "Mystical",
        "Starstruck",
    }

    if name in mythic:
        return "mythic"
    elif name in rare:
        return "rare"
    elif name in uncommon:
        return "uncommon"
    elif name in common:
        return "common"
    return "unknown"


def _slugify(name: str) -> str:
    return (
        name.lower()
        .replace(" ", "-")
        .replace("'", "")
        .replace("(", "")
        .replace(")", "")
        .replace("|", "")
        .replace("’", "")
    )
