"""Work out what kind of page a wiki page is.

The wiki holds two kinds of page that matter for the item data: the index
pages that list items (Pans, Minerals, Potions) and the pages that describe a
single item (Moonspire, Rusty Pan, Firefly Flare). The index pages are what
the scraper reads; the item pages hold the details, and a page that has no
item at all may be a guide, a shop or a location.

The classification is used to find the pages the scraper is missing and to
decide which pages can enrich an item.
"""

from __future__ import annotations

import re

__all__ = [
    "ITEM_CATEGORIES",
    "ITEM_INFOBOXES",
    "is_item_page",
    "is_index_page",
    "item_type_hint",
]

# The infobox templates an item page uses.
ITEM_INFOBOXES = (
    "{{Mineral",
    "{{PanInfobox",
    "{{ShovelInfobox",
    "{{SluiceInfobox",
    "{{EquipmentInfobox",
    "{{RuneInfobox",
    "{{RelicInfobox",
    "{{TrinketInfobox",
    "{{GeodeInfobox",
    "{{ItemInfobox",
    "{{ConsumableInfobox",
    "{{Infobox",
)

# The categories that hold items. The names are compared without the
# "Category:" prefix, the way categories_of returns them.
ITEM_CATEGORIES = (
    "Items",
    "Consumables",
    "Minerals",
    "Traveling Merchant Items",
    "Enchant Books",
    "Blueprints",
    "Equipment",
    "Relics",
    "Geodes",
    "Trinkets",
    "Potions",
)

# A wikitable that lists items has a header naming the thing in the row.
_ITEM_HEADER = re.compile(
    r"!\s*(?:style=\"[^\"]*\"\s*\|\s*)?(?:item|name|rune|mineral|equipment|enchantment)\b",
    re.IGNORECASE,
)

# A category link at the end of a page.
_CATEGORY_LINK = re.compile(r"\[\[\s*Category\s*:\s*([^\]|]+)", re.IGNORECASE)


def categories_of(wikitext: str) -> set[str]:
    """Return the categories a page is in."""
    found = {match.strip().lower() for match in _CATEGORY_LINK.findall(wikitext or "")}
    # The wiki's category names are compared without their prefix.
    return {name.replace("category:", "") for name in found}


def is_item_page(wikitext: str) -> bool:
    """Return True when a page describes a single item.

    A page is an item page when it uses one of the item infoboxes, or when it
    is in a category that holds items.
    """
    if not wikitext:
        return False

    lowered = wikitext.lower()
    if any(infobox.lower() in lowered for infobox in ITEM_INFOBOXES):
        return True

    item_categories = {name.lower() for name in ITEM_CATEGORIES}
    return bool(categories_of(wikitext) & item_categories)


def is_index_page(wikitext: str) -> bool:
    """Return True when a page holds a table that lists items."""
    for table in split_tables(wikitext):
        if _ITEM_HEADER.search(table):
            return True
    return False


def split_tables(wikitext: str) -> list[str]:
    """Split a page into its wikitables."""
    tables: list[str] = []
    start = None
    depth = 0

    for index, char in enumerate(wikitext or ""):
        if char == "{" and wikitext[index : index + 2] == "{|":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                tables.append(wikitext[start : index + 1])
                start = None

    return tables


def item_type_hint(wikitext: str, title: str = "") -> str | None:
    """Guess the type of the item a page describes.

    The infobox gives the type away for most items. For the pages that are
    only prose, the categories and the title are used instead.
    """
    lowered = (wikitext or "").lower()

    if "{{mineral" in lowered:
        return "mineral"
    if "{{paninfobox" in lowered:
        return "pan"
    if "{{shovelinfobox" in lowered:
        return "shovel"
    if "{{sluiceinfobox" in lowered:
        return "sluice"
    if "{{equipmentinfobox" in lowered:
        return "equipment"
    if "{{runeinfobox" in lowered:
        return "rune"
    if "{{relicinfobox" in lowered:
        return "relic"
    if "{{trinketinfobox" in lowered:
        return "trinket"
    if "{{geodeinfobox" in lowered:
        return "geode"

    categories = categories_of(wikitext or "")
    if "consumables" in categories or "traveling merchant items" in categories:
        return "consumable"
    if "minerals" in categories:
        return "mineral"
    if "enchant books" in categories:
        return "enchant_book"
    if "blueprints" in categories:
        return "blueprint"
    if "equipment" in categories:
        return "equipment"
    if "relics" in categories:
        return "relic"
    if "geodes" in categories:
        return "geode"
    if "trinkets" in categories:
        return "trinket"

    name = (title or "").lower()
    for suffix, item_type in (
        (" potion", "potion"),
        (" pan", "pan"),
        (" shovel", "shovel"),
        (" sluice", "sluice"),
        (" rune", "rune"),
    ):
        if name.endswith(suffix):
            return item_type

    return None
