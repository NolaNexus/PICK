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


# Lazy engine creation - only create when a database URL is configured
engine: AsyncEngine | None = None
async_session_factory = None


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
    global engine, async_session_factory
    if engine is None or async_session_factory is None:
        engine = create_async_engine(
            normalize_database_url(settings.database_url),
            echo=settings.debug,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
        async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return engine


async def get_session() -> AsyncSession:
    await get_engine()
    async_session = async_session_factory
    async with async_session() as session:
        yield session
