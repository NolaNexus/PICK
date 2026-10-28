"""Cross-page item reconciliation.

The same game object can appear on several wiki pages under different record
types. Relics are listed on the Relics page, sold by the Traveling Merchant,
and dropped at excavation sites. The scraper stores one row per wiki record, so
without reconciliation the merchant listing and the excavation drop overwrite
or duplicate the relic.

This module runs after all pages are scraped and:

* merges Traveling Merchant listings into the canonical item (relic, enchant
  book, potion, ...) instead of keeping a second row;
* folds the fragments that describe another item into it: the museum row of a
  mineral, the blueprint of a piece of equipment, the drop table of an
  excavation site, the catalyst of an equipment, the museum's own displays;
* links quests to the NPC that gives them.

The folds are described by one table, ``FOLDS``, so that adding a new one is
a matter of writing down where it comes from and what it becomes.

It is idempotent: running it again produces the same rows and data.
"""

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models import Item

logger = logging.getLogger(__name__)

# Records that describe game world entities rather than things a player owns.
ENTITY_TYPES = {"npc", "quest", "location", "event", "museum_info"}

# Per-site drop table rows. These stay separate from the item itself so the
# drop table remains browsable, but they link back to it.
DROP_TABLE_TYPES = {"excavation_site", "excavation_level", "excavation_reward"}

# Merchant listings are resolved into a canonical item when one exists.
MERCHANT_TYPES = {"merchant_item"}

# Types that we prefer to treat as the canonical row for a name.
CANONICAL_PREFERENCE = (
    "relic",
    "enchant_book",
    "potion",
    "pan",
    "shovel",
    "mineral",
    "gear",
)

# Merchant listings carry a volatile snapshot: stock, price and currency rotate
# every daily spawn and can be rerolled, so they are stored as "last seen".
MERCHANT_FIELDS = ("price_cash", "price_shards", "stock", "chance_percent")

# The excavation sites name their tier, e.g. "Volcanic Ruins (A-Site)".
_SITE_SUFFIX = re.compile(r"\s*\([A-F]-Site\)\s*$", re.IGNORECASE)

# The wiki writes one site's name in the plural.
SITE_NAME_ALIASES = {
    "mysterious meteors": "mysterious meteor",
}


def type_prefixed_slug(item_type: str, slug: str) -> str:
    """Namespace an item slug with its item type.

    ``items.slug`` is globally unique, but the same name can exist under
    different types (a "Dredge Master" NPC and a "Dredge Master" quest). Using
    the type as a prefix makes every slug deterministic and independent of the
    order pages happen to be scraped in.
    """
    prefix = item_type.strip().lower().replace("_", "-")
    if not prefix:
        return slug
    return f"{prefix}-{slug}"


def _name_key(name: str | None) -> str:
    """Normalize a display name for cross-page matching."""
    return " ".join((name or "").split()).lower()


def _merchant_listing(item: "Item", seen_at: datetime) -> dict[str, Any]:
    """Build the merchant snapshot stored on a canonical item."""
    data = item.data or {}
    cash = data.get("price_cash")
    shards = data.get("price_shards")

    if cash and not shards:
        currency = "cash"
    elif shards and not cash:
        currency = "shards"
    else:
        currency = "either"

    listing: dict[str, Any] = {field: data.get(field) for field in MERCHANT_FIELDS}
    listing["currency"] = currency
    listing["last_seen"] = seen_at.isoformat()
    return listing


def _normalize_location(name: str | None) -> str:
    """Normalize a location name for matching (ignores a leading 'The')."""
    return _name_key(name).removeprefix("the ")


def _npc_locations(npc: "Item") -> set[str]:
    """Return the locations an NPC appears in."""
    data = npc.data if isinstance(npc.data, dict) else {}
    locations = data.get("locations")
    if isinstance(locations, list):
        return {_name_key(location) for location in locations if isinstance(location, str)}
    region = data.get("region")
    return {_name_key(region)} if region else set()


def _find_geode(items: list["Item"], location: str) -> "Item | None":
    """Return the geode variant for a location, e.g. 'Volcanic Sands'."""
    key = _normalize_location(location)
    for item in items:
        if item.type != "geode":
            continue
        data = item.data if isinstance(item.data, dict) else {}
        if _normalize_location(data.get("location")) == key:
            return item
    return None


