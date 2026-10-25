from datetime import UTC, datetime

from sqlalchemy import JSON, BigInteger, Column, DateTime, String, Text

from app.database import Base


class News(Base):
    __tablename__ = "news_articles"

    id = Column(BigInteger, primary_key=True)
    source = Column(String(50), nullable=False, index=True)
    external_id = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    author = Column(String(100))
    score = Column(BigInteger, default=0)
    published_at = Column(DateTime(timezone=True), nullable=False, index=True)
    fetched_at = Column(
        DateTime(timezone=True),
        default=datetime.now(UTC),
        nullable=False,
    )
    content = Column(Text)
    tags = Column(JSON, default=list)

    def __repr__(self):
        return f"<News(id={self.id}, title={self.title[:50]}...)>"
