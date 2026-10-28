"""The canonical taxonomy of item types.

Every item type the scraper can produce is declared here once: which area it
belongs to, the group it sits in inside that area, the label to show a user,
and whether it is listed on its own or attached to something else.

Without this, the type is just a string a parser happened to emit, and the
site ends up with a flat list of cryptic names.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "AREAS",
    "GROUPS",
    "TAXONOMY",
    "area_of",
    "group_of",
    "is_listed",
    "label_of",
    "taxonomy_payload",
    "types_in_area",
    "types_in_group",
]

#: An area is a place the user can browse.
AREAS: tuple[str, ...] = ("items", "minerals", "world", "calculators")

#: The groups inside the items area.
GROUPS: dict[str, tuple[str, ...]] = {
    "items": ("gear", "consumables", "treasure"),
}

#: What a type is.
ITEM = "item"
RECORD = "record"
REFERENCE = "reference"

#: type -> (area, group, label, kind)
TAXONOMY: dict[str, tuple[str, str | None, str, str]] = {
    # Items: gear
    "pan": ("items", "gear", "Pan", ITEM),
    "shovel": ("items", "gear", "Shovel", ITEM),
    "sluice": ("items", "gear", "Sluice", ITEM),
    "equipment": ("items", "gear", "Equipment", ITEM),
    "trinket": ("items", "gear", "Trinket", ITEM),
    "rune": ("items", "gear", "Rune", ITEM),
    # Items: consumables
    "potion": ("items", "consumables", "Potion", ITEM),
    "enchant_book": ("items", "consumables", "Enchant Book", ITEM),
    "relic": ("items", "consumables", "Relic", ITEM),
    # Items: treasure
    "geode": ("items", "treasure", "Geode", ITEM),
    "treasure_chest": ("items", "treasure", "Treasure Chest", ITEM),
    "treasure_map": ("items", "treasure", "Treasure Map", ITEM),
    # Minerals
    "mineral": ("minerals", None, "Mineral", ITEM),
    # World
    "npc": ("world", None, "NPC", ITEM),
    "quest": ("world", None, "Quest", ITEM),
    "location": ("world", None, "Location", ITEM),
    "excavation_site": ("world", None, "Excavation Site", ITEM),
    "event": ("world", None, "Event", ITEM),
    # Calculators
    "formula": ("calculators", None, "Formula", REFERENCE),
    "mastery": ("calculators", None, "Mastery", REFERENCE),
    "mutation_chance": ("calculators", None, "Mutation Chance", REFERENCE),
    # Attached to an item, never listed on its own
    "enchantment": ("items", None, "Enchantment", REFERENCE),
    "modifier": ("minerals", None, "Modifier", REFERENCE),
    "mutation_effect": ("items", None, "Mutation", REFERENCE),
    # Merged into another item by reconciliation, listed here for completeness
    "mutation_catalyst": ("items", None, "Mutation Catalyst", REFERENCE),
    "museum_ore": ("minerals", None, "Museum Ore", REFERENCE),
    "blueprint": ("items", None, "Blueprint", REFERENCE),
    "consumable": ("items", "consumables", "Consumable", REFERENCE),
    "excavation_reward": ("world", None, "Excavation Drop", RECORD),
    "excavation_level": ("world", None, "Excavation Level", REFERENCE),
    "museum_display": ("world", None, "Museum Display", RECORD),
    "museum_info": ("world", None, "Museum Info", RECORD),
}

#: The order the types are shown in within an area.
ORDER: dict[str, tuple[str, ...]] = {
    "items": (
        "pan",
        "shovel",
        "sluice",
        "equipment",
        "trinket",
        "rune",
        "potion",
        "enchant_book",
        "relic",
        "geode",
        "treasure_chest",
        "treasure_map",
    ),
    "minerals": ("mineral",),
    "world": ("npc", "quest", "location", "excavation_site", "event"),
    "calculators": ("formula", "mastery", "mutation_chance"),
}


def area_of(item_type: str) -> str:
    """Return the area a type belongs to."""
    entry = TAXONOMY.get(item_type)
    return entry[0] if entry else "items"


def group_of(item_type: str) -> str | None:
    """Return the group a type sits in inside its area."""
    entry = TAXONOMY.get(item_type)
    return entry[1] if entry else None


def label_of(item_type: str) -> str:
    """Return the label to show a user for a type."""
    entry = TAXONOMY.get(item_type)
    if entry:
        return entry[2]
    # An unknown type still reads as something: "treasure_chest" -> "Treasure Chest".
    return item_type.replace("_", " ").strip().title()


def is_listed(item_type: str) -> bool:
    """Return True when a type is browsable on its own."""
    entry = TAXONOMY.get(item_type)
    if not entry:
        return False
    return entry[3] == ITEM


def types_in_area(area: str) -> list[str]:
    """Return the listed types of an area, in display order."""
    ordered = ORDER.get(area, ())
    known = [item_type for item_type in ordered if is_listed(item_type)]
    extra = sorted(
        item_type
        for item_type, entry in TAXONOMY.items()
        if entry[0] == area and is_listed(item_type) and item_type not in known
    )
    return known + extra


def all_types_in_area(area: str) -> list[str]:
    """Return every type of an area, listed or not, in display order."""
    ordered = ORDER.get(area, ())
    known = [item_type for item_type in ordered if item_type in TAXONOMY]
    extra = sorted(
        item_type
        for item_type, entry in TAXONOMY.items()
        if entry[0] == area and item_type not in known
    )
    return known + extra


def types_in_group(area: str, group: str) -> list[str]:
    """Return the listed types of a group, in display order."""
    return [item_type for item_type in types_in_area(area) if group_of(item_type) == group]


def taxonomy_payload() -> list[dict[str, Any]]:
    """Build the taxonomy the client reads.

    The frontend has no API of its own to ask, so the taxonomy travels with
    the snapshot.
    """
    payload: list[dict[str, Any]] = []

    for area in AREAS:
        groups = GROUPS.get(area)
        if groups:
            for group in groups:
                for item_type in types_in_group(area, group):
                    payload.append(
                        {
                            "type": item_type,
                            "area": area,
                            "group": group,
                            "label": label_of(item_type),
                            "kind": TAXONOMY[item_type][3],
                            "listed": True,
                        }
                    )
        else:
            for item_type in types_in_area(area):
                payload.append(
                    {
                        "type": item_type,
                        "area": area,
                        "group": None,
                        "label": label_of(item_type),
                        "kind": TAXONOMY[item_type][3],
                        "listed": True,
                    }
                )

    # The types that are attached to something are listed so a client can name
    # them, but they are not browsable on their own.
    for item_type, (area, group, label, kind) in TAXONOMY.items():
        if is_listed(item_type):
            continue
        payload.append(
            {
                "type": item_type,
                "area": area,
                "group": group,
                "label": label,
                "kind": kind,
                "listed": False,
            }
        )

    return payload
