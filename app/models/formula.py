from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import JSON, BigInteger, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

#: How sure a formula is.
#:
#: A formula read straight off the wiki is confirmed; one worked out from the
#: wiki's curves is approximate. The file contract constrains it to the same two
#: values, so the literal is declared once and used by both.
Confidence = Literal["approximate", "confirmed"]


class Formula(Base):
    __tablename__ = "formulas"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    formula_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    formula: Mapped[str] = mapped_column(Text, nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    confidence: Mapped[Confidence] = mapped_column(String(20), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    patch_version: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self):
        return f"<Formula(formula_id={self.formula_id}, name={self.name}, confidence={self.confidence})>"
