from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import News

router = APIRouter()


@router.get("", tags=["news"])
async def list_news(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    tag: str | None = Query(None, description="Filter by tag"),
    db: AsyncSession = Depends(get_session),  # noqa: B008
):
    """List news articles from Reddit."""
    query = select(News).order_by(News.published_at.desc())
    count_query = select(func.count(News.id))

    if tag:
        # Filter by tag in the JSON tags array
        query = query.where(News.tags.contains([tag]))
        count_query = count_query.where(News.tags.contains([tag]))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    result = await db.execute(query)
    articles = result.scalars().all()

    return {
        "items": [
            {
                "id": a.id,
                "title": a.title,
                "url": a.url,
                "author": a.author,
                "score": a.score,
                "tags": a.tags,
                "published_at": a.published_at,
            }
            for a in articles
        ],
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
    }


@router.get("/latest", tags=["news"])
async def latest_news(
    limit: int = Query(10, ge=1, le=50, description="Number of latest articles"),
    db: AsyncSession = Depends(get_session),  # noqa: B008
):
    """Get the latest news articles."""
    result = await db.execute(select(News).order_by(News.published_at.desc()).limit(limit))
    articles = result.scalars().all()

    return [
        {
            "id": a.id,
            "title": a.title,
            "url": a.url,
            "author": a.author,
            "score": a.score,
            "tags": a.tags,
            "published_at": a.published_at,
        }
        for a in articles
    ]


@router.get("/tags", response_model=list[str], tags=["news"])
async def list_news_tags(
    db: AsyncSession = Depends(get_session),  # noqa: B008
):
    """List available news article tags."""
    result = await db.execute(select(News.tags))
    all_tags = result.scalars().all()

    # Flatten and deduplicate tags
    unique_tags = set()
    for tags in all_tags:
        if tags:
            unique_tags.update(tags)

    return sorted(unique_tags)
