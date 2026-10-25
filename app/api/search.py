from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Item

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search(
    q: str = Query(..., min_length=2, description="Search query"),
    type: str | None = Query(None, description="Filter by item type"),
    location: str | None = Query(None, description="Filter by location (from item data)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_session),  # noqa: B008
):
    """Full-text search across items."""
    query = select(Item)
    count_query = select(func.count(Item.id))

    search_term = f"%{q}%"
    query = query.where(
        or_(
            Item.name.ilike(search_term),
            Item.description.ilike(search_term),
            Item.data.cast(str).ilike(search_term),  # Search in JSON data
        )
    )
    count_query = count_query.where(
        or_(
            Item.name.ilike(search_term),
            Item.description.ilike(search_term),
            Item.data.cast(str).ilike(search_term),
        )
    )

    if type:
        query = query.where(Item.type == type)
        count_query = count_query.where(Item.type == type)

    if location:
        query = query.where(Item.data["location"].astext.ilike(f"%{location}%"))
        count_query = count_query.where(Item.data["location"].astext.ilike(f"%{location}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * size
    query = query.offset(offset).limit(size).order_by(Item.name)

    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": [
            {
                "id": item.id,
                "type": item.type,
                "name": item.name,
                "slug": item.slug,
                "data": item.data,
                "description": item.description,
            }
            for item in items
        ],
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
        "query": q,
    }
