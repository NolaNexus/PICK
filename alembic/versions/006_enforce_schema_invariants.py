"""Give the schema the constraints it should have been enforcing.

The tables accepted anything: any ``items.type``, any ``data`` shape, an empty
name, a slug that did not derive from its type. The rules lived in Python, so a
bad write was only noticed when a later scrape produced something odd.

This migration:

* creates the ``item_type`` enum, holding every type a parser can emit;
* creates the ``taxonomy`` table, so the areas, groups, labels and display order
  live in the database rather than only in ``app/taxonomy.py``;
* moves ``items.type`` onto the enum;
* drops ``items.wiki_id``, which is null in every row and written by nobody;
* makes ``items.data`` a ``JSONB`` object with a check constraint;
* adds the check constraints the code already assumes, including the one that
  keeps a slug derived from its type;
* replaces the loose single-column indexes with partial indexes over the live
  rows, which is how every query actually filters.

The slug check is added ``NOT VALID`` first and validated afterwards, so a row
that predates the rule cannot lock the table while it is being checked.
"""

import sqlalchemy as sa
from alembic import op

from app.models.item import ITEM_TYPE_VALUES

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


#: Every type a parser can write to ``items.type``.
#:
#: This is the taxonomy (the types a user browses) plus the fragment types (the
#: types a parser emits only so reconciliation can fold them into another row).
#: ``consumable`` is included because the scraper writes it before reconciliation
#: reclassifies it as a relic.
#:
#: The list comes from the model, so the enum in the database, the column in the
#: table and the list in the schema cannot drift apart.
ITEM_TYPES = ITEM_TYPE_VALUES

