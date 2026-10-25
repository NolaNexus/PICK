"""Add game_versions table for patch detection."""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "003_add_game_versions"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "game_versions",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("version", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("raw_header", sa.Text),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("triggered_full_scrape", sa.BigInteger, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("game_versions")
