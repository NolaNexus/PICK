"""Shared pytest fixtures and safety guards for the test suite."""

import os
from pathlib import Path
from urllib.parse import urlparse

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import Base


class UnsafeTestDatabaseError(RuntimeError):
    """Raised when a test run is pointed at a database it could destroy."""


def get_test_database_url() -> str:
    """Return the test database URL, refusing anything that is not a test DB.

    The test fixtures drop every table when they tear down, so pointing them at
    a real database would destroy it. The URL must be set explicitly and the
    database name must end in ``_test``.
    """
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        raise UnsafeTestDatabaseError(
            "TEST_DATABASE_URL is not set. Tests must run against an explicit "
            "test database, for example "
            "TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/pick_test"
        )

    database_name = urlparse(database_url).path.lstrip("/")
    if not database_name.endswith("_test"):
        raise UnsafeTestDatabaseError(
            f"Refusing to run tests against database {database_name!r}: the "
            "database name must end in '_test'. Tests drop all tables on teardown."
        )

    return database_url


def wiki_is_reachable() -> bool:
    """Check whether the live MediaWiki API can be reached.

    Some tests scrape the real wiki. CI runners are sometimes blocked or
    rate-limited by the wiki, so those tests are skipped instead of failing
    the build when the API is not reachable.
    """
    import httpx

    try:
        response = httpx.get(
            settings.mediawiki_api_url,
            params={"action": "query", "meta": "siteinfo", "format": "json"},
            timeout=15.0,
            headers={"User-Agent": settings.user_agent},
        )
        return response.status_code == 200
    except Exception:
        return False


#: Skip marker for tests that need the live wiki.
requires_wiki = pytest.mark.skipif(
    not wiki_is_reachable(),
    reason="live MediaWiki API is not reachable from this environment",
)


@pytest_asyncio.fixture
async def test_engine():
    """Create a test database engine."""
    database_url = get_test_database_url()
    engine = create_async_engine(database_url, echo=False)

    async with engine.begin() as conn:
        # The item type enum is created by a migration, not by the metadata,
        # so it has to be made here before the tables that use it.
        await conn.run_sync(_create_item_type_enum)
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_seed_taxonomy)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        # The enum is not a table, so dropping the tables leaves it behind.
        await conn.run_sync(_drop_item_type_enum)
    await engine.dispose()


def _create_item_type_enum(connection) -> None:
    """Create the item type enum, the way the migration does."""
    from sqlalchemy import text

    from app.models.item import ITEM_TYPE_VALUES

    # A run that was killed part way through leaves the enum behind, and the
    # enum is not a table, so dropping the tables does not remove it.
    connection.execute(text("DROP TYPE IF EXISTS item_type CASCADE"))
    connection.execute(
        text(
            "CREATE TYPE item_type AS ENUM ({})".format(
                ", ".join(f"'{value}'" for value in ITEM_TYPE_VALUES)
            )
        )
    )


def _drop_item_type_enum(connection) -> None:
    """Drop the item type enum."""
    from sqlalchemy import text

    connection.execute(text("DROP TYPE IF EXISTS item_type"))


def _seed_taxonomy(connection) -> None:
    """Fill the taxonomy table, the way the migration does."""
    from pathlib import Path

    from sqlalchemy import text

    # The taxonomy rows live in the migration, because that is where the
    # taxonomy is defined.
    versions = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    module = _load_taxonomy_migration(versions)

    connection.execute(
        text(
            "INSERT INTO taxonomy "
            "(type, area, group_name, label, kind, listed, is_fragment, display_order) "
            "VALUES (:type, :area, :group_name, :label, :kind, :listed, :is_fragment, "
            ":display_order)"
        ),
        [
            {
                "type": row_type,
                "area": area,
                "group_name": group_name,
                "label": label,
                "kind": kind,
                "listed": kind == "item",
                "is_fragment": is_fragment,
                "display_order": display_order,
            }
            for row_type, area, group_name, label, kind, is_fragment, display_order in (
                module.TAXONOMY_ROWS
            )
        ],
    )


def _load_taxonomy_migration(versions: Path):
    """Load the migration that defines the taxonomy rows."""
    import importlib.util

    path = versions / "006_enforce_schema_invariants.py"
    spec = importlib.util.spec_from_file_location("migration_006", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Create a database session for testing."""
    async_session = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
