"""One-time script to seed the formulas table from Stat Systems Guide."""

import asyncio

from sqlalchemy import select

from app.database import async_session_factory, engine
from app.models import Base, Formula
from app.services.formulas import seed_formulas


async def main():
    """Seed formulas table with wiki-confirmed formulas."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        formulas = seed_formulas(session)
        for f in formulas:
            existing = await session.execute(
                select(Formula).where(Formula.formula_id == f["formula_id"])
            )
            if existing.scalar_one_or_none() is None:
                session.add(
                    Formula(
                        formula_id=f["formula_id"],
                        name=f["name"],
                        description=f["description"],
                        formula=f["formula"],
                        params=f["params"],
                        confidence=f["confidence"],
                        source_url=f["source_url"],
                        patch_version=f["patch_version"],
                    )
                )
        await session.commit()
        print(f"Seeded {len(formulas)} formulas")


if __name__ == "__main__":
    asyncio.run(main())