def _pick_canonical(candidates: list["Item"], exclude: "Item") -> "Item | None":
    """Return the canonical item for a name, ignoring world entities and drops."""
    usable = [
        candidate
        for candidate in candidates
        if candidate.id != exclude.id
        and candidate.type not in ENTITY_TYPES
        and candidate.type not in DROP_TABLE_TYPES
        and candidate.type not in MERCHANT_TYPES
    ]
    for preferred in CANONICAL_PREFERENCE:
        for candidate in usable:
            if candidate.type == preferred:
                return candidate
    return usable[0] if usable else None


def _data_of(item: "Item") -> dict[str, Any]:
    """Return the data of an item as a plain dictionary."""
    data = item.data
    return data if isinstance(data, dict) else {}


def _find_by_name(items: list["Item"], name: str, item_type: str) -> "Item | None":
    """Return the active item of a type with a given name."""
    key = _name_key(name)
    for item in items:
        if item.type == item_type and item.is_active and _name_key(item.name) == key:
            return item
    return None


@dataclass(frozen=True)
class FoldContext:
    """The lookups a fold needs to find the item a fragment belongs to."""

    items: list["Item"]
    by_name: dict[str, list["Item"]]
    sites: dict[str, "Item"]


@dataclass(frozen=True)
class Fold:
    """How one kind of fragment is folded into the item it describes.

    A fragment is a row that holds part of another item: the museum row of a
    mineral, the blueprint of a piece of equipment. The fold says which type
    it is, how to find the item it belongs to, and what is written on it.
    """

    fragment: str
    key: str
    project: Callable[["Item"], dict[str, Any]]
    match: Callable[["Item", FoldContext], "Item | None"]
    append: bool = False


def _fold_context(items: list["Item"], by_name: dict[str, list["Item"]]) -> FoldContext:
    """Build the lookups the folds share."""
    sites = {
        _site_key(_data_of(item).get("site_name") or item.name): item
        for item in items
        if item.type == "excavation_site" and item.is_active
    }
    return FoldContext(items=items, by_name=by_name, sites=sites)


def _first_of_type(by_name: dict[str, list["Item"]], name: str, item_type: str) -> "Item | None":
    """Return the first active item of a type with a given name."""
    for candidate in by_name.get(_name_key(name), []):
        if candidate.type == item_type and candidate.is_active:
            return candidate
    return None


def _match_by_name(item_type: str) -> Callable[["Item", FoldContext], "Item | None"]:
    """Build a matcher that finds the item of a type with the same name."""

    def match(fragment: "Item", context: FoldContext) -> "Item | None":
        return _first_of_type(context.by_name, fragment.name or "", item_type)

    return match


def _match_mineral_for_museum(fragment: "Item", context: FoldContext) -> "Item | None":
    """A museum row names the mineral it belongs to."""
    name = _data_of(fragment).get("mineral") or fragment.name
    return _first_of_type(context.by_name, name or "", "mineral")


def _match_equipment_named(fragment: "Item", context: FoldContext) -> "Item | None":
    """A catalyst names the equipment it is spent on."""
    name = _data_of(fragment).get("equipment")
    if not name:
        return None
    return _first_of_type(context.by_name, name, "equipment")


def _match_site_for_drop(fragment: "Item", context: FoldContext) -> "Item | None":
    """A drop names the excavation site it falls at."""
    return context.sites.get(_site_key(_data_of(fragment).get("site")))


def _project_museum(fragment: "Item") -> dict[str, Any]:
    """The weight and the bonus a mineral gives in a museum display."""
    data = _data_of(fragment)
    return {
        "min_weight_kg": data.get("min_kg"),
        "max_boost": data.get("max_boost"),
        "bonus_stat": data.get("bonus_stat"),
        "rarity": data.get("rarity"),
    }


def _project_blueprint(fragment: "Item") -> dict[str, Any]:
    """How a piece of equipment is crafted."""
    data = _data_of(fragment)
    return {
        "quest_giver": data.get("quest_giver"),
        "quest_name": data.get("quest_name"),
        "quest_steps": data.get("quest_steps") or [],
        "event_shop": data.get("event_shop"),
        "purchase_info": data.get("purchase_info"),
    }


def _project_catalyst(fragment: "Item") -> dict[str, Any]:
    """The catalyst that rerolls a piece of equipment."""
    data = _data_of(fragment)
    return {
        "name": fragment.name,
        "mineral": data.get("mineral"),
        "rarity": data.get("rarity"),
    }


