from datetime import UTC, datetime

from sqlalchemy import JSON, BigInteger, Column, DateTime, String, Text

from app.database import Base


class Formula(Base):
    __tablename__ = "formulas"

    id = Column(BigInteger, primary_key=True)
    formula_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    formula = Column(Text, nullable=False)
    params = Column(JSON, nullable=False)
    confidence = Column(String(20), nullable=False)
    source_url = Column(Text)
    patch_version = Column(String(50))
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self):
        return f"<Formula(formula_id={self.formula_id}, name={self.name}, confidence={self.confidence})>"
