"""Shared pytest fixtures and safety guards for the test suite."""

import os
from urllib.parse import urlparse

import pytest

from app.config import settings


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
            headers={"User-Agent": settings.reddit_user_agent},
        )
        return response.status_code == 200
    except Exception:
        return False


#: Skip marker for tests that need the live wiki.
requires_wiki = pytest.mark.skipif(
    not wiki_is_reachable(),
    reason="live MediaWiki API is not reachable from this environment",
)