def _project_drop(fragment: "Item") -> dict[str, Any]:
    """One row of an excavation site's drop table."""
    data = _data_of(fragment)
    return {
        "item_slug": data.get("item_slug"),
        "name": fragment.name,
        "chance": data.get("chance"),
        "activation": data.get("activation"),
        "description": data.get("description"),
    }


def _project_display(fragment: "Item") -> dict[str, Any]:
    """One display tier of the museum."""
    data = _data_of(fragment)
    return {
        "name": fragment.name,
        "rarity": data.get("rarity"),
        "free_displays": data.get("free_displays"),
        "locked_displays": data.get("locked_displays"),
        "total_displays": data.get("total_displays"),
        "money_price": data.get("money_price"),
        "shards_price": data.get("shards_price"),
    }


def _project_museum_info(fragment: "Item") -> dict[str, Any]:
    """The museum's description and the people and places in it."""
    data = _data_of(fragment)
    return {
        "description": data.get("description"),
        "location": data.get("location"),
        "staff": data.get("staff") or [],
        "extras": data.get("extras") or [],
    }


#: The folds, by the type of the fragment they fold.
FOLDS: dict[str, Fold] = {
    "museum_ore": Fold(
        fragment="museum_ore",
        key="museum",
        project=_project_museum,
        match=_match_mineral_for_museum,
    ),
    "blueprint": Fold(
        fragment="blueprint",
        key="blueprint",
        project=_project_blueprint,
        match=_match_by_name("equipment"),
    ),
    "mutation_catalyst": Fold(
        fragment="mutation_catalyst",
        key="catalyst",
        project=_project_catalyst,
        match=_match_equipment_named,
    ),
    "excavation_reward": Fold(
        fragment="excavation_reward",
        key="drops",
        project=_project_drop,
        match=_match_site_for_drop,
        append=True,
    ),
}


def _apply_folds(
    items: list["Item"],
    by_name: dict[str, list["Item"]],
    fragment_type: str,
) -> int:
    """Fold one kind of fragment into the item it describes.

    A fragment whose item is not in the wiki is left alone: the information
    it holds would otherwise be lost, and it is not browsable on its own.
    """
    fold = FOLDS[fragment_type]
    context = _fold_context(items, by_name)
    merged = 0

    for item in items:
        if item.type != fold.fragment or not item.is_active:
            continue

        target = fold.match(item, context)
        if target is None:
            logger.warning("%s %s has nothing to fold into", fold.fragment, item.name)
            continue

        value = fold.project(item)
        if fold.append:
            existing = list(_data_of(target).get(fold.key) or [])
            existing.append(value)
            target.data = {**(target.data or {}), fold.key: existing}
        else:
            target.data = {**(target.data or {}), fold.key: value}

        target.updated_at = datetime.now(UTC)
        item.is_active = False
        merged += 1

    return merged


def _merge_museum_ores(items: list["Item"], by_name: dict[str, list["Item"]]) -> int:
    """Merge the museum row of a mineral into the mineral itself.

    The museum row holds the weight and the bonus a mineral gives in a display.
    That is a property of the mineral, not a separate item.
    """
    return _apply_folds(items, by_name, "museum_ore")


def _merge_blueprints(items: list["Item"], by_name: dict[str, list["Item"]]) -> int:
    """Merge the blueprint of a craftable into the equipment it makes.

    A blueprint never exists without the equipment it unlocks, so the two are
    one thing: the equipment, and how to get it.
    """
    return _apply_folds(items, by_name, "blueprint")


def _merge_catalysts(items: list["Item"], by_name: dict[str, list["Item"]]) -> int:
    """Merge a mutation catalyst into the equipment it rerolls.

    A catalyst names the equipment it is spent on, so it is part of that
    equipment rather than an item of its own.
    """
    return _apply_folds(items, by_name, "mutation_catalyst")


def _site_key(name: str) -> str:
    """Return the comparison key of an excavation site name."""
    if not name:
        return ""
    cleaned = _SITE_SUFFIX.sub("", str(name)).strip()
    return _name_key(SITE_NAME_ALIASES.get(cleaned.lower(), cleaned))


