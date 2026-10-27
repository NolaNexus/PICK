from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ItemResponse(BaseModel):
    id: int = Field(description="Unique item identifier")
    type: str = Field(description="Item type (e.g., pan, shovel, mineral)")
    wiki_id: str | None = Field(default=None, description="Original wiki ID")
    name: str = Field(description="Item display name")
    slug: str = Field(description="URL-safe slug")
    data: dict | None = Field(default=None, description="Item data JSON")
    image_url: str | None = Field(default=None, description="Item image URL")
    description: str | None = Field(default=None, description="Item description")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "type": "pan",
                "wiki_id": None,
                "name": "Rusty Pan",
                "slug": "rusty-pan",
                "data": {"luck": 1, "capacity": 5, "strength": 0.2, "speed": 0.8},
                "image_url": None,
                "description": "A rusty pan for gold panning.",
                "created_at": "2026-10-25T00:00:00Z",
                "updated_at": "2026-10-25T00:00:00Z",
            }
        },
    }


class PaginatedResponse(BaseModel):
    total: int = Field(description="Total number of items")
    page: int = Field(default=1, ge=1, description="Current page number")
    size: int = Field(default=20, ge=1, le=100, description="Items per page")
    pages: int = Field(description="Total number of pages")
    items: list[Any] = Field(description="List of items on this page")

    @classmethod
    def create(
        cls,
        total: int,
        page: int = 1,
        size: int = 20,
        items: list[Any] | None = None,
    ) -> "PaginatedResponse":
        pages = (total + size - 1) // size if size > 0 else 0
        return cls(
            total=total,
            page=page,
            size=size,
            pages=pages,
            items=items or [],
        )

    model_config = {
        "json_schema_extra": {
            "example": {
                "total": 23,
                "page": 1,
                "size": 20,
                "pages": 2,
                "items": [],
            }
        },
    }
