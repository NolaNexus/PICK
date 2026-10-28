from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


#: The engine and its session factory, created on first use.
#:
#: They are held in one object so the factory always has a type. A pair of
#: module-level globals would leave the factory looking like ``None`` to a
#: type checker, and every caller would have to guard against it.
class _Database:
    def __init__(self) -> None:
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None

    async def get_engine(self) -> AsyncEngine:
        """Return the engine, creating it the first time."""
        if self.engine is None:
            self.engine = create_async_engine(
                normalize_database_url(settings.database_url),
                echo=settings.debug,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return self.engine

    async def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Return the session factory, creating the engine if needed."""
        await self.get_engine()
        assert self.session_factory is not None
        return self.session_factory


_database = _Database()


def normalize_database_url(url: str) -> str:
    """Convert provider-supplied PostgreSQL URLs to the asyncpg driver.

    Render (and Heroku-style providers) hand out ``postgres://`` URLs, but
    SQLAlchemy's async engine requires an explicit async driver.
    """
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


async def get_engine() -> AsyncEngine:
    """Return the engine, creating it the first time."""
    return await _database.get_engine()


async def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the session factory, creating the engine if needed."""
    return await _database.get_session_factory()


async def get_session() -> AsyncIterator[AsyncSession]:
    """A session for a request, closed when the request ends."""
    factory = await get_session_factory()
    async with factory() as session:
        yield session