def _merge_excavation_drops(items: list["Item"]) -> int:
    """Fold the drop tables into the excavation sites they belong to.

    The site is the record a player browses, so its drops are part of it. The
    items that drop stay their own items.
    """
    return _apply_folds(items, {}, "excavation_reward")


def _merge_museum_displays(items: list["Item"]) -> int:
    """Fold the museum's display tiers and info into the Museum sub-location.

    The museum is a place in Caldera Park, so its displays and its description
    belong to it rather than being items of their own.

    These two write into a sub-location of the location record rather than a
    key of their own, so they are folded here rather than through ``FOLDS``.
    """
    merged = 0

    museum = _find_museum_sublocation(items)
    if museum is None:
        logger.warning("No Museum sub-location to merge the displays into")
        return 0

    data = _data_of(museum)
    sublocations = data.get("sublocations") or []
    if not sublocations:
        return 0

    target = next(
        (entry for entry in sublocations if _name_key(entry.get("name")) == "museum"),
        None,
    )
    if target is None:
        logger.warning("The Museum sub-location was not found")
        return 0

    displays = list(target.get("displays") or [])
    info = dict(target.get("info") or {})

    for item in items:
        if item.type == "museum_display" and item.is_active:
            displays.append(_project_display(item))
            item.is_active = False
            merged += 1

        elif item.type == "museum_info" and item.is_active:
            info = _project_museum_info(item)
            item.is_active = False
            merged += 1

    # The list is rebuilt rather than edited in place: the database only sees
    # a change when the stored value is replaced.
    updated = [
        {**entry, "displays": displays, "info": info} if entry is target else entry
        for entry in sublocations
    ]
    museum.data = {**data, "sublocations": updated}
    museum.updated_at = datetime.now(UTC)

    return merged


def _find_museum_sublocation(items: list["Item"]) -> "Item | None":
    """Return the location record that holds the Museum sub-location."""
    for item in items:
        if item.type != "location" or not item.is_active:
            continue
        sublocations = _data_of(item).get("sublocations") or []
        if any(_name_key(entry.get("name")) == "museum" for entry in sublocations):
            return item
    return None


def _resolve_mineral_areas(items: list["Item"]) -> tuple[int, list[str]]:
    """Work out which area each mineral is found in.

    A mineral names the places it drops at, and those places sit inside an
    area. The area names are kept on the mineral so the site can filter by
    area without a join.
    """
    places: dict[str, str] = {}

    for item in items:
        if item.type != "location" or not item.is_active:
            continue
        for entry in _data_of(item).get("sublocations") or []:
            name = entry.get("name")
            if isinstance(name, str) and name:
                places[_name_key(name)] = item.name

    resolved = 0
    unmatched: list[str] = []

    for item in items:
        if item.type != "mineral" or not item.is_active:
            continue

        locations = _data_of(item).get("locations")
        if not isinstance(locations, list):
            continue

        areas: list[str] = []
        for location in locations:
            if not isinstance(location, str):
                continue
            area = places.get(_name_key(location))
            if area and area not in areas:
                areas.append(area)
            elif area is None and location not in unmatched:
                unmatched.append(location)

        if areas:
            item.data = {**_data_of(item), "areas": areas}
            item.updated_at = datetime.now(UTC)
            resolved += 1

    return resolved, unmatched


