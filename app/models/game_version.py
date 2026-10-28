"""Game version tracking model for patch detection."""

from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GameVersion(Base):
    """Track the last seen game version from Changelog."""

    __tablename__ = "game_versions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    raw_header: Mapped[str | None] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    triggered_full_scrape: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    def __repr__(self):
        return f"<GameVersion(version={self.version})>"
