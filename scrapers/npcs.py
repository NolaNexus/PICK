"""NPCs scraper - parse <tabber> with <gallery> sections from the NPCs wiki page."""

import re
from typing import Any


def parse_npcs(wikitext: str) -> list[dict[str, Any]]:
    """Parse NPC data from tabber gallery sections."""
    npcs = []

    # Find the main tabber
    tabber_pattern = r"<tabber>(.*?)</tabber>"
    tabber_match = re.search(tabber_pattern, wikitext, re.DOTALL)
    if not tabber_match:
        return npcs

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
                npcs.extend(tab_npcs)
            # Start new tab with name from same line
            current_tab = tab_sep_match.group(1).strip()
            current_content = []
            continue

        # Check for tab separator - Style 1: |-| on its own line
        if stripped == "|-|":
            # Save previous tab
            if current_tab is not None:
                tab_npcs = _parse_tab(current_tab, "\n".join(current_content))
                npcs.extend(tab_npcs)
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
        npcs.extend(tab_npcs)

    return npcs


def _parse_tab(tab_name: str, content: str) -> list[dict[str, Any]]:
    """Parse a single tab content."""
    if not tab_name:
        return []
    return _parse_gallery(tab_name, content)


def _parse_gallery(region: str, content: str) -> list[dict[str, Any]]:
    """Parse NPC entries from a gallery section."""
    npcs = []
    seen_slugs: set[str] = set()

    # Gallery format:
    # <gallery ...>
    # ImageName.png|link=TargetPage|[[DisplayName]]
    # </gallery>
    gallery_pattern = r"<gallery[^>]*>(.*?)</gallery>"
    gallery_match = re.search(gallery_pattern, content, re.DOTALL)
    if not gallery_match:
        return npcs

    gallery_content = gallery_match.group(1)

    # Each line is an entry: ImageName.png|link=TargetPage|[[DisplayName]]
    for line in gallery_content.split("\n"):
        line = line.strip()
        if not line or line.startswith("<") or line.startswith("|-"):
            continue

        # Parse: filename|link=target|[[display]] or filename|[[display]]
        parts = line.split("|")
        if len(parts) < 2:
            continue

        image_file = parts[0].strip()

        # Find display name and link target
        display_name = ""
        link_target = ""

        for part in parts[1:]:
            part = part.strip()
            if part.startswith("link="):
                link_target = part[5:].strip()
            elif part.startswith("[[") and part.endswith("]]"):
                display_name = part[2:-2].strip()
            elif part.startswith("[["):
                # Handle [[DisplayName|LinkTarget]] format
                inner = part[2:]
                if "|" in inner:
                    display_name, link_target = inner.split("|", 1)
                    link_target = link_target.rstrip("]").strip()
                else:
                    display_name = inner.rstrip("]").strip()

        # Use display name, fallback to link target
        name = display_name or link_target
        if not name:
            continue

        # Clean up name - remove trailing refs
        name = re.sub(r"\]\]<ref>.*$", "", name).strip()

        # NPC names repeat across regions (e.g. "Merchant" in many areas), so
        # the slug must include the region to keep every NPC a distinct item.
        slug = _slugify(f"{_slug_region(region)}-{name}")
        if slug in seen_slugs:
            # Same region, same name but a different NPC (e.g. two tourists
            # sharing one gallery entry). Disambiguate with the image name.
            slug = _slugify(f"{_slug_region(region)}-{name}-{_slugify(image_file)}")
            suffix = 2
            base_slug = slug
            while slug in seen_slugs:
                slug = f"{base_slug}-{suffix}"
                suffix += 1
        seen_slugs.add(slug)

        npcs.append(
            {
                "id": slug,
                "type": "npc",
                "name": name,
                "slug": slug,
                "data": {
                    "region": region,
                    "location": region,
                    "image": image_file,
                    "link_target": link_target,
                },
                "image_url": None,
            }
        )

    return npcs


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
