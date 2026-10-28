"""Mutations scraper - parse mutation chances and effects from the Mutations wiki page."""

import re

from scrapers.types import ParsedItem


def parse_mutations(wikitext: str) -> list[ParsedItem]:
    """Parse mutation data from tabber sections and tables."""
    items: list[ParsedItem] = []

    # Parse mutation chances from tabber
    chance_items = _parse_chances(wikitext)
    items.extend(chance_items)

    # Parse mutation effects
    effect_items = _parse_effects(wikitext)
    items.extend(effect_items)

    # Parse equipment catalysts from tabber
    catalyst_items = _parse_catalysts(wikitext)
    items.extend(catalyst_items)

    return items


def _parse_chances(wikitext: str) -> list[ParsedItem]:
    """Parse mutation chance tables from the Chances tabber."""
    items: list[ParsedItem] = []

    # Find the Chances tabber
    tabber_pattern = r"<tabber>(.*?)</tabber>"
    tabber_match = re.search(tabber_pattern, wikitext, re.DOTALL)
    if not tabber_match:
        return items

    tabber_content = tabber_match.group(1)

    # Split by |-| to get tabs
    parts = re.split(r"\n\|\-\|", tabber_content)

    for i, part in enumerate(parts):
        part = part.lstrip()
        if not part:
            continue

        # Parse tab: TabName = content
        if i == 0:
            tab_match = re.match(r"([^\n]+?)\s*=(.*)", part, re.DOTALL)
        else:
            tab_match = re.match(r"([^\n]+?)\s*=(.*)", part, re.DOTALL)

        if not tab_match:
            continue

        tab_name = tab_match.group(1).strip()
        content = tab_match.group(2).strip()

        # Parse the wikitable for this tab
        table_items = _parse_chance_table(tab_name, content)
        items.extend(table_items)

    return items


def _parse_chance_table(event_name: str, content: str) -> list[ParsedItem]:
    """Parse a single chance wikitable."""
    items: list[ParsedItem] = []

    # Find the wikitable
    table_match = re.search(r'\{\| class="wikitable".*?\n(.*?)\n\|\}', content, re.DOTALL)
    if not table_match:
        return items

    table_body = table_match.group(1)

    # Extract header to get catalyst counts
    header_match = re.search(r"!.*?# Catalysts:.*?\n(.*?)\n", content, re.DOTALL)
    catalyst_counts: list[int] = []
    if header_match:
        header_row = header_match.group(1)
        cells = [c.strip() for c in header_row.split("!!")]
        for cell in cells[1:]:  # Skip the "# Catalysts:" cell
            # Handle first cell which may start with "! " instead of just the number
            cell = cell.lstrip("! ").strip()
            try:
                catalyst_counts.append(int(cell))
            except (ValueError, TypeError):
                pass

    # Split table body by rows - look for |- at start of line
    rows = re.split(r"\n\|\-", table_body)

    for row in rows:
        row = row.strip()
        if not row:
            continue
        # Skip caption row
        if row.startswith("|+"):
            continue
        # Skip header row
        if row.startswith("!"):
            # Check if this is the header row with catalyst counts
            if "# Catalysts:" in row:
                continue
            # Data rows start with ! for the mutation name
            if not row.startswith("! {{Enchant|"):
                continue
        elif not row.startswith("|"):
            continue

        # Split by || - each cell is a mutation chance for a catalyst count
        # For header rows (starting with !), the first cell contains the mutation name
        cells = [c.strip() for c in row.split("||")]
        if len(cells) < 2:
            continue

        # Cell 0: Mutation name (with {{Enchant|Name}} template)
        mutation_cell = cells[0]
        mutation_match = re.search(r"\{\{Enchant\|([^}]+)\}\}", mutation_cell)
        if not mutation_match:
            continue
        mutation_name = mutation_match.group(1).strip()

        # Parse chances for each catalyst count
        chances = {}
        for i, cell in enumerate(cells[1:]):
            if i < len(catalyst_counts):
                chance_str = cell.strip()
                # Remove % if present
                chance_str = chance_str.rstrip("%")
                try:
                    chance = float(chance_str)
                except (ValueError, TypeError):
                    chance = 0.0
                chances[catalyst_counts[i]] = chance

        items.append(
            {
                "id": _slugify(f"{event_name}-{mutation_name}"),
                "type": "mutation_chance",
                "name": f"{mutation_name} ({event_name})",
                "slug": _slugify(f"{event_name}-{mutation_name}"),
                "data": {
                    "event": event_name,
                    "mutation": mutation_name,
                    "chances_by_catalysts": chances,
                },
                "image_url": None,
            }
        )

    return items


