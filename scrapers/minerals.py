"""Minerals scraper - parse {{Mineral row slim ...}} templates from the Minerals wiki page."""

import re
from typing import Any

import mwparserfromhell


def parse_minerals(wikitext: str) -> list[dict[str, Any]]:
    """Parse mineral data from wikitext containing Mineral tables with tabber tiers."""
    tree = mwparserfromhell.parse(wikitext)
    minerals = []

    # Find all tabber sections (tiers like Common, Uncommon, etc.)
    tabbers = tree.filter_tags("tabber")
    for tabber in tabbers:
        # Get the tabber content
        tabber_text = str(tabber).strip()

        # Parse the tab labels using regex
        # Pattern: |-| TierName =
        tab_pattern = r"\|\-\|\s*([^=]+)\s*=(.*?)(?=\|\-\||</?tabber>|\Z)"
        tab_matches = re.finditer(tab_pattern, tabber_text, re.DOTALL)

        current_tier = ""
        for tab_match in tab_matches:
            current_tier = tab_match.group(1).strip()
            tab_content = tab_match.group(2).strip()
            _parse_mineral_table(tab_content, current_tier, minerals)

    # Also parse minerals from any non-tabber tables
    _parse_all_mineral_templates(wikitext, minerals)

    return minerals


def _parse_mineral_table(table_text: str, tier: str, minerals: list[dict[str, Any]]) -> None:
    """Parse mineral rows from a table within a tabber section."""
    # Match {{Mineral row slim ...}} templates
    template_pattern = r"\{\{Mineral row slim[^}]*\}\}"

    for match in re.finditer(template_pattern, table_text, re.DOTALL):
        template_text = match.group(0)
        params = _extract_mineral_params(template_text)

        name = params.get("name", "")
        if not name:
            continue

        try:
            value = float(str(params.get("value", "0")).replace(",", "").strip())
        except (ValueError, TypeError):
            value = 0

        # Parse locations from wiki template references like {{LocationName}}
        locations = _parse_mineral_locations(params.get("locations", ""))

        description = str(params.get("description", "")).strip()
        image = str(params.get("image", "")).strip()

        minerals.append(
            {
                "id": _slugify(name),
                "type": "mineral",
                "name": name,
                "slug": _slugify(name),
                "data": {
                    "image": image,
                    "value": value,
                    "locations": locations,
                    "description": description,
                    "tier": tier,
                },
                "image_url": None,
            }
        )


def _parse_mineral_locations(locations_str: str) -> list[str]:
    """Parse location names from the locations parameter string."""
    locations = []
    # Find wikilink names: [[Name]] or [[Name|Display]]
    for match in re.finditer(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", locations_str):
        name = match.group(1).strip()
        if name and name not in locations:
            locations.append(name)
    return locations


def _extract_mineral_params(template_text: str) -> dict[str, str]:
    """Extract parameters from a Mineral row slim template."""
    params = {}

    # Match key=value pairs within the template
    # Pattern: | key = value (value extends to end or next pipe)
    param_pattern = r"\|\s*(\w+)\s*=\s*([^|}]+)"
    for match in re.finditer(param_pattern, template_text):
        key = match.group(1).strip().lower()
        value = match.group(2).strip()
        # Clean up value - remove trailing whitespace, newlines
        value = re.sub(r"\s+\|.*$", "", value).strip()
        params[key] = value

    return params


def _parse_all_mineral_templates(wikitext: str, minerals: list[dict[str, Any]]) -> None:
    """Parse any {{Mineral row slim ...}} templates found anywhere in the wikitext."""
    template_pattern = r"\{\{Mineral row slim[^}]*\}\}"

    for match in re.finditer(template_pattern, wikitext, re.DOTALL):
        template_text = match.group(0)
        params = _extract_mineral_params(template_text)

        name = params.get("name", "")
        if not name:
            continue

        try:
            value = float(str(params.get("value", "0")).replace(",", "").strip())
        except (ValueError, TypeError):
            value = 0

        locations = _parse_mineral_locations(params.get("locations", ""))
        description = str(params.get("description", "")).strip()
        image = str(params.get("image", "")).strip()

        minerals.append(
            {
                "id": _slugify(name),
                "type": "mineral",
                "name": name,
                "slug": _slugify(name),
                "data": {
                    "image": image,
                    "value": value,
                    "locations": locations,
                    "description": description,
                    "tier": "",
                },
                "image_url": None,
            }
        )


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace("'", "").replace("(", "").replace(")", "")
