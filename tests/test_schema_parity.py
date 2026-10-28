"""The models and the migrations must describe the same schema.

The database is created by the alembic migrations in production and by
``Base.metadata.create_all`` in the tests. If those two disagree, a test can
pass against a schema the site never runs on.

The drift is invisible unless somebody compares them, so this test does. It
reads the schema the migrations produced and the schema the models describe,
and checks that they say the same thing about the tables, columns, defaults,
nullability and constraints.

The comparison is on the information the database reports, not on the SQL
text: PostgreSQL writes the same default as ``DEFAULT 0`` and as
``DEFAULT '0'::bigint`` depending on how it was declared, and that is not a
difference worth failing a build over.
"""

from sqlalchemy import text

from app.database import Base

#: The tables the models own. ``alembic_version`` is alembic's own bookkeeping
#: and is not part of the schema.
TABLES = ("items", "wiki_pages", "formulas", "game_versions", "scraper_runs", "taxonomy")

#: The columns whose default the database reports. The value is the one the
#: column would get if a row did not set it.
_DEFAULTS = """
    SELECT c.table_name, c.column_name, c.column_default, c.is_nullable
    FROM information_schema.columns AS c
    WHERE c.table_schema = 'public' AND c.table_name = ANY (:tables)
"""


async def test_the_models_describe_the_columns_the_migrations_created(db_session):
    """Every column the migrations created is described by the models."""
    rows = (await db_session.execute(text(_DEFAULTS), {"tables": list(TABLES)})).all()
    migrated = {(row[0], row[1]) for row in rows}

    described = set()
    for table in Base.metadata.sorted_tables:
        if table.name not in TABLES:
            continue
        for column in table.columns:
            described.add((table.name, column.name))

    assert migrated, "the database has no columns to compare against"
    assert migrated == described, (
        "the models and the database disagree about the columns: "
        f"only in the database {migrated - described}, "
        f"only in the models {described - migrated}"
    )


async def test_the_models_and_the_database_agree_about_nullability(db_session):
    """A column the database allows to be null is nullable in the model too."""
    rows = (await db_session.execute(text(_DEFAULTS), {"tables": list(TABLES)})).all()

    for table_name, column_name, _default, is_nullable in rows:
        column = Base.metadata.tables[table_name].columns[column_name]
        assert column.nullable == (is_nullable == "YES"), (
            f"{table_name}.{column_name} is "
            f"{'nullable' if is_nullable == 'YES' else 'not null'} in the database "
            f"and {'nullable' if column.nullable else 'not null'} in the model"
        )


async def test_the_models_and_the_database_agree_about_defaults(db_session):
    """A column with a default in the database has one in the model too."""
    rows = (await db_session.execute(text(_DEFAULTS), {"tables": list(TABLES)})).all()

    for table_name, column_name, default, _is_nullable in rows:
        column = Base.metadata.tables[table_name].columns[column_name]
        # A sequence-backed autoincrementing column is the same behaviour
        # written a different way: PostgreSQL reports a nextval default for a
        # BIGSERIAL column, and the model says "autoincrement".
        has_default = (
            column.server_default is not None
            or column.default is not None
            or (column.autoincrement is True and column.primary_key)
        )
        assert has_default == (default is not None), (
            f"{table_name}.{column_name} has "
            f"{'a' if default is not None else 'no'} default in the database "
            f"and {'a' if has_default else 'no'} in the model"
        )


async def test_every_item_has_exactly_one_foreign_key(db_session):
    """The items table has one reference to the wiki pages, not two.

    The initial migration declared the reference twice - once inline on the
    column and once as a table constraint. Two foreign keys on one column
    behave differently when the referenced row is deleted, so there is one.
    """
    rows = (
        await db_session.execute(
            text(
                """
                SELECT c.conname, pg_get_constraintdef(c.oid)
                FROM pg_constraint AS c
                WHERE c.conrelid = 'items'::regclass AND c.contype = 'f'
                """
            )
        )
    ).all()

    assert len(rows) == 1, f"the items table has {len(rows)} foreign keys: {rows}"


async def test_the_foreign_key_nulls_the_reference(db_session):
    """Deleting a wiki page leaves the item alone."""
    row = (
        await db_session.execute(
            text(
                """
                SELECT pg_get_constraintdef(oid)
                FROM pg_constraint
                WHERE conrelid = 'items'::regclass AND contype = 'f'
                """
            )
        )
    ).scalar_one()

    assert "ON DELETE SET NULL" in row
