"""Geodes scraper - parse geode variants list from the Geodes wiki page."""

import re
from typing import Any


def parse_geodes(wikitext: str) -> list[dict[str, Any]]:
    """Parse geode data from wikitext containing the geode variants list."""
    geodes = []
    seen = {}  # slug -> index in geodes list

    # The geode variants are listed as bullet points like:
    # * '''Rubble Creek Geode''' - found in {{Rubble Creek Sands}}

    # Pattern to match: * '''Name''' - found in {{Location}}
    pattern = r"\*\s*'''([^']+)'''\s*[-–]\s*found in\s+\{\{([^}]+)\}\}"

    # First pass: main list
    for match in re.finditer(pattern, wikitext):
        name = match.group(1).strip()
        location = match.group(2).strip()

        if not name:
            continue

        slug = _slugify(name)
        seen[slug] = len(geodes)

        geodes.append(
            {
                "id": slug,
                "type": "geode",
                "name": name,
                "slug": slug,
                "data": {
                    "location": location,
                    "description": f"Geode found in {location}",
                    "image": "",
                    "requires_geothermal": False,
                },
                "image_url": None,
            }
        )

    # Second pass: geothermal-only section
    geothermal_section = False
    for line in wikitext.split("\n"):
        stripped = line.strip()
        if "Geodes obtainable only by using" in stripped:
            geothermal_section = True
            continue
        if geothermal_section and stripped.startswith("*"):
            match = re.match(r"\*\s*'''([^']+)'''\s*[-–]\s*found in\s+\{\{([^}]+)\}\}", stripped)
            if match:
                name = match.group(1).strip()
                location = match.group(2).strip()

                slug = _slugify(name)

                if slug in seen:
                    # Update existing entry to mark as geothermal
                    idx = seen[slug]
                    geodes[idx]["data"]["requires_geothermal"] = True
                    geodes[idx]["data"]["description"] = (
                        f"Geode found in {location} (requires Geothermal shovel enchant)"
                    )
                else:
                    seen[slug] = len(geodes)
                    geodes.append(
                        {
                            "id": slug,
                            "type": "geode",
                            "name": name,
                            "slug": slug,
                            "data": {
                                "location": location,
                                "description": f"Geode found in {location} (requires Geothermal shovel enchant)",
                                "image": "",
                                "requires_geothermal": True,
                            },
                            "image_url": None,
                        }
                    )
        elif geothermal_section and stripped and not stripped.startswith("*"):
            geothermal_section = False

    # There is exactly one geode type per location. If the wiki ever lists two
    # variants for the same place, keep the first so the invariant holds.
    unique: list[dict[str, Any]] = []
    seen_locations: set[str] = set()
    for geode in geodes:
        data = geode.get("data")
        location = data.get("location", "") if isinstance(data, dict) else ""
        location_key = str(location).strip().lower()
        if location_key and location_key in seen_locations:
            continue
        if location_key:
            seen_locations.add(location_key)
        unique.append(geode)

    return unique


def _slugify(name: str) -> str:
    return (
        name.lower()
        .replace(" ", "-")
        .replace("'", "")
        .replace("(", "")
        .replace(")", "")
        .replace("’", "")
    )
