from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FormulaResponse(BaseModel):
    """A game formula with its expression and confidence metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Database identifier")
    formula_id: str = Field(description="Stable formula key used by API clients")
    name: str = Field(description="Human-readable formula name")
    description: str | None = Field(default=None, description="Explanation of the formula")
    formula: str = Field(description="Formula expression")
    params: dict[str, Any] = Field(description="Parameters or components used by the formula")
    confidence: str = Field(description="Confidence level: confirmed, likely, or speculative")
    source_url: str | None = Field(default=None, description="Wiki source URL")
    patch_version: str | None = Field(
        default=None, description="Game patch that introduced or verified the formula"
    )
    created_at: datetime = Field(description="Creation timestamp")
