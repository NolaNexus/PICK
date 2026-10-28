"""Drop the news_articles table; the news feature is being reworked later."""

from alembic import op

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("news_articles")


def downgrade() -> None:
    import sqlalchemy as sa

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
