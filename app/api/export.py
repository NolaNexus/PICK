from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.snapshot import build_snapshot

router = APIRouter()


@router.get("/snapshot", tags=["export"])
async def export_snapshot(db: AsyncSession = Depends(get_session)):  # noqa: B008
    """Export the full public dataset as a single JSON snapshot for client-side caching."""
    return await build_snapshot(db)
