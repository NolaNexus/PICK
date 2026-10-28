"""Remove the duplicate foreign key on ``items.source_page_id``.

The initial migration declared the reference twice: once inline on the column
and once as a table-level constraint with ``ON DELETE SET NULL``. The database
therefore has two foreign keys on the same column, one of which nulls the
reference and one of which does not.

The behaviour of the two is the same unless a wiki page row is deleted, at
which point the stricter one refuses the delete and the looser one has
already nulled the reference. One constraint is the right number.

The surviving constraint is the one with ``ON DELETE SET NULL``: an item is a
fact about the game, not about the page it was first seen on, so deleting the
page row must not delete the item.
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def _foreign_keys(connection) -> list[tuple[str, str]]:
    """Return the name and definition of the foreign keys on the column."""
    rows = connection.execute(
        text(
            """
            SELECT c.conname, pg_get_constraintdef(c.oid)
            FROM pg_constraint AS c
            JOIN pg_attribute AS a
              ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
            WHERE c.conrelid = 'items'::regclass
              AND c.contype = 'f'
              AND a.attname = 'source_page_id'
            ORDER BY c.conname
            """
        )
    ).fetchall()
    return [(row[0], row[1]) for row in rows]


def upgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        return

    keys = _foreign_keys(connection)
    if len(keys) < 2:
        # There is only one constraint, or none. Nothing to remove.
        return

    # Keep the one that nulls the reference, drop the other.
    keep = next((name for name, definition in keys if "ON DELETE SET NULL" in definition), None)
    if keep is None:
        keep = keys[0][0]

    for name, _ in keys:
        if name != keep:
            op.execute(f'ALTER TABLE items DROP CONSTRAINT "{name}"')


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        return

    if len(_foreign_keys(connection)) > 1:
        # The duplicate is already back. Nothing to do.
        return

    # Put the plain foreign key back, without the ON DELETE clause.
    op.execute(
        """
        ALTER TABLE items
        ADD CONSTRAINT items_source_page_id_fkey1
        FOREIGN KEY (source_page_id) REFERENCES wiki_pages(id)
        """
    )
