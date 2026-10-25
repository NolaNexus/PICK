
from pydantic import BaseModel


class FormulaResponse(BaseModel):
    id: int
    formula_id: str
    name: str
    confidence: str
    source_url: str | None = None

    class Config:
        from_attributes = True
