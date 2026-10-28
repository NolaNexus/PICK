"""The database refuses to store a row that breaks the rules.

The schema used to accept anything: any type, any data shape, an empty name, a
slug that did not derive from its type. The rules lived in Python, so a bad
write was only noticed when a later scrape produced something odd.

These tests are the measure of that change. Each one asserts that the
database rejects a row it used to accept, so they are not a description of the
schema but a check on it.
"""

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.models import Item


def _item_kwargs(**overrides) -> dict:
    """A row that satisfies every constraint."""
    kwargs = {
        "type": "mineral",
        "name": "Quartz",
        "slug": "mineral-quartz",
        "data": {"rarity": "common"},
        "image_url": None,
        "description": "A common mineral.",
        "is_active": True,
    }
    kwargs.update(overrides)
    return kwargs


class TestTheSlugFollowsTheType:
    """A slug is the type prefix plus a name slug.

    This is what keeps ``items.slug`` unique and deterministic no matter which
    order the pages were scraped in.
    """

    async def test_a_matching_slug_is_accepted(self, db_session):
        item = Item(**_item_kwargs())
        db_session.add(item)
        await db_session.commit()
        assert item.id is not None

    async def test_a_slug_from_another_type_is_rejected(self, db_session):
        """The type prefix and the slug have to agree."""
        item = Item(**_item_kwargs(slug="pan-quartz"))
        db_session.add(item)
        with pytest.raises(DBAPIError):
            await db_session.commit()

    async def test_the_prefix_uses_hyphens(self, db_session):
        """An underscored type becomes a hyphenated prefix.

        "enchant_book" produces "enchant-book-...", not "enchant_book-...".
        """
        item = Item(
            **_item_kwargs(
                type="enchant_book",
                name="Blessed Enchant Book",
                slug="enchant-book-blessed-enchant-book",
            )
        )
        db_session.add(item)
        await db_session.commit()
        assert item.id is not None

    async def test_an_underscored_prefix_is_rejected(self, db_session):
        item = Item(
            **_item_kwargs(
                type="enchant_book",
                name="Blessed Enchant Book",
                slug="enchant_book-blessed-enchant-book",
            )
        )
        db_session.add(item)
        with pytest.raises(DBAPIError):
            await db_session.commit()


class TestTheTypeMustBeKnown:
    async def test_a_declared_type_is_accepted(self, db_session):
        item = Item(**_item_kwargs(type="relic", slug="relic-quartz"))
        db_session.add(item)
        await db_session.commit()
        assert item.id is not None

    async def test_an_undeclared_type_is_rejected(self, db_session):
        """A type nobody declared cannot be written at all.

        The type is a database enum, so this is a type error rather than a
        constraint violation.
        """
        item = Item(**_item_kwargs(type="not_a_real_type"))
        db_session.add(item)
        with pytest.raises((DBAPIError, IntegrityError)):
            await db_session.commit()

    async def test_a_fragment_type_can_still_be_written(self, db_session):
        """A parser writes these before reconciliation folds them away."""
        item = Item(**_item_kwargs(type="museum_ore", slug="museum-ore-quartz"))
        db_session.add(item)
        await db_session.commit()
        assert item.id is not None


class TestTheNameMustNotBeEmpty:
    async def test_an_empty_name_is_rejected(self, db_session):
        item = Item(**_item_kwargs(name="", slug="mineral-quartz"))
        db_session.add(item)
        with pytest.raises(DBAPIError):
            await db_session.commit()

    async def test_a_blank_name_is_rejected(self, db_session):
        """Whitespace is not a name."""
        item = Item(**_item_kwargs(name="   ", slug="mineral-quartz"))
        db_session.add(item)
        with pytest.raises(DBAPIError):
            await db_session.commit()


class TestTheDataMustBeAnObject:
    async def test_an_object_is_accepted(self, db_session):
        item = Item(**_item_kwargs())
        db_session.add(item)
        await db_session.commit()
        assert item.id is not None

    async def test_an_array_is_rejected(self, db_session):
        """The payload is a set of named fields, not a list."""
        item = Item(**_item_kwargs(data=[1, 2, 3]))
        db_session.add(item)
        with pytest.raises(DBAPIError):
            await db_session.commit()

    async def test_a_scalar_is_rejected(self, db_session):
        item = Item(**_item_kwargs(data="not an object"))
        db_session.add(item)
        with pytest.raises(DBAPIError):
            await db_session.commit()


class TestTheDeadColumnIsGone:
    async def test_there_is_no_wiki_id_column(self, db_session):
        """The column was null in every row and written by nobody."""
        columns = (
            (
                await db_session.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'items'"
                    )
                )
            )
            .scalars()
            .all()
        )
        assert "wiki_id" not in columns

    async def test_the_item_row_has_no_wiki_id(self, db_session):
        item = Item(**_item_kwargs())
        db_session.add(item)
        await db_session.commit()
        assert not hasattr(item, "wiki_id")


class TestTheIndexes:
    async def test_the_live_rows_have_a_partial_index(self, db_session):
        """Every read filters on is_active, so the index covers the live rows."""
        indexes = (
            (
                await db_session.execute(
                    text(
                        "SELECT indexname FROM pg_indexes "
                        "WHERE tablename = 'items' AND indexname LIKE 'ix_items_active%'"
                    )
                )
            )
            .scalars()
            .all()
        )
        assert set(indexes) == {"ix_items_active_type", "ix_items_active_name"}

    async def test_the_partial_indexes_only_cover_the_live_rows(self, db_session):
        indexdef = (
            await db_session.execute(
                text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_items_active_type'")
            )
        ).scalar_one()
        assert "is_active" in indexdef

    async def test_the_slug_still_has_one_index(self, db_session):
        """A second index on the slug would only cost space."""
        indexes = (
            (
                await db_session.execute(
                    text(
                        "SELECT indexname FROM pg_indexes "
                        "WHERE tablename = 'items' AND indexname LIKE '%slug%'"
                    )
                )
            )
            .scalars()
            .all()
        )
        assert list(indexes) == ["ix_items_slug"]


class TestTheTaxonomyTable:
    async def test_it_is_filled(self, db_session):
        from app.models import Taxonomy

        rows = (await db_session.execute(select(Taxonomy))).scalars().all()
        assert rows
        assert all(row.label for row in rows)

    async def test_a_listed_type_must_be_an_item(self, db_session):
        """A type that is browsable on its own has the kind "item"."""
        result = await db_session.execute(
            text("SELECT count(*) FROM taxonomy WHERE listed <> (kind = 'item')")
        )
        assert result.scalar_one() == 0

    async def test_the_kind_must_be_one_of_three(self, db_session):
        result = await db_session.execute(
            text("SELECT count(*) FROM taxonomy WHERE kind NOT IN ('item', 'record', 'reference')")
        )
        assert result.scalar_one() == 0
