from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Formula
from app.schemas import FormulaResponse

router = APIRouter()


@router.get("", response_model=list[FormulaResponse], tags=["formulas"])
async def list_formulas(
    db: AsyncSession = Depends(get_session),  # noqa: B008
):
    """List all game formulas with confidence levels and sources."""
    result = await db.execute(select(Formula).order_by(Formula.name))
    return result.scalars().all()


@router.get("/{formula_id}", response_model=FormulaResponse, tags=["formulas"])
async def get_formula(
    formula_id: str,
    db: AsyncSession = Depends(get_session),  # noqa: B008
):
    """Get a single formula by its stable formula ID."""
    result = await db.execute(select(Formula).where(Formula.formula_id == formula_id))
    formula = result.scalar_one_or_none()

    if not formula:
        raise HTTPException(status_code=404, detail="Formula not found")

    return formula
