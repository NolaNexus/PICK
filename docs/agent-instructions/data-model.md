# Data Model, Migrations and Typing

Covers `app/models/`, `app/services/reconcile.py`, `app/taxonomy.py` and `alembic/versions/`.

## Item identity

- `type_prefixed_slug()` in `app/services/reconcile.py` keeps an NPC and a quest with the
  same name distinct.
- `items.slug` is globally unique. The same game object on several wiki pages is stored
  once.
- Items removed from a page are soft-deleted (`is_active = false`), never deleted.

## Taxonomy

- The `taxonomy` table holds every type with its area, group, label, kind, display order
  and whether it is a fragment.
- `app/taxonomy.py` reads it through `load_taxonomy(db)`, an async loader. The exporter
  and the scraper both already have a session.
- `items.type` is a PostgreSQL enum over the same 33 values. A type that is not in the
  table cannot be written.

## Fragment types

Eight types are `is_fragment`: `museum_ore`, `blueprint`, `mutation_catalyst`,
`excavation_reward`, `museum_display`, `museum_info`, `merchant_item`, `consumable`.
Parsers emit them so reconciliation can fold them into another row. They are not
browsable.

- The `FOLDS` table in `app/services/reconcile.py` covers four of them: `museum_ore`,
  `blueprint`, `mutation_catalyst`, `excavation_reward`. Add a fold there rather than
  writing a bespoke merge.
- The other four have dedicated code: `_merge_museum_displays`, the merchant merge, and
  the consumable-to-relic reclassification.
- A fragment with nothing to fold into stays active. `mutation_catalyst` for
  "Frosthorn Pendant" is an example, and the client needs a label for it.

## Adding an item type

A type is added in five places, not one. Missing any of them fails a test.

1. Add the value to `ITEM_TYPE_VALUES` in `app/models/item.py`. That tuple, not the
   migration, is the source of truth: `tests/conftest.py` builds the test database's
   enum from it, and `tests/test_snapshot_contract.py` compares `snapshot.schema.json`
   against it.
2. Add the taxonomy row to `TAXONOMY_ROWS` in
   `alembic/versions/006_enforce_schema_invariants.py`. `006` creates the taxonomy table
   and bulk-inserts every row in one revision, and `tests/conftest.py` seeds the test
   taxonomy from the same module, so the row has to be in `006` for a fresh database and
   for the tests.
3. Add the type to the `itemType` list in `snapshot.schema.json`, in the same position as
   it appears in `ITEM_TYPE_VALUES`. The test compares the two lists element by element,
   so the order matters as much as the membership.
4. Add **two** new numbered revisions in `alembic/versions/`. Never edit an applied
   migration: `006` has already run in production, and editing it does not change a
   database that has run it.
   - The first revision runs `ALTER TYPE item_type ADD VALUE '<type>'`.
   - The second inserts the `taxonomy` row, with `ON CONFLICT (type) DO NOTHING`. The
     conflict guard is needed because `006` already inserted the row in step 2, so a
     fresh database has it twice.

   Two revisions are required because PostgreSQL refuses to use an enum value in the
   transaction that added it (`unsafe use of new value`). This also needs
   `transaction_per_migration=True` in `alembic/env.py`, which is set: Alembic's default
   is one transaction for the whole run, so without it both revisions share a transaction
   and the insert fails even though they are separate files. Keep that setting, and keep
   the two revisions, or `alembic upgrade head` — and with it `scripts/refresh_site.sh` —
   fails.
5. Regenerate the frontend types: `cd frontend && npm run generate:snapshot-types`. CI
   fails if the committed file does not match the schema.

A type that joins a group also has to be added to the group assertions in
`tests/test_taxonomy.py`, which list the expected members explicitly.

## Database constraints

`items` has three check constraints: `ck_items_name_not_empty`, `ck_items_data_object`
and `ck_items_slug_prefix`.

- The slug constraint is the important one. A slug is the type prefix, hyphenated (so
  `enchant_book` gives `enchant-book-…`), plus the name. That keeps slugs unique and
  deterministic whatever order pages were scraped in.
- `tests/test_schema_constraints.py` asserts the database rejects rows that break each one.
  A rule that exists only in Python fails no test, so put it in the database.
- `items.data` is JSONB with `jsonb_typeof(data) = 'object'`. That check is added by hand
  in `app/models/item.py`, because the JSON type function is named differently in
  PostgreSQL and SQLite.

## Models and parity

- `app/models/*.py` declare columns with `Mapped[T]` and `mapped_column()`, not `Column()`.
  That makes query results typed.
- `Item.type` is `Mapped[str]`, not an enum. The reconciler compares and assigns it as a
  string.
- `tests/test_schema_parity.py` compares the models' columns, nullability and defaults with
  the migrated database. Production runs the migrations; the tests use
  `Base.metadata.create_all`. A mismatch means tests can pass against a schema the site
  never runs on.

## Typecheck

- mypy is not in strict mode: `pyproject.toml` sets no `strict = true`, and
  `mypy --strict app/ scrapers/ scripts/` currently reports 42 errors across 16 files
  (mostly `type-arg`, `no-untyped-def` and `no-any-return`). Treat those as the backlog,
  not as a broken gate.
- The seven error codes `arg-type`, `assignment`, `attr-defined`, `call-arg`, `index`,
  `misc` and `var-annotated` are all **on**. They are on by default in mypy 2.4; the
  project's `pyproject.toml` used to list them under `disable_error_code` and that list
  was removed in `85b4553`. Do not re-add them, and do not disable them.
- To see what a code would catch: `mypy app/ scrapers/ scripts/ --enable-error-code=<code>`.
  Passing the flag on a code that is already on changes nothing; it is a way to inspect
  a single code, not to turn one on.

## Known lint drift

`ruff format --check` fails on `alembic/` (4 files would be reformatted). This is
pre-existing and outside CI's scope, which is `app scrapers scripts tests`. Do not fix it
inside an unrelated change. Tracked as issue #8.
