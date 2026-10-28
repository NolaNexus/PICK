"""The shapes the scrapers produce.

The parsers read a wiki page and turn it into rows. Every one of them
produces the same shape, so the scraper can rely on it and the typechecker can
check it.

Without this, a parser returns ``dict[str, Any]`` and everything it produces
is unchecked: a type the database does not accept, a missing name, a payload
that is not an object. All of those are caught by the database now, but they
are caught at the end of a long pipeline rather than at the parser.
"""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class ParsedItem(TypedDict):
    """One item as a parser read it from the wiki.

    The keys are the same for every parser. ``slug`` and ``image_url`` are
    always present; ``image_url`` is always ``None`` at this point, because the
    wiki stores the name of an image file and the scraper resolves it to a URL
    afterwards.
    """

    id: str
    type: str
    name: str
    slug: str
    data: dict[str, Any]
    image_url: str | None
    description: NotRequired[str | None]


class ParsedItemPage(TypedDict):
    """What an item's own wiki page holds.

    This is a different shape from :class:`ParsedItem`: an item page is read
    to fill in the fields a table left empty, not to make an item.
    """

    name: str
    type: str
    fields: dict[str, Any]
    modifiers: list[dict[str, Any]]


class NpcEntry(TypedDict):
    """One NPC as a gallery lists it, before the entries are grouped.

    The gallery gives a name, the region it was seen in, its picture and the
    page it links to. Grouping turns those into items.
    """

    name: str
    region: str
    image: str
    link_target: str
