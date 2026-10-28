"""Fill in the items from the wiki pages that describe them.

Some items have a page of their own, and that page holds details the index
page does not: where the item comes from, what it does, where it drops and
how it is made. The index pages are read first, and this pass then fills in
the fields they left empty.

The index value is never overwritten. When a page and the index disagree, the
index value is kept and the difference is reported, so a human can decide.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Item
from app.services.reconcile import CANONICAL_PREFERENCE, type_prefixed_slug
from app.utils.mw_api import MediaWikiClient
from scrapers.item_page import parse_item_page
from scrapers.pages import is_index_page, is_item_page
from scrapers.wikitext import title_key

logger = logging.getLogger(__name__)

# The types an item page can enrich. The rows that describe a drop or a link
# are left alone, because they are not the item itself.
ENRICHABLE_TYPES = {
    "relic",
    "enchant_book",
    "potion",
    "consumable",
    "pan",
    "shovel",
    "sluice",
    "mineral",
    "equipment",
    "rune",
    "geode",
    "trinket",
    "blueprint",
}

# The fields that are filled in from a page. The ones the site already shows
# are not touched. The image is left out, because the index page and the item
# page often name different variants of the same picture.
PAGE_FIELDS = (
    "description",
    "overview",
    "obtained",
    "obtainment",
    "usage",
    "trivia",
    "notes",
    "museum_usage",
    "chances",
    "recipes",
    "locations",
    "effect",
    "effects",
    "price",
    "location",
    "rarity",
    "tier",
    "color",
)

# The fields whose value is a list of names, one per line on the wiki.
LIST_FIELDS = {"locations"}

# A value that counts as missing.
_EMPTY = (None, "", [], {}, ())


def _as_list(value: str) -> list[str]:
    """Turn a block of text into a list of names, one per line."""
    entries: list[str] = []
    for line in value.split("\n"):
        cleaned = line.strip()
        # A line that is only an HTML tag is not a name.
        if not cleaned or cleaned.startswith("<"):
            continue
        if cleaned not in entries:
            entries.append(cleaned)
    return entries


def _is_empty(value: Any) -> bool:
    """Return True when a stored value holds nothing."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False


def _canonical_key(item: Item) -> str:
    """The key an item is matched by."""
    return title_key(item.name)


async def enrich_items_from_pages(
    db: AsyncSession,
    client: MediaWikiClient,
) -> dict[str, Any]:
    """Fill in the items from the pages that describe them.

    Items that have a page but are not on the site yet are added as well.
    """
    items = (await db.execute(select(Item).where(Item.is_active.is_(True)))).scalars().all()

    by_name: dict[str, Item] = {}
    for item in items:
        if item.type not in ENRICHABLE_TYPES:
            continue
        key = _canonical_key(item)
        # A preferred type wins when a name exists under several types.
        existing = by_name.get(key)
        if existing is None or _is_preferred(item.type, existing.type):
            by_name[key] = item

    summary: dict[str, Any] = {
        "pages_found": 0,
        "enriched": 0,
        "fields_filled": 0,
        "conflicts": [],
        "created": [],
    }

    # The pages that could describe one of our items.
    candidates = sorted({item.name for item in by_name.values()})
    contents = await client.get_pages_with_content(candidates)
    summary["pages_found"] = len(contents)

    for title, wikitext in contents.items():
        parsed = parse_item_page(title, wikitext)
        if not parsed:
            continue

        key = title_key(parsed["name"])
        item = by_name.get(key)
        if item is None:
            continue

        filled, conflicts = _merge_into(item, parsed)
        if filled:
            summary["enriched"] += 1
            summary["fields_filled"] += filled
        summary["conflicts"].extend(conflicts)

    # The items that have a picture but no URL for it.
    summary["images_resolved"] = await _resolve_images(db, client, list(by_name.values()), contents)

    # The items that have a page but are not on the site yet.
    summary["created"] = await _create_missing(db, client, set(by_name))

    await db.commit()
    return summary


async def _resolve_images(
    db: AsyncSession,
    client: MediaWikiClient,
    items: list[Item],
    pages: dict[str, str],
) -> int:
    """Give the items that have a picture but no URL for it one.

    The index pages name the picture file, but the URL is only known once the
    wiki is asked for it. A name the wiki does not have is replaced by the
    name the item's own page uses, because the index pages sometimes name a
    picture that was renamed.
    """
    candidates: list[tuple[Item, str]] = []

    for item in items:
        if item.image_url or not isinstance(item.data, dict):
            continue
        image = item.data.get("image")
        if not isinstance(image, str) or not image.strip():
            continue
        candidates.append((item, image.strip()))

    if not candidates:
        return 0

    # Which names the wiki has, and which it has under another name.
    resolved = await client.get_image_urls(sorted({name for _, name in candidates}))

    missing = [(item, name) for item, name in candidates if name not in resolved]
    replacements: dict[str, str] = {}
    if missing:
        page_names = await client.get_image_urls(
            sorted(
                {
                    name
                    for item, _ in missing
                    for name in _page_image_names(pages.get(_page_of(item, pages), ""))
                }
            )
        )
        for item, name in missing:
            for candidate in _page_image_names(pages.get(_page_of(item, pages), "")):
                if candidate in page_names:
                    replacements[name] = candidate
                    break

    count = 0
    for item, name in candidates:
        url = resolved.get(name)
        if not url and name in replacements:
            replacement = replacements[name]
            url = resolved.get(replacement) or (await client.get_image_urls([replacement])).get(
                replacement
            )
            if url and isinstance(item.data, dict):
                item.data = {**item.data, "image": replacement}
        if url:
            item.image_url = url
            count += 1

    return count


