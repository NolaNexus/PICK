"""The taxonomy of item types.

Every item type the scraper can produce is described once: which area it
belongs to, the group it sits in inside that area, the label to show a user,
and whether it is listed on its own or attached to something else.

Without this, the type is just a string a parser happened to emit, and the
site ends up with a flat list of cryptic names.

The descriptions live in the ``taxonomy`` table, so the database owns the list
and the column that holds a type is constrained to the same values. This
module reads that table and answers the questions the rest of the code asks
about a type.

Some types are only ever a part of another item. A parser that reads the
museum table emits a row for each mineral it lists there, and reconciliation
folds that row into the mineral. Those rows are marked ``is_fragment``: they
are not items a user browses, and the site should not offer them a place of
their own.

The taxonomy is read through an async loader, because it lives in the
database. Everything that needs it already has a session.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = [
    "AREAS",
    "GROUPS",
    "Taxonomy",
    "TaxonomyEntry",
    "load_taxonomy",
]

#: An area is a place the user can browse.
AREAS: tuple[str, ...] = ("items", "minerals", "world", "calculators")

#: The groups inside the items area.
GROUPS: dict[str, tuple[str, ...]] = {
    "items": ("gear", "consumables", "treasure"),
}

#: What a type is.
#:
#: "record" is still part of the vocabulary the client understands, but no type
#: uses it now: the types that were records were fragments.
ITEM = "item"
RECORD = "record"
REFERENCE = "reference"


@dataclass(frozen=True)
class TaxonomyEntry:
    """What the database says about one type."""

    type: str
    area: str
    group: str | None
    label: str
    kind: str
    listed: bool
    is_fragment: bool
    display_order: int


class Taxonomy:
    """The types, loaded from the database.

    The rows are held in memory once they have been read. The taxonomy changes
    when the game changes, which is rare, and the process that reads it is
    short-lived, so there is nothing to invalidate.
    """

    def __init__(self, entries: list[TaxonomyEntry]):
        self._entries = {entry.type: entry for entry in entries}
        self._by_area: dict[str, list[TaxonomyEntry]] = {}
        for entry in entries:
            self._by_area.setdefault(entry.area, []).append(entry)
        for rows in self._by_area.values():
            rows.sort(key=lambda entry: (entry.display_order, entry.type))

    def __contains__(self, item_type: object) -> bool:
        return item_type in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    def get(self, item_type: str) -> TaxonomyEntry | None:
        return self._entries.get(item_type)

    @property
    def entries(self) -> list[TaxonomyEntry]:
        return list(self._entries.values())

    @property
    def types(self) -> list[str]:
        return list(self._entries)

    def area_of(self, item_type: str) -> str:
        entry = self._entries.get(item_type)
        return entry.area if entry else "items"

    def group_of(self, item_type: str) -> str | None:
        entry = self._entries.get(item_type)
        return entry.group if entry else None

    def label_of(self, item_type: str) -> str:
        entry = self._entries.get(item_type)
        if entry:
            return entry.label
        # An unknown type still reads as something: "treasure_chest" -> "Treasure Chest".
        return item_type.replace("_", " ").strip().title()

    def is_fragment(self, item_type: str) -> bool:
        entry = self._entries.get(item_type)
        return bool(entry and entry.is_fragment)

    def is_listed(self, item_type: str) -> bool:
        entry = self._entries.get(item_type)
        return bool(entry and entry.listed)

    def types_in_area(self, area: str) -> list[str]:
        """Return the listed types of an area, in display order."""
        return [entry.type for entry in self._by_area.get(area, []) if entry.listed]

    def all_types_in_area(self, area: str) -> list[str]:
        """Return every type of an area, listed or not, in display order."""
        return [entry.type for entry in self._by_area.get(area, [])]

    def types_in_group(self, area: str, group: str) -> list[str]:
        """Return the listed types of a group, in display order."""
        return [
            entry.type
            for entry in self._by_area.get(area, [])
            if entry.listed and entry.group == group
        ]

    def payload(self) -> list[dict[str, Any]]:
        """Build the taxonomy the client reads.

        The frontend has no API of its own to ask, so the taxonomy travels
        with the snapshot.
        """
        payload: list[dict[str, Any]] = []

        for area in AREAS:
            groups = GROUPS.get(area)
            if groups:
                for group in groups:
                    for item_type in self.types_in_group(area, group):
                        entry = self._entries[item_type]
                        payload.append(
                            {
                                "type": item_type,
                                "area": area,
                                "group": group,
                                "label": entry.label,
                                "kind": entry.kind,
                                "listed": True,
                            }
                        )
            else:
                for item_type in self.types_in_area(area):
                    entry = self._entries[item_type]
                    payload.append(
                        {
                            "type": item_type,
                            "area": area,
                            "group": None,
                            "label": entry.label,
                            "kind": entry.kind,
                            "listed": True,
                        }
                    )

        # The types that are attached to something are listed so a client can
        # name them, but they are not browsable on their own.
        for entry in self._entries.values():
            if entry.listed:
                continue
            payload.append(
                {
                    "type": entry.type,
                    "area": entry.area,
                    "group": entry.group,
                    "label": entry.label,
                    "kind": entry.kind,
                    "listed": False,
                }
            )

        return payload


async def load_taxonomy(db) -> Taxonomy:
    """Read the taxonomy out of the database."""
    from sqlalchemy import select

    from app.models import Taxonomy as TaxonomyRow

    result = await db.execute(
        select(TaxonomyRow).order_by(TaxonomyRow.area, TaxonomyRow.display_order, TaxonomyRow.type)
    )
    return Taxonomy(
        [
            TaxonomyEntry(
                type=row.type,
                area=row.area,
                group=row.group_name,
                label=row.label,
                kind=row.kind,
                listed=bool(row.listed),
                is_fragment=bool(row.is_fragment),
                display_order=row.display_order,
            )
            for row in result.scalars().all()
        ]
    )
