"""Normalise the payload stored in ``items.data``.

The wiki is the source of the shape, but the shape it produces is not the shape
the site should read. This module is the single place where a parser's payload
is cleaned before it is written, so the database and the published snapshot
agree about what a field is called and what type it has.
"""

from __future__ import annotations

from typing import Any

from scrapers.wikitext import render_text


def clean_text(value: Any) -> Any:
    """Render a wiki-text value to plain text when it is a string."""
    if isinstance(value, str):
        return render_text(value)
    return value


def _drop_empty(value: Any) -> Any:
    """Remove values that hold nothing, without touching 0 or False."""
    if value is None:
        return None
    if isinstance(value, str):
        return value if value.strip() else None
    if isinstance(value, list):
        cleaned = [_drop_empty(item) for item in value]
        cleaned = [item for item in cleaned if item is not None]
        return cleaned if cleaned else None
    if isinstance(value, dict):
        cleaned = {key: _drop_empty(item) for key, item in value.items()}
        cleaned = {key: item for key, item in cleaned.items() if item is not None}
        return cleaned if cleaned else None
    return value


def normalize_item_data(data: Any, item_type: str | None = None) -> dict[str, Any]:
    """Return a cleaned copy of an item's data payload.

    The type is accepted so per-type rules can be added later without changing
    the call sites. Today the rules are common to every type.
    """
    if not isinstance(data, dict):
        data = {}

    cleaned: dict[str, Any] = {}
    for key, value in data.items():
        if key in {"source_page"}:
            continue
        if key == "description":
            continue
        cleaned[key] = clean_text(value)

    cleaned = _drop_empty(cleaned) or {}
    if not isinstance(cleaned, dict):
        cleaned = {}
    return cleaned


def public_item_data(data: Any) -> dict[str, Any]:
    """Return the subset of an item's data that is published."""
    if not isinstance(data, dict):
        return {}
    # The DB may keep a richer payload than the public file. Today they are the
    # same, but the door stays open for fields that are useful while scraping
    # and not useful to the site.
    return {key: value for key, value in data.items() if value is not None}
