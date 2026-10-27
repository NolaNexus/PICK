from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NewsResponse(BaseModel):
    """A community news article imported from Reddit."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Database identifier")
    source: str = Field(description="Source platform (currently reddit)")
    external_id: str = Field(description="Unique identifier from the source platform")
    title: str = Field(description="Article title")
    url: str = Field(description="Link to the original article")
    author: str | None = Field(default=None, description="Article author")
    score: int = Field(default=0, description="Community score at fetch time")
    published_at: datetime = Field(description="Original publication timestamp")
    tags: list[str] = Field(default_factory=list, description="Inferred topic tags")
