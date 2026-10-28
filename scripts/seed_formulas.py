"""One-time script to seed the formulas table from Stat Systems Guide."""

import asyncio

from sqlalchemy import select

import app.database as app_database
from app.models import Base, Formula
from app.services.seed_formulas import seed_formulas


async def main():
    """Seed formulas table with wiki-confirmed formulas.

    Idempotent: existing formulas are updated in place, so the script can run
    on every scrape cycle without creating duplicates.
    """
    engine = await app_database.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = await app_database.get_session_factory()
    async with factory() as session:
        formulas = seed_formulas(session)
        created = 0
        updated = 0
        for f in formulas:
            existing = await session.execute(
                select(Formula).where(Formula.formula_id == f["formula_id"])
            )
            row = existing.scalar_one_or_none()
            if row is None:
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
                created += 1
            else:
                row.name = f["name"]
                row.description = f["description"]
                row.formula = f["formula"]
                row.params = f["params"]
                row.confidence = f["confidence"]
                row.source_url = f["source_url"]
                row.patch_version = f["patch_version"]
                updated += 1
        await session.commit()
        print(f"Seeded {len(formulas)} formulas ({created} created, {updated} updated)")


if __name__ == "__main__":
    asyncio.run(main())
