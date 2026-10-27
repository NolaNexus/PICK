"""Helper utilities for the FastAPI app."""

from fastapi import Request


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host if request.client else "unknown"


def rate_limit_key(request: Request) -> str:
    """Generate a rate limit key for the request."""
    return f"{get_client_ip(request)}"


class ValidationError(Exception):
    """Custom validation error for API validation."""

    pass


def format_time_seconds(seconds: float) -> str:
    """Format seconds into human-readable time (HH:MM:SS)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