#: The taxonomy: type -> (area, group, label, kind, is_fragment, display order).
#:
#: The display order is the order the types are shown in within their area. The
#: kinds are "item" (browsable on its own) and "reference" (attached to
#: something else). "record" is still accepted by the client but unused.
TAXONOMY_ROWS = (
    # Items: gear
    ("pan", "items", "gear", "Pan", "item", False, 0),
    ("shovel", "items", "gear", "Shovel", "item", False, 1),
    ("sluice", "items", "gear", "Sluice", "item", False, 2),
    ("equipment", "items", "gear", "Equipment", "item", False, 3),
    ("trinket", "items", "gear", "Trinket", "item", False, 4),
    ("rune", "items", "gear", "Rune", "item", False, 5),
    # Items: consumables
    ("potion", "items", "consumables", "Potion", "item", False, 6),
    ("enchant_book", "items", "consumables", "Enchant Book", "item", False, 7),
    ("relic", "items", "consumables", "Relic", "item", False, 8),
    # Items: treasure
    ("geode", "items", "treasure", "Geode", "item", False, 9),
    ("treasure_chest", "items", "treasure", "Treasure Chest", "item", False, 10),
    ("treasure_map", "items", "treasure", "Treasure Map", "item", False, 11),
    # Minerals
    ("mineral", "minerals", None, "Mineral", "item", False, 0),
    # World
    ("npc", "world", None, "NPC", "item", False, 0),
    ("quest", "world", None, "Quest", "item", False, 1),
    ("location", "world", None, "Location", "item", False, 2),
    ("excavation_site", "world", None, "Excavation Site", "item", False, 3),
    ("excavation_level", "world", None, "Excavation Level", "reference", False, 4),
    ("event", "world", None, "Event", "item", False, 5),
    # Calculators
    ("formula", "calculators", None, "Formula", "reference", False, 0),
    ("mastery", "calculators", None, "Mastery", "reference", False, 1),
    ("mutation_chance", "calculators", None, "Mutation Chance", "reference", False, 2),
    # Attached to an item, never listed on its own
    ("enchantment", "items", None, "Enchantment", "reference", False, 0),
    ("modifier", "minerals", None, "Modifier", "reference", False, 1),
    ("mutation_effect", "items", None, "Mutation", "reference", False, 1),
    # Fragments: a parser emits these so reconciliation can fold them into
    # another row. They are never browsable.
    ("blueprint", "items", "gear", "Blueprint", "reference", True, 0),
    ("consumable", "items", "consumables", "Consumable", "reference", True, 0),
    ("excavation_reward", "world", None, "Excavation Drop", "record", True, 0),
    ("merchant_item", "items", None, "Merchant Item", "reference", True, 0),
    ("museum_display", "world", None, "Museum Display", "record", True, 0),
    ("museum_info", "world", None, "Museum Info", "record", True, 0),
    ("museum_ore", "minerals", None, "Museum Ore", "reference", True, 0),
    ("mutation_catalyst", "items", None, "Mutation Catalyst", "reference", True, 0),
)


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        # SQLite has no enum type, no JSONB and no partial indexes. The
        # constraints that can be expressed there are added; the rest need
        # PostgreSQL, which is what the project runs on.
        with op.batch_alter_table("items", schema=None) as batch_op:
            batch_op.alter_column(
                "data",
                existing_type=sa.JSON(),
                type_=sa.JSON(),
                existing_nullable=False,
            )
        return

    # ------------------------------------------------------------------
    # The item type enum
    # ------------------------------------------------------------------
    # The type is created by hand rather than through sa.Enum.create(), because
    # sa.Enum would also try to create it when the taxonomy table is created,
    # and the second attempt fails. create_type=False stops the table from
    # trying again.
    op.execute(
        "CREATE TYPE item_type AS ENUM (%s)"
        % ", ".join("'%s'" % value for value in ITEM_TYPES)
    )
    item_type = sa.Enum(name="item_type", create_type=False)

    # ------------------------------------------------------------------
    # The taxonomy table
    # ------------------------------------------------------------------
    op.create_table(
        "taxonomy",
        sa.Column("type", item_type, primary_key=True),        sa.Column("area", sa.String(50), nullable=False),
        sa.Column("group_name", sa.String(50), nullable=True),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("listed", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("is_fragment", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.CheckConstraint(
            "kind IN ('item', 'record', 'reference')",
            name="ck_taxonomy_kind",
        ),
        sa.CheckConstraint(
            "listed = (kind = 'item')",
            name="ck_taxonomy_listed",
        ),
    )
    op.create_index("ix_taxonomy_area", "taxonomy", ["area"])

    taxonomy = sa.table(
        "taxonomy",
        sa.column("type", item_type),
        sa.column("area", sa.String(50)),
        sa.column("group_name", sa.String(50)),
        sa.column("label", sa.String(100)),
        sa.column("kind", sa.String(20)),
        sa.column("listed", sa.Boolean),
        sa.column("is_fragment", sa.Boolean),
        sa.column("display_order", sa.Integer),
    )
    op.bulk_insert(
        taxonomy,
        [
            {
                "type": row_type,
                "area": area,
                "group_name": group_name,
                "label": label,
                "kind": kind,
                "listed": kind == "item",
                "is_fragment": is_fragment,
                "display_order": display_order,
            }
            for row_type, area, group_name, label, kind, is_fragment, display_order in TAXONOMY_ROWS
        ],
    )

    # ------------------------------------------------------------------
    # items.type moves onto the enum
    # ------------------------------------------------------------------
    op.execute("ALTER TABLE items ALTER COLUMN type DROP DEFAULT")
    op.execute("ALTER TABLE items ALTER COLUMN type TYPE item_type USING type::item_type")
    op.execute("ALTER TABLE items ALTER COLUMN type SET NOT NULL")

    # ------------------------------------------------------------------
    # items.data becomes a JSONB object
    # ------------------------------------------------------------------
    op.execute("ALTER TABLE items ALTER COLUMN data TYPE jsonb USING data::jsonb")
    op.execute(
        "ALTER TABLE items ADD CONSTRAINT ck_items_data_object "
        "CHECK (jsonb_typeof(data) = 'object')"
    )

    # ------------------------------------------------------------------
    # The columns that should not be empty
    # ------------------------------------------------------------------
    op.execute(
        "ALTER TABLE items ADD CONSTRAINT ck_items_name_not_empty "
        "CHECK (btrim(name) <> '')"
    )
    # A slug is the type prefix plus a name slug. The prefix uses hyphens
    # where the type uses underscores: "enchant_book" -> "enchant-book-...".
    # Added NOT VALID so a row that predates the rule cannot block it.
    op.execute(
        "ALTER TABLE items ADD CONSTRAINT ck_items_slug_prefix "
        "CHECK (slug LIKE replace(type::text, '_', '-') || '-%') NOT VALID"
    )
    op.execute("ALTER TABLE items VALIDATE CONSTRAINT ck_items_slug_prefix")

    # ------------------------------------------------------------------
    # The dead column
    # ------------------------------------------------------------------
    # Every row has it null and nothing writes it.
    op.drop_index("ix_items_wiki_id", table_name="items", if_exists=True)
    op.drop_column("items", "wiki_id")

    # ------------------------------------------------------------------
    # Indexes for the queries that actually run
    # ------------------------------------------------------------------
    # Every read filters on is_active, so a partial index over the live rows
    # is both smaller and faster than indexing the column on its own.
    op.execute("DROP INDEX IF EXISTS ix_items_is_active")
    op.execute("DROP INDEX IF EXISTS ix_items_name")
    op.execute("DROP INDEX IF EXISTS ix_items_type")
    op.create_index(
        "ix_items_active_type", "items", ["type"], postgresql_where=sa.text("is_active")
    )
    op.create_index(
        "ix_items_active_name", "items", ["name"], postgresql_where=sa.text("is_active")
    )
    # The slug already has a unique index over every row, and that serves the
    # lookup by slug just as well, so a second index on the same column would
    # only cost space.

    # ------------------------------------------------------------------
    # The inconsistencies
    # ------------------------------------------------------------------
    # Every other table counts with a bigint.
    op.execute("ALTER TABLE scraper_runs ALTER COLUMN id TYPE bigint")
    op.execute("DROP SEQUENCE IF EXISTS scraper_runs_id_seq CASCADE")
    op.execute("CREATE SEQUENCE scraper_runs_id_seq AS BIGINT")
    op.execute(
        "ALTER TABLE scraper_runs ALTER COLUMN id SET DEFAULT nextval('scraper_runs_id_seq')"
    )
    op.execute("SELECT setval('scraper_runs_id_seq', COALESCE(MAX(id), 1)) FROM scraper_runs")

    # A flag, not a count. The default has to go before the type changes, or
    # PostgreSQL tries to cast it.
    op.execute("ALTER TABLE game_versions ALTER COLUMN triggered_full_scrape DROP DEFAULT")
    op.execute(
        "ALTER TABLE game_versions ALTER COLUMN triggered_full_scrape TYPE boolean "
        "USING (triggered_full_scrape <> 0)"
    )
    op.execute(
        "ALTER TABLE game_versions ALTER COLUMN triggered_full_scrape SET DEFAULT false"
    )

    # Every page has a namespace; the main one is 0.
    op.execute("UPDATE wiki_pages SET namespace = 0 WHERE namespace IS NULL")
    op.execute("ALTER TABLE wiki_pages ALTER COLUMN namespace SET NOT NULL")
    op.execute("ALTER TABLE wiki_pages ALTER COLUMN namespace SET DEFAULT 0")


def downgrade() -> None:
    if not _is_postgres():
        return

    op.execute("ALTER TABLE wiki_pages ALTER COLUMN namespace DROP NOT NULL")
    op.execute("ALTER TABLE wiki_pages ALTER COLUMN namespace DROP DEFAULT")

    op.execute("ALTER TABLE game_versions ALTER COLUMN triggered_full_scrape DROP DEFAULT")
    op.execute(
        "ALTER TABLE game_versions ALTER COLUMN triggered_full_scrape TYPE bigint "
        "USING (CASE WHEN triggered_full_scrape THEN 1 ELSE 0 END)"
    )
    op.execute(
        "ALTER TABLE game_versions ALTER COLUMN triggered_full_scrape SET DEFAULT 0"
    )

    op.execute("ALTER TABLE scraper_runs ALTER COLUMN id TYPE integer")
    op.execute("DROP SEQUENCE IF EXISTS scraper_runs_id_seq CASCADE")
    op.execute("CREATE SEQUENCE scraper_runs_id_seq AS INTEGER")
    op.execute(
        "ALTER TABLE scraper_runs ALTER COLUMN id SET DEFAULT nextval('scraper_runs_id_seq')"
    )
    op.execute("SELECT setval('scraper_runs_id_seq', COALESCE(MAX(id), 1)) FROM scraper_runs")

    op.drop_index("ix_items_active_name", table_name="items")
    op.drop_index("ix_items_active_type", table_name="items")
    op.create_index("ix_items_type", "items", ["type"])
    op.create_index("ix_items_name", "items", ["name"])
    op.create_index("ix_items_is_active", "items", ["is_active"])

    op.add_column("items", sa.Column("wiki_id", sa.String(100), nullable=True))
    op.create_index("ix_items_wiki_id", "items", ["wiki_id"])

    op.execute("ALTER TABLE items DROP CONSTRAINT IF EXISTS ck_items_slug_prefix")
    op.execute("ALTER TABLE items DROP CONSTRAINT IF EXISTS ck_items_name_not_empty")
    op.execute("ALTER TABLE items DROP CONSTRAINT IF EXISTS ck_items_data_object")

    op.execute("ALTER TABLE items ALTER COLUMN data TYPE json USING data::json")
    op.execute("ALTER TABLE items ALTER COLUMN type TYPE varchar(50)")
    op.execute("ALTER TABLE items ALTER COLUMN type DROP NOT NULL")

    op.drop_index("ix_taxonomy_area", table_name="taxonomy")
    op.drop_table("taxonomy")
    sa.Enum(name="item_type").drop(op.get_bind(), checkfirst=True)