async def reconcile_items(db: "AsyncSession") -> dict[str, int]:
    """Merge and link duplicate records that describe the same game object."""
    from app.models import Item

    items = (await db.execute(select(Item).where(Item.is_active.is_(True)))).scalars().all()

    by_name: dict[str, list[Item]] = {}
    for item in items:
        by_name.setdefault(_name_key(item.name), []).append(item)

    merged = 0
    for item in items:
        if item.type not in MERCHANT_TYPES:
            continue

        canonical = _pick_canonical(by_name.get(_name_key(item.name), []), exclude=item)
        if canonical is None:
            # Nothing else represents this item (for example Traveler's
            # Backpack), so the merchant row is the canonical row.
            item.data = {**(item.data or {}), "sold_by_merchant": True}
            continue

        seen_at = item.updated_at or datetime.now(UTC)
        item.is_active = False
        canonical.data = {
            **(canonical.data or {}),
            "merchant": _merchant_listing(item, seen_at),
            "sold_by_merchant": True,
        }
        canonical.updated_at = datetime.now(UTC)
        merged += 1

    # Canonical items that are themselves merchant-native (an enchant book is
    # only sold by the merchant) also expose the normalized listing. Potions
    # are not merchant-native: their cost comes from the Potions wiki page, so
    # their listing is merged in from the merchant row above.
    for item in items:
        if item.type == "enchant_book" and "price_cash" in (item.data or {}):
            seen_at = item.updated_at or datetime.now(UTC)
            item.data = {
                **(item.data or {}),
                "merchant": _merchant_listing(item, seen_at),
                "sold_by_merchant": True,
            }

    linked_rewards = 0
    for item in items:
        if item.type != "excavation_reward" or not item.is_active:
            continue

        geode_location = (item.data or {}).get("geode_location")
        if geode_location:
            geode = _find_geode(items, geode_location)
            if geode is not None:
                item.data = {**(item.data or {}), "item_slug": geode.slug}
                linked_rewards += 1
                continue

        canonical = _pick_canonical(by_name.get(_name_key(item.name), []), exclude=item)
        if canonical is None:
            continue
        item.data = {**(item.data or {}), "item_slug": canonical.slug}
        linked_rewards += 1

    linked_chest_loot = 0
    for item in items:
        if item.type != "treasure_chest":
            continue
        # Copy each entry: mutating the loaded JSON in place makes SQLAlchemy
        # see no change, because the "old" value already contains the mutation.
        loot = [dict(entry) for entry in (item.data or {}).get("loot") or []]
        for entry in loot:
            if entry.get("kind") != "item" or entry.get("item_slug"):
                continue
            canonical = _pick_canonical(by_name.get(_name_key(entry.get("name")), []), exclude=item)
            if canonical is not None:
                entry["item_slug"] = canonical.slug
                linked_chest_loot += 1
        item.data = {**(item.data or {}), "loot": loot}

    linked_quests = 0
    for item in items:
        if item.type != "quest":
            continue
        data = item.data or {}
        npc_name = data.get("npc")
        if not npc_name:
            continue

        npcs = [npc for npc in by_name.get(_name_key(npc_name), []) if npc.type == "npc"]
        if not npcs:
            continue

        # Prefer the NPC in the quest's own location when several share a name.
        location = _name_key(data.get("location"))
        npc = next(
            (candidate for candidate in npcs if location in _npc_locations(candidate)),
            npcs[0],
        )
        item.data = {**data, "npc_slug": npc.slug}
        linked_quests += 1

    # The records that describe another item are folded into it.
    merged_museum_ores = _merge_museum_ores(items, by_name)
    merged_blueprints = _merge_blueprints(items, by_name)
    merged_catalysts = _merge_catalysts(items, by_name)
    merged_drops = _merge_excavation_drops(items)
    merged_museum = _merge_museum_displays(items)
    resolved_areas, unmatched_places = _resolve_mineral_areas(items)

    # A consumable is a relic: both are used up. The type is corrected so the
    # item appears under the Consumables group as a relic.
    reclassified = 0
    for item in items:
        if item.type != "consumable" or not item.is_active:
            continue
        item.type = "relic"
        item.slug = type_prefixed_slug("relic", item.slug.removeprefix("consumable-"))
        item.updated_at = datetime.now(UTC)
        reclassified += 1

    logger.info(
        "Reconciled items: merged=%d rewards_linked=%d chest_loot_linked=%d quests_linked=%d "
        "museum_ores=%d blueprints=%d catalysts=%d drops=%d museum=%d reclassified=%d areas=%d",
        merged,
        linked_rewards,
        linked_chest_loot,
        linked_quests,
        merged_museum_ores,
        merged_blueprints,
        merged_catalysts,
        merged_drops,
        merged_museum,
        reclassified,
        resolved_areas,
    )
    if unmatched_places:
        logger.info("Mineral places with no area: %s", ", ".join(sorted(unmatched_places)))

    return {
        "merged_merchant_items": merged,
        "linked_excavation_rewards": linked_rewards,
        "linked_chest_loot": linked_chest_loot,
        "linked_quests": linked_quests,
        "merged_museum_ores": merged_museum_ores,
        "merged_blueprints": merged_blueprints,
        "merged_catalysts": merged_catalysts,
        "merged_excavation_drops": merged_drops,
        "merged_museum": merged_museum,
        "reclassified_consumables": reclassified,
        "resolved_mineral_areas": resolved_areas,
        "unmatched_mineral_places": len(unmatched_places),
    }
