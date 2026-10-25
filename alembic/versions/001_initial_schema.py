import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    # Create wiki_pages table
    op.create_table(
        "wiki_pages",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("title", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("page_id", sa.BigInteger, nullable=False, unique=True, index=True),
        sa.Column("last_revision_id", sa.BigInteger, nullable=False),
        sa.Column(
            "last_scraped",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("namespace", sa.BigInteger, server_default="0"),
    )

    # Create items table
    op.create_table(
        "items",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column(
            "source_page_id",
            sa.BigInteger,
            sa.ForeignKey("wiki_pages.id"),
            index=True,
        ),
        sa.Column("type", sa.String(50), nullable=False, index=True),
        sa.Column("wiki_id", sa.String(100), index=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("slug", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("data", sa.JSON, nullable=False),
        sa.Column("image_url", sa.Text),
        sa.Column("description", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_page_id"], ["wiki_pages.id"], ondelete="SET NULL"
        ),
    )

    # Create formulas table
    op.create_table(
        "formulas",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("formula_id", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("formula", sa.Text, nullable=False),
        sa.Column("params", sa.JSON, nullable=False),
        sa.Column("confidence", sa.String(20), nullable=False),
        sa.Column("source_url", sa.Text),
        sa.Column("patch_version", sa.String(50)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create news_articles table
    op.create_table(
        "news_articles",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("source", sa.String(50), nullable=False, index=True),
        sa.Column("external_id", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("author", sa.String(100)),
        sa.Column("score", sa.BigInteger, server_default="0"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("content", sa.Text),
        sa.Column("tags", sa.JSON, server_default="[]"),
    )

    # Create scraper_runs table
    op.create_table(
        "scraper_runs",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20)),
        sa.Column("pages_scraped", sa.BigInteger, server_default="0"),
        sa.Column("pages_changed", sa.BigInteger, server_default="0"),
        sa.Column("pages_errors", sa.BigInteger, server_default="0"),
        sa.Column("error_log", sa.Text),
    )

    # Add indexes
    op.create_index("ix_items_slug", "items", "slug", unique=True)
    op.create_index("ix_items_type", "items", "type")
    op.create_index("ix_news_published_at", "news_articles", "published_at")


def downgrade() -> None:
    op.drop_table("scraper_runs")
    op.drop_table("news_articles")
    op.drop_table("formulas")
    op.drop_table("items")
    op.drop_table("wiki_pages")