def _parse_effects(wikitext: str) -> list[ParsedItem]:
    """Parse mutation effects from the Effects section."""
    items: list[ParsedItem] = []

    # Find the Effects section
    effects_match = re.search(r"== Effects ==\n(.*?)(?:\n==|$)", wikitext, re.DOTALL)
    if not effects_match:
        return items

    effects_content = effects_match.group(1)

    # Parse bullet points: * {{Enchant|Name}}: multiplier, +additives
    bullet_pattern = r"\*\s*\{\{Enchant\|([^}]+)\}\}:\s*([^\n]+)"
    for match in re.finditer(bullet_pattern, effects_content):
        mutation_name = match.group(1).strip()
        effect_text = match.group(2).strip()

        # Parse the effect text
        # Format: X× or X×, +Y Stat
        multiplier_match = re.search(r"([\d.]+)×", effect_text)
        multiplier = float(multiplier_match.group(1)) if multiplier_match else 1.0

        # Parse additive bonuses
        additives = {}
        add_matches = re.findall(r"\+(\d+)\s*\{\{Stat\|([^}]+)\}\}", effect_text)
        for value, stat in add_matches:
            additives[stat] = int(value)

        items.append(
            {
                "id": _slugify(f"mutation-effect-{mutation_name}"),
                "type": "mutation_effect",
                "name": mutation_name,
                "slug": _slugify(f"mutation-effect-{mutation_name}"),
                "data": {
                    "multiplier": multiplier,
                    "additives": additives,
                    "description": effect_text,
                },
                "image_url": None,
            }
        )

    return items


def _parse_catalysts(wikitext: str) -> list[ParsedItem]:
    """Parse equipment catalysts from the List of Equipment Catalysts tabber."""
    items: list[ParsedItem] = []

    # Find the second tabber (catalysts)
    tabber_matches = list(re.finditer(r"<tabber>(.*?)</tabber>", wikitext, re.DOTALL))
    if len(tabber_matches) < 2:
        return items

    tabber_content = tabber_matches[1].group(1)

    # Split by |-| to get tabs - skip empty first part
    parts = re.split(r"\n\|\-\|", tabber_content)

    for _i, part in enumerate(parts):
        part = part.lstrip()
        if not part:
            continue

        # Parse tab: TabName = content
        tab_match = re.match(r"([^\n]+?)\s*=(.*)", part, re.DOTALL)
        if not tab_match:
            continue

        rarity = tab_match.group(1).strip()
        content = tab_match.group(2).strip()

        catalyst_items = _parse_catalyst_table(rarity, content)
        items.extend(catalyst_items)

    return items


def _parse_catalyst_table(rarity: str, content: str) -> list[ParsedItem]:
    """Parse a single catalyst wikitable."""
    # The tab content IS the table - extract mutations rows directly from content
    mutations_rows = re.findall(r"\{\{Mutations Row\s*\n(.*?)(?:\n\}\}|\}\})", content, re.DOTALL)
    items: list[ParsedItem] = []
    for mr_content in mutations_rows:
        catalyst = _parse_mutations_row(rarity, mr_content)
        if catalyst:
            items.append(catalyst)

    return items


def _parse_mutations_row(rarity: str, content: str) -> ParsedItem | None:
    """Parse a single {{Mutations Row}} template."""
    fields = {}

    # Parse template fields line by line
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("|"):
            # Parse | key = value
            parts = line[1:].split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                fields[key] = value

    equip_name = fields.get("equip name", "")
    equip_name_color = fields.get("equip name color", "")
    mineral_name = fields.get("mineral name", "")
    mineral_name_color = fields.get("mineral name color", "")

    if not equip_name:
        return None

    # Clean up names
    equip_name = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", equip_name)
    mineral_name = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", mineral_name)

    slug = _slugify(f"{rarity}-{equip_name}")

    return {
        "id": slug,
        "type": "mutation_catalyst",
        "name": equip_name,
        "slug": slug,
        "data": {
            "rarity": rarity,
            "equipment": equip_name,
            "equipment_color": equip_name_color,
            "mineral": mineral_name,
            "mineral_color": mineral_name_color,
        },
        "image_url": None,
    }


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
        .replace("|", "")
        .replace("%", "")
    )
