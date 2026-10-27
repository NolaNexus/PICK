"""Change scraper_runs.id from BigInteger to Integer with autoincrement."""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "002_change_scraper_runs_id_to_integer"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL: change column type and rebuild the autoincrement sequence.
    # SQLite: batch mode handles column recreation.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(
            "scraper_runs", "id",
            existing_type=sa.BigInteger,
            type_=sa.Integer,
            nullable=False,
            existing_server_default=None,
        )
        # Recreate the sequence for the Integer column.
        op.execute("DROP SEQUENCE IF EXISTS scraper_runs_id_seq CASCADE")
        op.execute("CREATE SEQUENCE scraper_runs_id_seq AS INTEGER")
        op.execute("ALTER TABLE scraper_runs ALTER COLUMN id SET DEFAULT nextval('scraper_runs_id_seq')")
    elif bind.dialect.name == "sqlite":
        with op.batch_alter_table("scraper_runs", schema=None) as batch_op:
            batch_op.alter_column(
                "id",
                existing_type=sa.BigInteger,
                type_=sa.Integer,
                nullable=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE scraper_runs ALTER COLUMN id SET DEFAULT NULL")
        op.execute("DROP SEQUENCE IF EXISTS scraper_runs_id_seq CASCADE")
        op.execute("CREATE SEQUENCE scraper_runs_id_seq AS BIGINT")
        op.execute("ALTER TABLE scraper_runs ALTER COLUMN id SET DEFAULT nextval('scraper_runs_id_seq')")
        op.alter_column(
            "scraper_runs", "id",
            existing_type=sa.Integer,
            type_=sa.BigInteger,
            nullable=False,
            existing_server_default=None,
        )
    elif bind.dialect.name == "sqlite":
        with op.batch_alter_table("scraper_runs", schema=None) as batch_op:
            batch_op.alter_column(
                "id",
                existing_type=sa.Integer,
                type_=sa.BigInteger,
                nullable=False,
            )
