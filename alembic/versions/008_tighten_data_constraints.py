"""Tighten the constraints the data layer relies on.

The previous revisions made the database enforce the shape of items and the
taxonomy. This one does the same for the rest of the tables: formulas and
scraper runs. It also fixes the defaults that were evaluated once when the
module was imported, so a timestamp written later in the process is no longer
the time the process started.

This is a PostgreSQL migration. The tests build their schema from the models
rather than from the migrations, and the models carry the same rules.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # ------------------------------------------------------------------
    # scraper_runs: the counters are counts, not optional values
    # ------------------------------------------------------------------
    op.execute("UPDATE scraper_runs SET pages_scraped = 0 WHERE pages_scraped IS NULL")
    op.execute("UPDATE scraper_runs SET pages_changed = 0 WHERE pages_changed IS NULL")
    op.execute("UPDATE scraper_runs SET pages_errors = 0 WHERE pages_errors IS NULL")
    op.alter_column("scraper_runs", "pages_scraped", nullable=False, server_default="0")
    op.alter_column("scraper_runs", "pages_changed", nullable=False, server_default="0")
    op.alter_column("scraper_runs", "pages_errors", nullable=False, server_default="0")

    # ------------------------------------------------------------------
    # formulas: confidence is one of two values, params is a JSON object
    # ------------------------------------------------------------------
    op.execute("ALTER TABLE formulas ALTER COLUMN params TYPE jsonb USING params::jsonb")
    op.execute(
        "ALTER TABLE formulas ADD CONSTRAINT ck_formulas_confidence "
        "CHECK (confidence IN ('approximate', 'confirmed'))"
    )
    op.execute(
        "ALTER TABLE formulas ADD CONSTRAINT ck_formulas_params_object "
        "CHECK (jsonb_typeof(params) = 'object')"
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("ALTER TABLE formulas DROP CONSTRAINT IF EXISTS ck_formulas_params_object")
    op.execute("ALTER TABLE formulas DROP CONSTRAINT IF EXISTS ck_formulas_confidence")
    op.execute("ALTER TABLE formulas ALTER COLUMN params TYPE json USING params::json")

    op.alter_column("scraper_runs", "pages_scraped", nullable=True)
    op.alter_column("scraper_runs", "pages_changed", nullable=True)
    op.alter_column("scraper_runs", "pages_errors", nullable=True)
