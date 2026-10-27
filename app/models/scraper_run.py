from datetime import UTC, datetime

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text

from app.database import Base


class ScraperRun(Base):
    __tablename__ = "scraper_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(
        DateTime(timezone=True),
        default=datetime.now(UTC),
        nullable=False,
    )
    finished_at = Column(DateTime(timezone=True))
    status = Column(String(20))
    pages_scraped = Column(BigInteger, default=0)
    pages_changed = Column(BigInteger, default=0)
    pages_errors = Column(BigInteger, default=0)
    error_log = Column(Text)

    def __repr__(self):
        return (
            f"<ScraperRun(id={self.id}, status={self.status}, pages_scraped={self.pages_scraped})>"
        )
