"""Add is_active flag to items for soft-deleting items removed from the wiki."""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "items",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.create_index("ix_items_is_active", "items", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_items_is_active", table_name="items")
    op.drop_column("items", "is_active")
