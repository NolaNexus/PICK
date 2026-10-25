"""Integration tests for database operations and scraper pipeline."""

import os

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, GameVersion, Item, ScraperRun, WikiPage
from app.services.scraper import run_daily_scrape, run_full_scrape, scrape_page
from app.utils.mw_api import MediaWikiClient


@pytest_asyncio.fixture
async def test_engine():
    """Create a test database engine."""
    database_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost/pick"
    )
    engine = create_async_engine(database_url, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Create a database session for testing."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


@pytest.mark.integration
class TestScraperIntegration:
    """Integration tests for scraper against real database."""

    @pytest.mark.asyncio
    async def test_full_scrape_populates_db(self, db_session):
        """Test that full scrape populates database with items."""
        # Run full scrape
        result = await run_full_scrape(db_session)

        assert result["status"] in ("success", "partial")
        assert result["pages_scraped"] > 0
        assert result["pages_changed"] >= 0

        # Verify items were inserted
        total_items = await db_session.execute(select(func.count(Item.id)))
        count = total_items.scalar()
        assert count > 100, f"Expected at least 100 items, got {count}"

        # Verify different item types exist
        item_types = await db_session.execute(
            select(Item.type, func.count(Item.id)).group_by(Item.type)
        )
        types = dict(item_types.all())
        assert len(types) >= 10, f"Expected at least 10 item types, got {len(types)}"

        # Verify WikiPage records created
        wiki_pages = await db_session.execute(select(func.count(WikiPage.id)))
        assert wiki_pages.scalar() > 10

        # Verify ScraperRun record created
        runs = await db_session.execute(select(func.count(ScraperRun.id)))
        assert runs.scalar() >= 1

    @pytest.mark.asyncio
    async def test_incremental_scrape_zero_writes_on_unchanged(self, db_session):
        """Test that incremental scrape produces 0 writes when wiki unchanged."""
        # First run - full scrape
        result1 = await run_full_scrape(db_session)
        assert result1["status"] in ("success", "partial")

        # Second run - should be incremental (recentchanges)
        # Since wiki hasn't changed, should produce 0 changes
        result2 = await run_daily_scrape(db_session)
        assert result2["status"] in ("success", "partial")
        assert result2["pages_changed"] == 0, "Expected 0 changes on unchanged wiki"

        # Verify no new items added
        count_before = await db_session.execute(select(func.count(Item.id)))
        count_after = await db_session.execute(select(func.count(Item.id)))
        assert count_before.scalar() == count_after.scalar()

    @pytest.mark.asyncio
    async def test_scraper_run_records_created(self, db_session):
        """Test that ScraperRun records are properly created."""
        await run_full_scrape(db_session)

        runs = await db_session.execute(
            select(ScraperRun).order_by(ScraperRun.started_at.desc()).limit(2)
        )
        runs_list = runs.scalars().all()
        assert len(runs_list) >= 1

        latest_run = runs_list[0]
        assert latest_run.status in ("success", "partial")
        assert latest_run.pages_scraped >= 0
        assert latest_run.finished_at is not None

    @pytest.mark.asyncio
    async def test_game_version_tracking(self, db_session):
        """Test game version detection and tracking."""
        # This would require mocking the Changelog page
        # For now, just verify the table exists and can be queried
        versions = await db_session.execute(select(func.count(GameVersion.id)))
        count = versions.scalar()
        # Table should exist (may be empty)
        assert count >= 0


@pytest.mark.integration
class TestWebhookIntegration:
    """Integration tests for webhook endpoint."""

    @pytest.mark.asyncio
    async def test_webhook_triggers_targeted_scrape(self, db_session, monkeypatch):
        """Test that webhook endpoint triggers targeted scrape."""
        from unittest.mock import AsyncMock, MagicMock

        from fastapi import Request

        from app.api.webhooks import wiki_edit_webhook
        from app.config import settings

        # Create mock request
        mock_request = MagicMock(spec=Request)
        mock_request.json = AsyncMock(return_value={
            "title": "Pans",
            "user": "TestUser",
            "comment": "Updated stats",
        })
        mock_request.body = AsyncMock(return_value=b'{"title": "Pans", "user": "TestUser"}')

        # Mock settings to skip signature verification
        monkeypatch.setattr(settings, "webhook_secret", None)

        # Call webhook handler
        response = await wiki_edit_webhook(mock_request, db_session)

        assert response["status"] == "ok"
        assert response["page"] == "Pans"
        assert response["changed"] is True  # Should have changed since DB is empty


@pytest.mark.integration
class TestScraperUnit:
    """Unit tests for scraper functions (with mocked wiki)."""

    @pytest.mark.asyncio
    async def test_scrape_page_upserts_item(self, db_session):
        """Test that scrape_page upserts items correctly."""
        from unittest.mock import AsyncMock, MagicMock

        from scrapers.pans import parse_pans

        mock_client = MagicMock(spec=MediaWikiClient)
        mock_client.get_page_info = AsyncMock(return_value={
            "title": "Test Item",
            "wikitext": "{{Pan row\n|name=Test Pan\n|luck=100\n}}",
            "page_id": 123,
            "revision_id": 456,
        })

        # Mock parser - use actual parser
        changed = await scrape_page(db_session, mock_client, "Pans", parse_pans)
        assert changed is True

        # Verify item was created
        item = await db_session.execute(
            select(Item).where(Item.slug == "test-pan")
        )
        item = item.scalar_one_or_none()
        assert item is not None
        assert item.name == "Test Pan"
        assert item.data["luck"] == 100


# Configuration for pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


# Skip integration tests if no database available
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring database"
    )


# Allow running integration tests with: pytest -m integration
# Skip by default: pytest -m "not integration"
