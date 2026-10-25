
from pydantic import BaseModel


class ItemResponse(BaseModel):
    id: int
    type: str
    wiki_id: str | None = None
    name: str
    slug: str
    data: dict | None = None
    description: str | None = None
    image_url: str | None = None

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(
        cls,
        total: int,
        page: int = 1,
        size: int = 20,
    ) -> "PaginatedResponse":
        pages = (total + size - 1) // size if size > 0 else 0
        return cls(total=total, page=page, size=size, pages=pages)
