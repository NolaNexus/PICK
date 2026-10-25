"""Game version tracking model for patch detection."""

from datetime import UTC, datetime

from sqlalchemy import BigInteger, Column, DateTime, String, Text

from app.database import Base


class GameVersion(Base):
    """Track the last seen game version from Changelog."""

    __tablename__ = "game_versions"

    id = Column(BigInteger, primary_key=True)
    version = Column(String(100), nullable=False, unique=True, index=True)
    raw_header = Column(Text)
    detected_at = Column(
        DateTime(timezone=True),
        default=datetime.now(UTC),
        nullable=False,
    )
    triggered_full_scrape = Column(BigInteger, default=0)

    def __repr__(self):
        return f"<GameVersion(version={self.version})>"
