"""NPCs scraper - parse <tabber> with <gallery> sections from the NPCs wiki page."""

import re
from typing import Any


def parse_npcs(wikitext: str) -> list[dict[str, Any]]:
    """Parse NPC data from tabber gallery sections."""
    entries: list[dict[str, Any]] = []

    # Find the main tabber
    tabber_pattern = r"<tabber>(.*?)</tabber>"
    tabber_match = re.search(tabber_pattern, wikitext, re.DOTALL)
    if not tabber_match:
        return []

    tabber_content = tabber_match.group(1)

    # The tabber format has two styles:
    # Style 1 (early tabs): |-| on its own line, then TabName = on next line
    # Style 2 (later tabs): |-| TabName = on same line
    # First tab: TabName = on first line (no |-| before it)

    lines = tabber_content.split("\n")

    current_tab = None
    current_content = []

    for _i, line in enumerate(lines):
        stripped = line.strip()

        # Check for tab separator - Style 2: |-| TabName =
        tab_sep_match = re.match(r"^\|-\|\s*(.+?)\s*=$", stripped)
        if tab_sep_match:
            # Save previous tab
            if current_tab is not None:
                tab_npcs = _parse_tab(current_tab, "\n".join(current_content))
                entries.extend(tab_npcs)
            # Start new tab with name from same line
            current_tab = tab_sep_match.group(1).strip()
            current_content = []
            continue

        # Check for tab separator - Style 1: |-| on its own line
        if stripped == "|-|":
            # Save previous tab
            if current_tab is not None:
                tab_npcs = _parse_tab(current_tab, "\n".join(current_content))
                entries.extend(tab_npcs)
            # Next line will be the tab name
            current_tab = None
            current_content = []
            continue

        # Check for tab name (contains = but not a gallery line, and we're expecting a tab name)
        if (
            "=" in stripped
            and not stripped.startswith("<")
            and not stripped.startswith("|")
            and current_tab is None
        ):
            current_tab = stripped.rstrip("=").strip()
            current_content = []
            continue

        # Accumulate content for current tab
        if current_tab is not None:
            current_content.append(line)

    # Don't forget the last tab
    if current_tab is not None:
        tab_npcs = _parse_tab(current_tab, "\n".join(current_content))
        entries.extend(tab_npcs)

    return _group_npcs(entries)


def _parse_tab(tab_name: str, content: str) -> list[dict[str, Any]]:
    """Parse a single tab content."""
    if not tab_name:
        return []
    return _parse_gallery(tab_name, content)


def _parse_gallery(region: str, content: str) -> list[dict[str, Any]]:
    """Parse raw NPC entries from a gallery section."""
    entries: list[dict[str, Any]] = []

    # Gallery format:
    # <gallery ...>
    # ImageName.png|link=TargetPage|[[DisplayName]]
    # </gallery>
    gallery_pattern = r"<gallery[^>]*>(.*?)</gallery>"
    gallery_match = re.search(gallery_pattern, content, re.DOTALL)
    if not gallery_match:
        return entries

    gallery_content = gallery_match.group(1)

    for line in gallery_content.split("\n"):
        line = line.strip()
        if not line or line.startswith("<") or line.startswith("|-"):
            continue

        parts = line.split("|")
        if len(parts) < 2:
            continue

        image_file = parts[0].strip()

        display_name = ""
        link_target = ""

        for part in parts[1:]:
            part = part.strip()
            if part.startswith("link="):
                link_target = part[5:].strip()
            elif part.startswith("[[") and part.endswith("]]"):
                display_name = part[2:-2].strip()
            elif part.startswith("[["):
                inner = part[2:]
                if "|" in inner:
                    display_name, link_target = inner.split("|", 1)
                    link_target = link_target.rstrip("]").strip()
                else:
                    display_name = inner.rstrip("]").strip()

        name = display_name or link_target
        if not name:
            continue

        name = re.sub(r"\]\]<ref>.*$", "", name).strip()

        entries.append(
            {
                "name": name,
                "region": region,
                "image": image_file,
                "link_target": link_target,
            }
        )

    return entries


# NPCs that exist once per town as a service. Each town's merchant, blacksmith,
# alchemist and trader is a distinct character, even though they share a name.
TOWN_SERVICE_NAMES = {"merchant", "blacksmith", "alchemist", "trader"}


def _group_npcs(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group the same NPC across locations into one entry.

    Town services stay separate per location, and same-name entries inside one
    location (e.g. two tourists) remain distinct individuals.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        groups.setdefault(entry["name"], []).append(entry)

    npcs: list[dict[str, Any]] = []
    seen_slugs: set[str] = set()

    for name, rows in groups.items():
        regions = [row["region"] for row in rows]
        one_per_location = len(regions) == len(set(regions))

        if name.lower() in TOWN_SERVICE_NAMES or not one_per_location:
            for row in rows:
                slug = _slugify(f"{_slug_region(row['region'])}-{name}")
                if slug in seen_slugs:
                    slug = _slugify(f"{slug}-{_slugify(row['image'])}")
                base_slug = slug
                suffix = 2
                while slug in seen_slugs:
                    slug = f"{base_slug}-{suffix}"
                    suffix += 1
                seen_slugs.add(slug)
                npcs.append(_separate_npc(name, row, slug))
            continue

        slug = _slugify(name)
        if slug in seen_slugs:
            # Distinct names can slugify identically (e.g. "Archaeologist" and
            # "Archaeologist?"). Keep them separate with a numeric suffix.
            base_slug = slug
            suffix = 2
            while slug in seen_slugs:
                slug = f"{base_slug}-{suffix}"
                suffix += 1
        seen_slugs.add(slug)
        npcs.append(_grouped_npc(name, rows, slug))

    return npcs


def _grouped_npc(name: str, rows: list[dict[str, Any]], slug: str) -> dict[str, Any]:
    """Build one NPC entry spanning several locations."""
    locations = sorted({row["region"] for row in rows})
    data: dict[str, Any] = {
        "locations": locations,
        "portraits": {row["region"]: row["image"] for row in rows},
        "image": rows[0]["image"],
        "link_target": rows[0]["link_target"],
    }
    if len(locations) == 1:
        data["region"] = locations[0]
        data["location"] = locations[0]

    return {
        "id": slug,
        "type": "npc",
        "name": name,
        "slug": slug,
        "data": data,
        "image_url": None,
    }


def _separate_npc(name: str, row: dict[str, Any], slug: str) -> dict[str, Any]:
    """Build a location-specific NPC entry (town service or same-name pair)."""
    return {
        "id": slug,
        "type": "npc",
        "name": name,
        "slug": slug,
        "data": {
            "region": row["region"],
            "location": row["region"],
            "locations": [row["region"]],
            "image": row["image"],
            "link_target": row["link_target"],
        },
        "image_url": None,
    }


REGIONLESS_LABEL = "Regionless NPCs"


def _slug_region(region: str) -> str:
    """Return the slug prefix for a region label."""
    if not region or region == REGIONLESS_LABEL:
        return "global"
    return region


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
        .replace("|", "")
        .replace("?", "")
        .replace("]", "")
    )
