from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.item import Item


class WikiPage(Base):
    __tablename__ = "wiki_pages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    page_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    last_revision_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_scraped: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    namespace: Mapped[int] = mapped_column(
        BigInteger, default=0, server_default="0", nullable=False
    )

    # An item is a fact about the game, not about the page it was first seen
    # on. Deleting the page row leaves the item alone; the database nulls the
    # reference rather than cascading the delete, so the two agree.
    items: Mapped[list["Item"]] = relationship("Item", back_populates="wiki_page")

    def __repr__(self):
        return f"<WikiPage(title={self.title}, page_id={self.page_id})>"
