"""Cross-page item reconciliation.

The same game object can appear on several wiki pages under different record
types. Relics are listed on the Relics page, sold by the Traveling Merchant,
and dropped at excavation sites. The scraper stores one row per wiki record, so
without reconciliation the merchant listing and the excavation drop overwrite
or duplicate the relic.

This module runs after all pages are scraped and:

* merges Traveling Merchant listings into the canonical item (relic, enchant
  book, potion, ...) instead of keeping a second row;
* merges the records that describe another item into it: the museum row of a
  mineral, the blueprint of a piece of equipment, the drop table of an
  excavation site, the catalyst of an equipment, the museum's own displays;
* links quests to the NPC that gives them.

It is idempotent: running it again produces the same rows and data.
"""

import logging
import re
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


def _merge_museum_ores(items: list["Item"], by_name: dict[str, list["Item"]]) -> int:
    """Merge the museum row of a mineral into the mineral itself.

    The museum row holds the weight and the bonus a mineral gives in a display.
    That is a property of the mineral, not a separate item.
    """
    merged = 0

    for item in items:
        if item.type != "museum_ore" or not item.is_active:
            continue

        data = item.data or {}
        name = data.get("mineral") or item.name
        candidates = [
            candidate
            for candidate in by_name.get(_name_key(name), [])
            if candidate.type == "mineral" and candidate.is_active
        ]
        if not candidates:
            logger.warning("Museum row %s has no mineral to merge into", item.name)
            continue

        mineral = candidates[0]
        mineral.data = {
            **(mineral.data or {}),
            "museum": {
                "min_weight_kg": data.get("min_kg"),
                "max_boost": data.get("max_boost"),
                "bonus_stat": data.get("bonus_stat"),
                "rarity": data.get("rarity"),
            },
        }
        mineral.updated_at = datetime.now(UTC)
        item.is_active = False
        merged += 1

    return merged


def _merge_blueprints(items: list["Item"], by_name: dict[str, list["Item"]]) -> int:
    """Merge the blueprint of a craftable into the equipment it makes.

    A blueprint never exists without the equipment it unlocks, so the two are
    one thing: the equipment, and how to get it.
    """
    merged = 0

    for item in items:
        if item.type != "blueprint" or not item.is_active:
            continue

        candidates = [
            candidate
            for candidate in by_name.get(_name_key(item.name), [])
            if candidate.type == "equipment" and candidate.is_active
        ]
        if not candidates:
            logger.warning("Blueprint %s has no equipment to merge into", item.name)
            continue

        data = item.data or {}
        equipment = candidates[0]
        equipment.data = {
            **(equipment.data or {}),
            "blueprint": {
                "quest_giver": data.get("quest_giver"),
                "quest_name": data.get("quest_name"),
                "quest_steps": data.get("quest_steps") or [],
                "event_shop": data.get("event_shop"),
                "purchase_info": data.get("purchase_info"),
            },
        }
        equipment.updated_at = datetime.now(UTC)
        item.is_active = False
        merged += 1

    return merged


def _merge_catalysts(items: list["Item"], by_name: dict[str, list["Item"]]) -> int:
    """Merge a mutation catalyst into the equipment it rerolls.

    A catalyst names the equipment it is spent on, so it is part of that
    equipment rather than an item of its own.
    """
    merged = 0

    for item in items:
        if item.type != "mutation_catalyst" or not item.is_active:
            continue

        data = item.data or {}
        equipment_name = data.get("equipment")
        if not equipment_name:
            logger.warning("Catalyst %s names no equipment", item.name)
            continue

        candidates = [
            candidate
            for candidate in by_name.get(_name_key(equipment_name), [])
            if candidate.type == "equipment" and candidate.is_active
        ]
        if not candidates:
            logger.warning("Catalyst %s has no equipment to merge into", item.name)
            continue

        equipment = candidates[0]
        equipment.data = {
            **(equipment.data or {}),
            "catalyst": {
                "name": item.name,
                "mineral": data.get("mineral"),
                "rarity": data.get("rarity"),
            },
        }
        equipment.updated_at = datetime.now(UTC)
        item.is_active = False
        merged += 1

    return merged


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
    merged = 0

    sites = {
        _site_key(_data_of(item).get("site_name") or item.name): item
        for item in items
        if item.type == "excavation_site" and item.is_active
    }
    if not sites:
        return 0

    for item in items:
        if item.type != "excavation_reward" or not item.is_active:
            continue

        data = item.data or {}
        site = sites.get(_site_key(data.get("site")))
        if site is None:
            logger.warning("Drop %s names no known site", item.name)
            continue

        drops = list(_data_of(site).get("drops") or [])
        drops.append(
            {
                "item_slug": data.get("item_slug"),
                "name": item.name,
                "chance": data.get("chance"),
                "activation": data.get("activation"),
                "description": data.get("description"),
            }
        )
        site.data = {**(site.data or {}), "drops": drops}
        site.updated_at = datetime.now(UTC)
        item.is_active = False
        merged += 1

    return merged


def _merge_museum_displays(items: list["Item"]) -> int:
    """Fold the museum's display tiers and info into the Museum sub-location.

    The museum is a place in Caldera Park, so its displays and its description
    belong to it rather than being items of their own.
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
            item_data = _data_of(item)
            displays.append(
                {
                    "name": item.name,
                    "rarity": item_data.get("rarity"),
                    "free_displays": item_data.get("free_displays"),
                    "locked_displays": item_data.get("locked_displays"),
                    "total_displays": item_data.get("total_displays"),
                    "money_price": item_data.get("money_price"),
                    "shards_price": item_data.get("shards_price"),
                }
            )
            item.is_active = False
            merged += 1

        elif item.type == "museum_info" and item.is_active:
            item_data = _data_of(item)
            info = {
                "description": item_data.get("description"),
                "location": item_data.get("location"),
                "staff": item_data.get("staff") or [],
                "extras": item_data.get("extras") or [],
            }
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
