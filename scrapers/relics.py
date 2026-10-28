"""Relics scraper - parse relics from the Relics wiki page with tabber sections."""

import re

from scrapers.types import ParsedItem


def parse_relics(wikitext: str) -> list[ParsedItem]:
    """Parse relic data from tabber sections."""
    relics: list[ParsedItem] = []

    # Find all tabber tags
    tabber_pattern = r"<tabber>(.*?)</tabber>"

    for tabber_match in re.finditer(tabber_pattern, wikitext, re.DOTALL):
        tabber_content = tabber_match.group(1)

        # Parse each tab: |-| TabName = content
        tab_pattern = r"\|\-\|\s*([^=]+)\s*=(.*?)(?=\|\-\||$)"

        for tab_match in re.finditer(tab_pattern, tabber_content, re.DOTALL):
            tab_name = tab_match.group(1).strip()
            tab_content = tab_match.group(2).strip()

            if not tab_name:
                continue

            relic = _parse_relic_content(tab_name, tab_content)
            if relic:
                relics.append(relic)

    return relics


def _parse_relic_content(name: str, content: str) -> ParsedItem | None:
    """Parse a single relic's content."""
    # Extract description (first paragraph after image). The heading markers
    # are left out of the captured text.
    desc_match = re.search(r"\]\]\s*(.*?)(?=\n==\s*Obtainment|\n==\s*Usage|\Z)", content, re.DOTALL)
    description = desc_match.group(1).strip() if desc_match else ""

    # Extract obtainment
    obtainment_match = re.search(
        r"==\s*Obtainment\s*==(.*?)(?=\n==\s*Usage|\Z)", content, re.DOTALL
    )
    obtainment = obtainment_match.group(1).strip() if obtainment_match else ""

    # Extract usage
    usage_match = re.search(r"==\s*Usage\s*==(.*)\Z", content, re.DOTALL)
    usage = usage_match.group(1).strip() if usage_match else ""

    # Extract image
    image_match = re.search(r"\[\[File:([^\]]+)\]\]", content)
    image = image_match.group(1) if image_match else ""

    # Determine relic type from tabber section (Event Relics, Boost Relics, etc.)
    relic_type = "relic"

    # The markup is resolved by the shared renderer when the item is stored,
    # so the raw wikitext is kept here.
    return {
        "id": _slugify(name),
        "type": relic_type,
        "name": name,
        "slug": _slugify(name),
        "data": {
            "description": description,
            "obtainment": obtainment,
            "usage": usage,
            "image": image,
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
        .replace(":", "")
        .replace("#", "")
    )
