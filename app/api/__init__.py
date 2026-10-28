"""API route registration - registers all versioned API routes."""

from fastapi import FastAPI


def register_api_routes(app: FastAPI) -> None:
    """Register all versioned API routes."""
    from app.api import (
        calculators as calculators_router,
    )
    from app.api import (
        export as export_router,
    )
    from app.api import (
        formulas as formulas_router,
    )
    from app.api import (
        items as items_router,
    )
    from app.api import (
        meta as meta_router,
    )
    from app.api import (
        search as search_router,
    )

    api_prefix = "/api/v1"
    app.include_router(items_router.router, prefix=f"{api_prefix}/items", tags=["items"])
    app.include_router(formulas_router.router, prefix=f"{api_prefix}/formulas", tags=["formulas"])
    app.include_router(
        calculators_router.router, prefix=f"{api_prefix}/calculators", tags=["calculators"]
    )
    app.include_router(meta_router.router, prefix=f"{api_prefix}/meta", tags=["meta"])
    app.include_router(search_router.router, prefix=f"{api_prefix}/search", tags=["search"])
    app.include_router(export_router.router, prefix=f"{api_prefix}/export", tags=["export"])
