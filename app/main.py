import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST

from app.api import register_api_routes
from app.config import settings
from app.logging_config import setup_logging
from app.monitoring import health_router, metrics, metrics_middleware

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Community-built companion API for the Roblox game **Prospecting!**. "
        "It exposes wiki-sourced items, formulas, calculators, "
        "search, and public dataset snapshots.\n\n"
        "Data is scraped from the official Prospecting! wiki on a schedule. "
        "Calculator endpoints are grouped under `/api/v1/calculators`."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "items", "description": "Wiki items such as pans, shovels, minerals, and relics."},
        {"name": "formulas", "description": "Game formulas and their confidence levels."},
        {"name": "calculators", "description": "Stat, EV, museum, and hunting calculators."},
        {"name": "meta", "description": "Application and dataset metadata."},
        {"name": "search", "description": "Full-text search across items."},
        {"name": "export", "description": "Public dataset snapshot export."},
        {"name": "health", "description": "Liveness and readiness checks."},
        {"name": "metrics", "description": "Prometheus metrics."},
    ],
)

# Setup logging
setup_logging(
    json_format=not settings.debug, level=logging.INFO if not settings.debug else logging.DEBUG
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add metrics middleware
app.middleware("http")(metrics_middleware)


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "ok",
        "docs": "/docs",
    }


# Metrics endpoint
@app.get("/metrics")
async def metrics_endpoint() -> Response:
    return Response(content=metrics(), media_type=CONTENT_TYPE_LATEST)


# Health endpoints
app.include_router(health_router, prefix="/api/v1/health")


register_api_routes(app)
