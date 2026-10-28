from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Item
from app.schemas import ItemResponse, PaginatedResponse
from app.taxonomy import load_taxonomy

router = APIRouter()


@router.get("/taxonomy", tags=["items"])
async def list_taxonomy(db: AsyncSession = Depends(get_session)):  # noqa: B008
    """List the item types, with the area, group and label each one has."""
    taxonomy = await load_taxonomy(db)
    return taxonomy.payload()


@router.get("", response_model=PaginatedResponse, tags=["items"])
async def list_items(
    type: str | None = Query(None, description="Filter by item type (e.g., pan, shovel, mineral)"),
    area: str | None = Query(None, description="Filter by area (e.g., items, minerals, world)"),
    group: str | None = Query(None, description="Filter by group inside an area (e.g., gear)"),
    search: str | None = Query(None, description="Search in item name and description"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_session),  # noqa: B008
):
    """List wiki items with optional type filter and text search."""
    query = select(Item).where(Item.is_active.is_(True))
    count_query = select(func.count(Item.id)).where(Item.is_active.is_(True))

    if type:
        query = query.where(Item.type == type)
        count_query = count_query.where(Item.type == type)

    if area or group:
        taxonomy = await load_taxonomy(db)
        types = [entry.type for entry in taxonomy.entries if _matches_area(entry, area, group)]
        if not types:
            return PaginatedResponse(items=[], total=0, page=page, size=size, pages=0)
        query = query.where(Item.type.in_(types))
        count_query = count_query.where(Item.type.in_(types))

    if search:
        search_term = f"%{search}%"
        query = query.where(or_(Item.name.ilike(search_term), Item.description.ilike(search_term)))
        count_query = count_query.where(
            or_(Item.name.ilike(search_term), Item.description.ilike(search_term))
        )

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * size
    query = query.offset(offset).limit(size).order_by(Item.name)

    # Execute query
    result = await db.execute(query)
    items = result.scalars().all()

    # Convert to response models
    item_responses = [
        ItemResponse(
            id=item.id,
            type=item.type,
            name=item.name,
            slug=item.slug,
            data=item.data,
            image_url=item.image_url,
            description=item.description,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in items
    ]

    return PaginatedResponse(
        items=item_responses,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


def _matches_area(entry, area: str | None, group: str | None) -> bool:
    """Return True when a type is in the requested area and group."""
    if area and entry.area != area:
        return False
    if group and entry.group != group:
        return False
    return True


@router.get("/types", response_model=list[str], tags=["items"])
async def list_item_types(
    db: AsyncSession = Depends(get_session),  # noqa: B008
):
    """List distinct item types found in the database."""
    result = await db.execute(
        select(Item.type).where(Item.is_active.is_(True)).distinct().order_by(Item.type)
    )
    types = result.scalars().all()
    return list(types)


@router.get("/type/{type}", response_model=PaginatedResponse, tags=["items"])
async def list_items_by_type(
    type: str,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_session),  # noqa: B008
):
    """List all items of a given type."""
    query = select(Item).where(Item.type == type, Item.is_active.is_(True)).order_by(Item.name)
    count_query = select(func.count(Item.id)).where(Item.type == type, Item.is_active.is_(True))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    result = await db.execute(query)
    items = result.scalars().all()

    item_responses = [
        ItemResponse(
            id=item.id,
            type=item.type,
            name=item.name,
            slug=item.slug,
            data=item.data,
            image_url=item.image_url,
            description=item.description,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in items
    ]

    return PaginatedResponse(
        items=item_responses,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get("/{slug}", response_model=ItemResponse, tags=["items"])
async def get_item(
    slug: str,
    db: AsyncSession = Depends(get_session),  # noqa: B008
):
    """Get a single item by its URL-safe slug."""
    result = await db.execute(select(Item).where(Item.slug == slug, Item.is_active.is_(True)))
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    return ItemResponse(
        id=item.id,
        type=item.type,
        name=item.name,
        slug=item.slug,
        data=item.data,
        image_url=item.image_url,
        description=item.description,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
