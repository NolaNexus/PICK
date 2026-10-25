from datetime import datetime

from pydantic import BaseModel


class NewsResponse(BaseModel):
    id: int
    source: str
    external_id: str
    title: str
    url: str
    author: str | None = None
    score: int = 0
    published_at: datetime
    tags: list[str]

    class Config:
        from_attributes = True
