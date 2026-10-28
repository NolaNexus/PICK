from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ScraperRun(Base):
    __tablename__ = "scraper_runs"

    # The id is a bigint with an explicit sequence, the way migration 002 and
    # then migration 006 left it. The model names the same sequence so the two
    # cannot disagree about the schema.
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        server_default=text("nextval('scraper_runs_id_seq'::regclass)"),
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str | None] = mapped_column(String(20))
    # These three are nullable in the database, which is what the initial
    # migration created. The model matches it rather than being stricter, so
    # the two cannot disagree about the schema.
    pages_scraped: Mapped[int | None] = mapped_column(BigInteger, default=0, server_default="0")
    pages_changed: Mapped[int | None] = mapped_column(BigInteger, default=0, server_default="0")
    pages_errors: Mapped[int | None] = mapped_column(BigInteger, default=0, server_default="0")
    error_log: Mapped[str | None] = mapped_column(Text)

    def __repr__(self):
        return (
            f"<ScraperRun(id={self.id}, status={self.status}, pages_scraped={self.pages_scraped})>"
        )
