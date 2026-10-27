"""Shared pytest fixtures and safety guards for the test suite."""

import os
from urllib.parse import urlparse


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
