"""Excavations scraper - parse Excavation Sites, Levels, and Rewards from the Excavations wiki page."""

import re
from typing import Any


def parse_excavations(wikitext: str) -> list[dict[str, Any]]:
    """Parse excavation data from tabber sections and tables."""
    items = []

    # Parse Excavation Sites (first tabber)
    sites = _parse_sites(wikitext)
    items.extend(sites)

    # Parse Excavation Levels table
    levels = _parse_levels(wikitext)
    items.extend(levels)

    # Parse Excavation Rewards (second tabber)
    rewards = _parse_rewards(wikitext)
    items.extend(rewards)

    return items


def _parse_sites(wikitext: str) -> list[dict[str, Any]]:
    """Parse excavation sites from the Sites tabber."""
    items = []

    # Find the first tabber (sites)
    tabber_match = re.search(r"<tabber>(.*?)</tabber>", wikitext, re.DOTALL)
    if not tabber_match:
        return items

    tabber_content = tabber_match.group(1)

    # Split by |-| to get tabs
    parts = re.split(r"\n\|\-\|", tabber_content)

    for i, part in enumerate(parts):
        part = part.lstrip()
        if not part:
            continue

        # Parse tab: RegionName = content
        if i == 0:
            # First tab doesn't have |-| prefix
            tab_match = re.match(r"([^\n]+?)\s*=(.*)", part, re.DOTALL)
        else:
            tab_match = re.match(r"([^\n]+?)\s*=(.*)", part, re.DOTALL)

        if not tab_match:
            continue

        region = tab_match.group(1).strip()
        content = tab_match.group(2).strip()

        site_items = _parse_region_sites(region, content)
        items.extend(site_items)

    return items


def _parse_region_sites(region: str, content: str) -> list[dict[str, Any]]:
    """Parse individual sites within a region."""
    items = []

    # Split by === Site Name === to get individual sites
    # Pattern: === Site Name (X-Site) ===
    sections = re.split(r"===\s*([^=]+?)\s*===", content)

    for i in range(1, len(sections), 2):
        site_name = sections[i].strip()
        content_section = sections[i + 1] if i + 1 < len(sections) else ""

        site = _parse_site(region, site_name, content_section)
        if site:
            items.append(site)

    return items


def _parse_site(region: str, site_name: str, content: str) -> dict[str, Any] | None:
    """Parse a single excavation site."""
    # Clean site name
    site_name = site_name.strip()
    if not site_name:
        return None

    # Extract bullet points
    permit_cost = ""
    excavation_cost = ""
    items_range = ""
    duration = ""

    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("* Permit Cost:"):
            permit_cost = line.replace("* Permit Cost:", "").strip()
        elif line.startswith("* Excavation Cost:"):
            excavation_cost = line.replace("* Excavation Cost:", "").strip()
        elif line.startswith("* Number of items (base):"):
            items_range = line.replace("* Number of items (base):", "").strip()
        elif line.startswith("* Duration (base):"):
            duration = line.replace("* Duration (base):", "").strip()

    # Clean up values
    permit_cost = re.sub(r"<[^>]+>", "", permit_cost).strip()
    excavation_cost = re.sub(r"<[^>]+>", "", excavation_cost).strip()
    items_range = items_range.strip()
    duration = duration.strip()

    return {
        "id": _slugify(f"{region}-{site_name}"),
        "type": "excavation_site",
        "name": site_name,
        "slug": _slugify(f"{region}-{site_name}"),
        "data": {
            "region": region,
            "site_name": site_name,
            "permit_cost": permit_cost,
            "excavation_cost": excavation_cost,
            "items_range": items_range,
            "duration": duration,
        },
        "image_url": None,
    }


