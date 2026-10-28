"""Prometheus metrics and health check endpoints."""

import time
from typing import Any

from fastapi import APIRouter, Depends, Request
from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session

router = APIRouter(prefix="/metrics", tags=["metrics"])

# Prometheus metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
)


@router.get("")
async def metrics() -> bytes:
    """Prometheus metrics endpoint."""
    return generate_latest()


# Health check router
health_router = APIRouter(prefix="/health", tags=["health"])


@health_router.get("")
async def health_check() -> dict[str, Any]:
    """Basic health check."""
    return {"status": "ok", "timestamp": time.time()}


@health_router.get("/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    """Readiness check - verifies DB connectivity."""
    start = time.time()
    try:
        await db.execute(text("SELECT 1"))
        db_latency = time.time() - start
        return {
            "status": "ready",
            "database": "connected",
            "db_latency_ms": round(db_latency * 1000, 2),
            "timestamp": time.time(),
        }
    except Exception as e:
        return {
            "status": "not_ready",
            "database": "disconnected",
            "error": str(e),
            "timestamp": time.time(),
        }


@health_router.get("/live")
async def liveness_check() -> dict[str, Any]:
    """Liveness check - minimal check for k8s."""
    return {"status": "alive", "timestamp": time.time()}


# Middleware for request metrics
async def metrics_middleware(request: Request, call_next):
    """Track request metrics."""
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
    ).inc()

    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path,
    ).observe(duration)

    return response
