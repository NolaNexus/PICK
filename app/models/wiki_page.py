from datetime import UTC, datetime

from sqlalchemy import BigInteger, Column, DateTime, String
from sqlalchemy.orm import relationship

from app.database import Base


class WikiPage(Base):
    __tablename__ = "wiki_pages"

    id = Column(BigInteger, primary_key=True)
    title = Column(String(255), unique=True, nullable=False, index=True)
    page_id = Column(BigInteger, unique=True, nullable=False, index=True)
    last_revision_id = Column(BigInteger, nullable=False)
    last_scraped = Column(
        DateTime(timezone=True),
        default=datetime.now(UTC),
        nullable=False,
    )
    content_hash = Column(String(64), nullable=False)
    namespace = Column(BigInteger, default=0)

    items = relationship("Item", back_populates="wiki_page", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<WikiPage(title={self.title}, page_id={self.page_id})>"