def _page_of(item: Item, pages: dict[str, str]) -> str:
    """Find the page that describes an item."""
    key = title_key(item.name)
    for title in pages:
        if title_key(title) == key:
            return title
    return ""


def _page_image_names(wikitext: str) -> list[str]:
    """Return the picture names a page uses."""
    if not wikitext:
        return []
    names: list[str] = []
    for match in re.finditer(r"\[\[File:([^\]|]+)", wikitext):
        names.append(match.group(1).strip())
    return names


async def _create_missing(
    db: AsyncSession,
    client: MediaWikiClient,
    known: set[str],
) -> list[dict[str, Any]]:
    """Add the consumables that have a page but are not on the site yet.

    Only consumables are added. Everything else has an index page that is
    scraped already.
    """
    members = await client.get_category_members("Category:Consumables")
    if not members:
        return []

    contents = await client.get_pages_with_content(members)
    created: list[dict[str, Any]] = []

    for title, wikitext in contents.items():
        if not is_item_page(wikitext):
            continue

        # A page that lists items is an index page, not an item.
        if is_index_page(wikitext):
            continue

        parsed = parse_item_page(title, wikitext)
        if not parsed or parsed["type"] != "consumable":
            continue

        key = title_key(parsed["name"])
        if key in known:
            continue

        slug = type_prefixed_slug("consumable", _slug(parsed["name"]))
        data = dict(parsed.get("fields") or {})

        # The picture of the item is resolved from its file name.
        image = data.get("image")
        image_url = None
        if isinstance(image, str) and image:
            resolved = await client.get_image_urls([image])
            image_url = resolved.get(image)

        db.add(
            _new_item(
                item_type="consumable",
                name=parsed["name"],
                slug=slug,
                data=data,
                source_page=title,
                image_url=image_url,
            )
        )
        known.add(key)
        created.append({"name": parsed["name"], "slug": slug, "page": title})

    if created:
        await db.flush()

    return created


def _is_preferred(item_type: str, existing_type: str) -> bool:
    """Return True when a type is preferred over another for the same name."""
    order = list(CANONICAL_PREFERENCE)
    if item_type in order and existing_type in order:
        return order.index(item_type) < order.index(existing_type)
    if item_type in order:
        return True
    return False


def _merge_into(item: Item, parsed: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
    """Fill the empty fields of an item from its page.

    Returns the number of fields filled and the conflicts that were found.
    """
    data = dict(item.data or {})
    fields = parsed.get("fields", {})
    filled = 0
    conflicts: list[dict[str, Any]] = []

    for key in PAGE_FIELDS:
        value = fields.get(key)
        if value is None:
            continue

        # A list of places stays a list, whichever source it came from.
        if key in LIST_FIELDS and isinstance(value, str):
            value = _as_list(value)

        stored = data.get(key)
        if _is_empty(stored):
            data[key] = value
            filled += 1
        elif key in LIST_FIELDS and isinstance(stored, str):
            # A list of places that was stored as text becomes a list, so the
            # site can group and filter by it.
            data[key] = _as_list(stored)
            filled += 1
        elif not _values_agree(stored, value):
            conflicts.append({"item": item.name, "field": key, "stored": stored, "page": value})

    # The stat modifiers are merged by stat and unit, and the stored one wins.
    modifiers = data.get("modifiers")
    page_modifiers = parsed.get("modifiers") or []
    if page_modifiers:
        merged = _merge_modifiers(modifiers, page_modifiers)
        if merged:
            data["modifiers"] = merged
            filled += 1

    if filled:
        item.data = data
        item.updated_at = datetime.now(UTC)

    return filled, conflicts


def _values_agree(stored: Any, page: Any) -> bool:
    """Return True when a stored value and a page value mean the same thing."""
    if isinstance(stored, str) and isinstance(page, str):
        return title_key(stored) == title_key(page)
    if isinstance(stored, (int, float)) and isinstance(page, (int, float)):
        return float(stored) == float(page)
    return stored == page


def _merge_modifiers(stored: Any, page: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge the modifiers of a page into the stored ones."""
    if not isinstance(stored, list):
        return list(page)

    merged = list(stored)
    seen = {
        (modifier.get("stat"), modifier.get("unit"), modifier.get("amount"))
        for modifier in merged
        if isinstance(modifier, dict)
    }

    for modifier in page:
        key = (modifier.get("stat"), modifier.get("unit"), modifier.get("amount"))
        if key in seen:
            continue
        seen.add(key)
        merged.append(modifier)

    return merged


def _slug(name: str) -> str:
    """Turn a name into a slug fragment."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "item"


def _new_item(
    item_type: str,
    name: str,
    slug: str,
    data: dict[str, Any],
    source_page: str,
    image_url: str | None = None,
) -> Item:
    """Build an item row."""
    description = data.get("description") if isinstance(data.get("description"), str) else None

    item = Item(
        type=item_type,
        name=name,
        slug=slug,
        data=data,
        image_url=image_url,
        description=description,
        is_active=True,
    )
    # The page the item came from is kept in its data, because the wiki page
    # row is only for the pages the scraper reads as index pages.
    item.data = {**data, "source_page": source_page}
    return item
