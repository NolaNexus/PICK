"""Relics scraper - parse relics from the Relics wiki page with tabber sections."""

import re
from typing import Any


def parse_relics(wikitext: str) -> list[dict[str, Any]]:
    """Parse relic data from tabber sections."""
    relics = []

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


def _parse_relic_content(name: str, content: str) -> dict[str, Any] | None:
    """Parse a single relic's content."""
    # Extract description (first paragraph after image)
    desc_match = re.search(r"\]\](.*?)(?==\s*Obtainment|==\s*Usage|$)", content, re.DOTALL)
    description = ""
    if desc_match:
        description = desc_match.group(1).strip()
        # Clean up
        description = re.sub(r"<[^>]+>", "", description)  # Remove HTML tags
        description = re.sub(r"'''([^']+)'''", r"\1", description)  # Remove bold
        description = description.strip()

    # Extract obtainment
    obtainment = ""
    obtainment_match = re.search(r"==\s*Obtainment\s*==(.*?)(?==\s*Usage|==|$)", content, re.DOTALL)
    if obtainment_match:
        obtainment = obtainment_match.group(1).strip()
        obtainment = re.sub(r"<[^>]+>", "", obtainment)
        obtainment = re.sub(r"\{\{[^}]+\}\}", "", obtainment)
        obtainment = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", obtainment)
        obtainment = obtainment.strip()

    # Extract usage
    usage = ""
    usage_match = re.search(r"==\s*Usage\s*==(.*?)(?==|$)", content, re.DOTALL)
    if usage_match:
        usage = usage_match.group(1).strip()
        usage = re.sub(r"<[^>]+>", "", usage)
        usage = re.sub(r"\{\{[^}]+\}\}", "", usage)
        usage = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", usage)
        usage = usage.strip()

    # Extract image
    image_match = re.search(r"\[\[File:([^\]]+)\]\]", content)
    image = image_match.group(1) if image_match else ""

    # Determine relic type from tabber section (Event Relics, Boost Relics, etc.)
    relic_type = "relic"

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
