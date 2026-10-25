"""Integration tests for API endpoints using a test database."""

import os
from typing import Any

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_session
from app.main import app
from app.models import Item, WikiPage


@pytest_asyncio.fixture
async def test_engine():
    """Create a test database engine."""
    database_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost/pick",
    )
    engine = create_async_engine(database_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

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


@pytest_asyncio.fixture
async def client(db_session):
    """Create an AsyncTestClient with overridden database session."""

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


async def _add_wiki_page_and_item(
    db_session: AsyncSession,
    title: str,
    page_id: int,
    item_type: str,
    item_name: str,
    item_slug: str,
    item_data: dict[str, Any] | None = None,
) -> Item:
    """Helper to insert a wiki page and item."""
    wiki_page = WikiPage(
        title=title,
        page_id=page_id,
        last_revision_id=1,
        content_hash="abc123",
    )
    db_session.add(wiki_page)
    await db_session.flush()

    item = Item(
        type=item_type,
        name=item_name,
        slug=item_slug,
        data=item_data or {},
        image_url=None,
        description=f"{item_name} description.",
        wiki_page=wiki_page,
    )
    db_session.add(item)
    await db_session.commit()
    return item


@pytest.mark.asyncio
async def test_api_meta_endpoint(client, db_session):
    """Test GET /api/v1/meta returns database statistics."""
    await _add_wiki_page_and_item(
        db_session, "Pans", 100, "pan", "Rusty Pan", "rusty-pan",
        {"luck": 1, "capacity": 5},
    )

    response = await client.get("/api/v1/meta")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "PICK"
    assert data["database"]["total_items"] == 1
    assert data["database"]["items_by_type"] == {"pan": 1}


@pytest.mark.asyncio
async def test_api_list_items(client, db_session):
    """Test GET /api/v1/items returns paginated items."""
    for i in range(5):
        await _add_wiki_page_and_item(
            db_session, f"Pans Page {i}", 100 + i, "pan", f"Pan {i}",
            f"pan-{i}", {"luck": float(i), "capacity": float(i * 5)},
        )

    response = await client.get("/api/v1/items")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["size"] == 20
    assert len(data["items"]) == 5
    assert data["items"][0]["name"] == "Pan 0"


@pytest.mark.asyncio
async def test_api_list_items_filter_by_type(client, db_session):
    """Test GET /api/v1/items with type filter."""
    await _add_wiki_page_and_item(
        db_session, "Pans", 200, "pan", "Rusty Pan", "rusty-pan", {"luck": 1},
    )
    await _add_wiki_page_and_item(
        db_session, "Shovels", 201, "shovel", "Rusty Shovel", "rusty-shovel",
        {"strength": 1},
    )

    response = await client.get("/api/v1/items?type=pan")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["type"] == "pan"


@pytest.mark.asyncio
async def test_api_list_items_search(client, db_session):
    """Test GET /api/v1/items with search query."""
    await _add_wiki_page_and_item(
        db_session, "Pans", 300, "pan", "Golden Pan", "golden-pan", {"luck": 10},
    )

    response = await client.get("/api/v1/items?search=Golden")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Golden Pan"


@pytest.mark.asyncio
async def test_api_get_item_by_slug(client, db_session):
    """Test GET /api/v1/items/{slug} returns a single item."""
    await _add_wiki_page_and_item(
        db_session, "Pans", 400, "pan", "Rusty Pan", "rusty-pan", {"luck": 1},
    )

    response = await client.get("/api/v1/items/rusty-pan")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "rusty-pan"
    assert data["name"] == "Rusty Pan"
    assert data["type"] == "pan"


@pytest.mark.asyncio
async def test_api_get_item_not_found(client):
    """Test GET /api/v1/items/{slug} returns 404 for missing item."""
    response = await client.get("/api/v1/items/nonexistent-item")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_list_item_types(client, db_session):
    """Test GET /api/v1/items/types returns distinct types."""
    await _add_wiki_page_and_item(
        db_session, "Pans", 500, "pan", "Rusty Pan", "rusty-pan", {},
    )
    await _add_wiki_page_and_item(
        db_session, "Shovels", 501, "shovel", "Rusty Shovel", "rusty-shovel", {},
    )

    response = await client.get("/api/v1/items/types")
    assert response.status_code == 200
    types = response.json()
    assert "pan" in types
    assert "shovel" in types


@pytest.mark.asyncio
async def test_api_search_endpoint(client, db_session):
    """Test GET /api/v1/search searches items by name and data."""
    await _add_wiki_page_and_item(
        db_session, "Pans", 600, "pan", "Silver Pan", "silver-pan",
        {"location": "Rubble Creek"},
    )

    response = await client.get("/api/v1/search?q=Silver")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Silver Pan"

    response = await client.get("/api/v1/search?q=Rubble")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["data"]["location"] == "Rubble Creek"
