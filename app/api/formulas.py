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
    formulas = result.scalars().all()

    return [
        FormulaResponse(
            id=f.id,
            name=f.name,
            formula=f.formula,
            description=f.description,
            variables=f.variables,
            confidence=f.confidence,
            source_url=f.source_url,
            created_at=f.created_at,
            updated_at=f.updated_at,
        )
        for f in formulas
    ]


@router.get("/{formula_id}", response_model=FormulaResponse, tags=["formulas"])
async def get_formula(
    formula_id: str,
    db: AsyncSession = Depends(get_session),  # noqa: B008
):
    """Get a single formula by its ID."""
    result = await db.execute(select(Formula).where(Formula.id == formula_id))
    formula = result.scalar_one_or_none()

    if not formula:
        raise HTTPException(status_code=404, detail="Formula not found")

    return FormulaResponse(
        id=formula.id,
        name=formula.name,
        formula=formula.formula,
        description=formula.description,
        variables=formula.variables,
        confidence=formula.confidence,
        source_url=formula.source_url,
        created_at=formula.created_at,
        updated_at=formula.updated_at,
    )
