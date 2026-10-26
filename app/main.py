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
    docs_url="/docs",
    redoc_url="/redoc",
)

# Setup logging
setup_logging(json_format=not settings.debug, level=logging.INFO if not settings.debug else logging.DEBUG)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
