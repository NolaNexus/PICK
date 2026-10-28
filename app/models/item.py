from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    event,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

#: Every type an item row can hold.
#:
#: A native PostgreSQL enum, so a row with a type nobody declared cannot be
#: written at all. The values are the taxonomy (the types a user browses) plus
#: the fragment types (the types a parser emits only so reconciliation can fold
#: them into another row).
#:
#: The list is kept in ``alembic/versions/006_enforce_schema_invariants.py``,
#: which creates the type in the database.
ITEM_TYPE_VALUES = (
    "blueprint",
    "consumable",
    "enchant_book",
    "enchantment",
    "equipment",
    "event",
    "excavation_level",
    "excavation_reward",
    "excavation_site",
    "formula",
    "geode",
    "location",
    "mastery",
    "merchant_item",
    "mineral",
    "modifier",
    "museum_display",
    "museum_info",
    "museum_ore",
    "mutation_catalyst",
    "mutation_chance",
    "mutation_effect",
    "npc",
    "pan",
    "potion",
    "quest",
    "relic",
    "rune",
    "shovel",
    "sluice",
    "treasure_chest",
    "treasure_map",
    "trinket",
)

ItemType = Enum(
    *ITEM_TYPE_VALUES,
    name="item_type",
    # The type is created by the migration, not by the metadata, because the
    # metadata is also used to build the test database and the type has to be
    # there before the tables that use it.
    create_type=False,
)

#: The item payload, as a JSONB object.
#:
#: JSONB rather than JSON: it is smaller, it normalises the key order so two
#: equal documents compare equal, and it can be indexed. SQLite has no JSONB,
#: so it falls back to plain JSON there.
ItemData = JSON().with_variant(JSONB(), "postgresql")


class Item(Base):
    """One thing in the game, as the wiki describes it.

    The same object can be described on several wiki pages, so one row holds
    the merged result. Rows are never deleted: a row that leaves the wiki is
    marked inactive instead.
    """

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # The type is a database enum, but Python sees the string it stores: the
    # reconciler compares item.type to "relic" and assigns item.type = "relic".
    type: Mapped[str] = mapped_column(ItemType, nullable=False)
    # An item is a fact about the game, not about the page it was first seen
    # on. Deleting the page row leaves the item alone and nulls the reference.
    source_page_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("wiki_pages.id", ondelete="SET NULL"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    data: Mapped[dict[str, Any]] = mapped_column(ItemData, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(UTC),
        server_default=func.now(),
        onupdate=datetime.now(UTC),
        nullable=False,
    )

    wiki_page = relationship("WikiPage", back_populates="items")

    __table_args__ = (
        # The rules the code assumes, stated once so the database enforces them.
        CheckConstraint(
            "btrim(name) <> ''",
            name="ck_items_name_not_empty",
        ),
        # A slug is the type prefix plus a name slug. The prefix uses hyphens
        # where the type uses underscores: "enchant_book" -> "enchant-book-...".
        # This is what keeps the slug unique and deterministic whatever order
        # the pages were scraped in.
        CheckConstraint(
            "slug LIKE replace(type::text, '_', '-') || '-%'",
            name="ck_items_slug_prefix",
        ),
    )

    def __repr__(self) -> str:
        return f"<Item(type={self.type}, name={self.name!r})>"


#: The data must be a set of named fields, not a list or a scalar.
#:
#: The check is added by hand, because the function that reads the type of a
#: JSON value is named differently in PostgreSQL and in SQLite.
@event.listens_for(Item.__table__, "after_create")
def _add_data_object_check(target, connection, **kw):
    """Add the JSON object check for the dialect in use."""
    if connection.dialect.name == "postgresql":
        connection.execute(
            text(
                "ALTER TABLE items ADD CONSTRAINT ck_items_data_object "
                "CHECK (jsonb_typeof(data) = 'object')"
            )
        )
    elif connection.dialect.name == "sqlite":
        connection.execute(
            text(
                "ALTER TABLE items ADD CONSTRAINT ck_items_data_object "
                "CHECK (json_type(data) = 'object')"
            )
        )


#: The indexes for the queries that actually run.
#:
#: Every read filters on is_active, so a partial index over the live rows is
#: both smaller and faster than indexing the column on its own. PostgreSQL
#: supports partial indexes; elsewhere these are the plain columns.
Index(
    "ix_items_active_type",
    Item.type,
    postgresql_where=text("is_active"),
    sqlite_where=text("is_active"),
)
Index(
    "ix_items_active_name",
    Item.name,
    postgresql_where=text("is_active"),
    sqlite_where=text("is_active"),
)