def _parse_levels(wikitext: str) -> list[dict[str, Any]]:
    """Parse the Excavation Levels wikitable."""
    items = []

    # Find the levels table - it has "Level" header
    table_match = re.search(
        r'\{\| class="wikitable".*?Level.*?\n(.*?)\n\|\}',
        wikitext,
        re.DOTALL
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

        # Split by || - complex table with many columns
        cells = [c.strip() for c in row.split("||")]
        if len(cells) < 9:
            continue

        # Cell 0: Level (e.g., "| 1")
        level_cell = cells[0]
        level_match = re.search(r"(\d+)", level_cell)
        if not level_match:
            continue
        level = int(level_match.group(1))

        # Parse cell values
        cell_values = [_clean_cell(c) for c in cells]

        # Table structure has rowspans causing empty cells:
        # Index 0: Level (e.g., "| 1")
        # Index 1: Empty (rowspan)
        # Index 2: Luck (e.g., "+1")
        # Index 3: Empty (rowspan)
        # Index 4: Items A-Site (e.g., "4–8 (+0)")
        # Index 5: Items B-Site (e.g., "4–10 (+0)")
        # Index 6: Items C-F (e.g., "5–12 (+0)")
        # Index 7: Empty (rowspan)
        # Index 8: Multiplier (e.g., "1×")
        # Index 9-14: Durations for sites A-F

        data = {
            "level": level,
        }

        if len(cell_values) >= 15:
            data["luck"] = cell_values[2]
            data["items_a_site"] = cell_values[4]
            data["items_b_site"] = cell_values[5]
            data["items_c_f_sites"] = cell_values[6]
            data["speed_multiplier"] = cell_values[8]
            data["durations"] = cell_values[9:15]

        items.append({
            "id": f"excavation-level-{level}",
            "type": "excavation_level",
            "name": f"Excavation Level {level}",
            "slug": f"excavation-level-{level}",
            "data": data,
            "image_url": None,
        })

    return items


def _parse_rewards(wikitext: str) -> list[dict[str, Any]]:
    """Parse Excavation Rewards from the second tabber."""
    items = []

    # Find ALL tabbers
    tabber_matches = list(re.finditer(r"<tabber>(.*?)</tabber>", wikitext, re.DOTALL))
    if len(tabber_matches) < 2:
        return items

    # Second tabber is rewards
    tabber_content = tabber_matches[1].group(1)

    # Split by |-| to get tabs
    parts = re.split(r"\n\|\-\|", tabber_content)

    for _i, part in enumerate(parts):
        part = part.lstrip()
        if not part:
            continue

        # Parse tab: SiteName = content
        tab_match = re.match(r"([^\n]+?)\s*=(.*)", part, re.DOTALL)
        if not tab_match:
            continue

        site_name = tab_match.group(1).strip()
        content = tab_match.group(2).strip()

        rewards = _parse_reward_table(site_name, content)
        items.extend(rewards)

    return items


def _parse_reward_table(site_name: str, content: str) -> list[dict[str, Any]]:
    """Parse a single reward wikitable."""
    items = []

    # Find the wikitable - try multiple patterns
    table_match = re.search(
        r'\{\| class="wikitable[^}]*".*?\n(.*?)\n\|\}',
        content,
        re.DOTALL
    )
    if not table_match:
        # Try simpler pattern
        table_match = re.search(
            r'\{\|.*?\n(.*?)\n\|\}',
            content,
            re.DOTALL
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

        cells = [c.strip() for c in row.split("||")]

        # Handle different table formats
        # Format 1: 4 columns (Item, Description, Activation, Chances) - most sites
        # Format 2: 2 columns (Possible Rewards, Chances) - Alien Wreckage

        if len(cells) >= 4:
            # Standard 4-column format
            item_cell = cells[0]
            item_name = _extract_item_name(item_cell)
            description = _clean_cell(cells[1])
            activation = _clean_cell(cells[2])
            chance = _clean_cell(cells[3])
        elif len(cells) >= 2:
            # 2-column format (Alien Wreckage)
            item_cell = cells[0]
            item_name = _extract_item_name(item_cell)
            description = ""
            activation = ""
            chance = _clean_cell(cells[1])
        else:
            continue

        if not item_name:
            continue

        items.append({
            "id": _slugify(f"{site_name}-{item_name}"),
            "type": "excavation_reward",
            "name": item_name,
            "slug": _slugify(f"{site_name}-{item_name}"),
            "data": {
                "site": site_name,
                "description": description,
                "activation": activation,
                "chance": chance,
            },
            "image_url": None,
        })

    return items


def _extract_item_name(cell: str) -> str:
    """Extract item name from cell (handles [[Item]] and {{Item}})."""
    # Try [[Item]] first
    link_match = re.search(r"\[\[([^\]]+)\]\]", cell)
    if link_match:
        name = link_match.group(1)
        # Remove pipe if present
        if "|" in name:
            name = name.split("|")[0]
        return name.strip()

    # Try {{Item}}
    template_match = re.search(r"\{\{([^}]+)\}\}", cell)
    if template_match:
        return template_match.group(1).strip()

    # Fallback
    return _clean_cell(cell)


def _clean_cell(text: str) -> str:
    """Clean wiki markup from cell."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"'''([^']+)'''", r"\1", text)
    text = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", text)
    text = re.sub(r"\{\{[^}]+\}\}", "", text)
    return text.strip()


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace("'", "").replace("(", "").replace(")", "").replace("’", "").replace("&", "").replace("#", "").replace("×", "x").replace(":", "").replace("/", "-").replace("[", "").replace("]", "").replace(",", "").replace(".", "").replace("!", "").replace(";", "").replace("×", "x").replace("=", "").replace("?", "").replace("|", "")
