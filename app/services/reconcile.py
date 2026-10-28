"""Cross-page item reconciliation.

The same game object can appear on several wiki pages under different record
types. Relics are listed on the Relics page, sold by the Traveling Merchant,
and dropped at excavation sites. The scraper stores one row per wiki record, so
without reconciliation the merchant listing and the excavation drop overwrite
or duplicate the relic.

This module runs after all pages are scraped and:

* merges Traveling Merchant listings into the canonical item (relic, enchant
  book, potion, ...) instead of keeping a second row;
* links excavation reward rows to the item they drop, keeping the per-site drop
  table intact;
* links quests to the NPC that gives them.

It is idempotent: running it again produces the same rows and data.
"""

import logging
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
    "consumable",
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

    logger.info(
        "Reconciled items: merged=%d rewards_linked=%d chest_loot_linked=%d quests_linked=%d",
        merged,
        linked_rewards,
        linked_chest_loot,
        linked_quests,
    )
    return {
        "merged_merchant_items": merged,
        "linked_excavation_rewards": linked_rewards,
        "linked_chest_loot": linked_chest_loot,
        "linked_quests": linked_quests,
    }
