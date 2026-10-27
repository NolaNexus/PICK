from datetime import UTC, datetime

from sqlalchemy import JSON, BigInteger, Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Item(Base):
    __tablename__ = "items"

    id = Column(BigInteger, primary_key=True)
    type = Column(String(50), nullable=False, index=True)
    source_page_id = Column(BigInteger, ForeignKey("wiki_pages.id"), index=True)
    wiki_id = Column(String(100), index=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    data = Column(JSON, nullable=False)
    image_url = Column(Text)
    description = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true", index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.now(UTC),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.now(UTC),
        onupdate=datetime.now(UTC),
        nullable=False,
    )

    wiki_page = relationship("WikiPage", back_populates="items")

    def __repr__(self):
        return f"<Item(id={self.id}, name={self.name}, type={self.type})>"
