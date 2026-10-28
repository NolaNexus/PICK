# AGENTS.md

PICK scrapes the Prospecting! wiki into PostgreSQL and exports a committed
`frontend/public/snapshot.json`, which a static React + Vite site reads. The site never
calls the backend. Verify anything here against `pyproject.toml`, `.github/workflows/ci.yml`
and the code.

## Run commands

- **Backend tools**: Always invoke via `.venv/bin/python -m <tool>` (e.g., `.venv/bin/python -m ruff check app scrapers scripts tests`, `.venv/bin/python -m mypy app/ scrapers/ scripts/`, `.venv/bin/python -m alembic upgrade head`). Never use `.venv/bin/<tool>` because shebangs break when `.venv` moves.
- **Frontend tools**: Run from `frontend/`: `npm run typecheck`, `npm run test`, `npm run lint`, `npm run build`. `npm run format` on `src/` would bury real changes in `calculators.ts`/`museum.ts` because they use tabs (see §Indentation).
- **Full refresh cycle**: `./scripts/refresh_site.sh [--dry-run]`. Does: start DB (`docker compose up -d db` if container doesn't exist), migrate (`alembic upgrade head`), scrape (`--full` if game version detected), seed formulas, export snapshot (`frontend/public/snapshot.json` only if changed), commit only the snapshot. Fails if:
  - checkout has uncommitted changes (commit/stash first),
  - anything other than `snapshot.json` is staged (fails at `git commit`).
  - snapshot would lose >20% items (refuses write unless `--force`).
  `--dry-run` exercises the cycle without writing/committing.
- **Generate frontend types**: `cd frontend && npm run generate:snapshot-types`. Never hand-edit `frontend/src/lib/snapshot.types.ts`; it is generated from `snapshot.schema.json`. CI fails if it differs.

## Database

- **Local dev**: `docker compose up -d db` starts Postgres 16 at `localhost:5432` (user `pick`, password `pick`, DB `pick`). Always start the container first if you haven't yet.
- **Migrations**: `alembic/versions/`. Run with `.venv/bin/python -m alembic upgrade head`. Never edit an applied migration.
- **Test database**: Use `docker compose up -d db` then `docker exec pick-db psql -U pick -d pick -c "CREATE DATABASE pick_test;"` to create `pick_test`. Set `TEST_DATABASE_URL=postgresql+asyncpg://pick:pick@localhost:5432/pick_test` for tests. CI creates `pick_test` automatically. Pure-logic tests (e.g., `test_export_guard.py`) need no DB; integration tests need `TEST_DATABASE_URL` and the DB container.

## Scraper logic

- `run_daily_scrape` checks `Changelog` for a new game version (heading `== Month Year ==`). If found, triggers `run_full_scrape` automatically.
- `pages_ok` counts only pages that actually reached the wiki (have a parser). A scrape with `pages_ok == 0` fails and nothing is published. `pages_scraped` counts all pages attempted (including no-parser pages).
- `PARSER_VERSION` in `scrapers/registry.py` must be incremented when parsers or `scrapers/wikitext.py` changes; otherwise stored data keeps the old parser shape.

## Snapshot export

- `scripts/export_snapshot` writes `frontend/public/snapshot.json` only if the snapshot differs from the last export (compared after stripping volatile keys).
- Volatile keys stripped: `generated_at`, `last_scrape`, all `created_at`/`updated_at` on items, `last_seen` on merchants. Adding a volatile field requires updating `_strip_volatile` in `export_snapshot.py`.
- Snapshot comparison sorts rows by `slug` (items), `formula_id` (formulas), `title` (wiki pages) via `_comparable`. Without `ORDER BY` in `build_snapshot`, row order may vary between runs, causing unnecessary diffs.
- Refuses to overwrite if it would lose >20% items (checked by `_refusal_reason`). Use `--force` only for real drops (e.g., game update removing items).

## Frontend

- `frontend/src/lib/calculators.ts` and `frontend/src/lib/museum.ts` use tabs; everything else under `src/` uses 2 spaces. Match the file you edit; do not run `npm run format` across `src/`.
- `Item.type` is the `ItemType` union; `Item.data` is non-nullable; there is no `wiki_id`. Import from `@/lib/snapshot.types` or `@/lib/snapshot`.
- Calculator result types are hand-written: `calculators.ts` exports `EVOutput`, `TTGOutput`, `ModifierOddsOutput`, `BestPanOutput` (camelCase) and `*Inputs` types; `museum.ts` exports `MuseumComparatorOutput`, `MuseumOptimizerOutput`, `UnlockCostsOutput`. They are not in a generated file.
- `calculateEV` is a placeholder: uses `base_price` as drop chance, ignores `luck` and `quality`. Real drop chances live at `data.chances[]` (`chance_percent`, `one_in`). Tracked as issue #6.
- There is no `src/api/` directory and no API client. Do not recreate one. The ESLint config lists it in `ignorePatterns`; that is a leftover.
- Vite `base` is `/PICK/`. `404.html` is a hand-written SPA fallback for deep links.

## Adding an item type

A type is added in five places (missing any fails a test):

1. `ITEM_TYPE_VALUES` in `app/models/item.py`.
2. `TAXONOMY_ROWS` in `alembic/versions/006_enforce_schema_invariants.py` (creates taxonomy table and seeds it; `tests/conftest.py` seeds from it).
3. `itemType` list in `snapshot.schema.json` (same order as `ITEM_TYPE_VALUES`).
4. Two new numbered revisions in `alembic/versions/`: first `ALTER TYPE item_type ADD VALUE`, second inserts the taxonomy row with `ON CONFLICT (type) DO NOTHING`. Two revisions required because PostgreSQL refuses to use an enum value in the transaction that added it (`unsafe use of new value`). Requires `transaction_per_migration=True` in `alembic/env.py`.
5. Regenerate: `cd frontend && npm run generate:snapshot-types`.

Also add to group assertions in `tests/test_taxonomy.py`.

## Known issues (tracked)

- `calculateEV` uses `base_price` as drop chance (issue #6).
- Museum calculator returns empty results (issue #1).
- `ruff format --check` fails on `alembic/` (4 files) — outside CI scope (issue #8).
- `src/lib/calculators.ts` and `src/lib/museum.ts` use tabs (issue #7).
- `mypy --strict` reports 42 errors (issue #13).
- 106 items carry raw wiki markup; 455 of 853 have no `image_url` (issues #9, #10).
- `Codes`, `Changelog`, `Guides` have no parser (issue #11).

## Where things live

- `app/` — models, services, MediaWiki client.
- `scrapers/` — wiki wikitext parsers; `scrapers/registry.py` holds `TRACKED_PAGES`, `PARSERS`, `PARSER_VERSION`.
- `scripts/` — CLI entry points (`scraper.py`, `export_snapshot.py`, `refresh_site.sh`, `seed_formulas.py`).
- `frontend/` — static site; `frontend/public/snapshot.json` is the dataset and is committed.
- `docs/agent-instructions/` — per-area guidance. Read the matching file before changing its area.
- `.kilo/plans/` — git-ignored scratch space. Never read one as a description of the current tree.

## Detailed guidance

Read the linked file before changing its area (not loaded automatically).

| Working on | Read |
| --- | --- |
| Scraper, parsers, `PARSER_VERSION` | [scraper.md](docs/agent-instructions/scraper.md) |
| Models, migrations, item types, taxonomy, typecheck | [data-model.md](docs/agent-instructions/data-model.md) |
| Snapshot, exporter, refresh cycle, contract | [snapshot-and-publishing.md](docs/agent-instructions/snapshot-and-publishing.md) |
| Vite app, calculators, generated types | [frontend.md](docs/agent-instructions/frontend.md) |
| Running or writing tests | [testing.md](docs/agent-instructions/testing.md) |
| Virtualenv, Postgres, `.env`, systemd | [environment.md](docs/agent-instructions/environment.md) |
| Commits, issues, docs, slash commands | [git-and-issues.md](docs/agent-instructions/git-and-issues.md) |

## Rules for every task

- **No HTTP API.** Do not add a server for data the site already has as a file.
- **`master` is the deploy branch.** Pushing it triggers CI and the Pages deploy.
- **Never hand-edit `frontend/src/lib/snapshot.types.ts`.** It is generated; CI fails if stale.
- **The wiki is reachable only from the local machine.** Miraheze returns 403 to GitHub runners. No scrape workflows in CI; no test may depend on the wiki.
- **Target Python 3.11.** Local `.venv` is 3.14; CI runs 3.11 and 3.12. No 3.12+ syntax.
- **`.venv` hard-codes its absolute path.** If the checkout moves, delete `.venv` and recreate it (`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt`). Shebangs in `.venv/bin` break.
- **`.env` is dotenv, not shell.** `scripts/refresh_site.sh` parses it line by line; do not `source .env`. `app/config.py` reads it via `pydantic-settings`; an env var already set wins over the file.
- **Virtualenv tools**: Invoke as `.venv/bin/python -m <tool>`, not `.venv/bin/<tool>`.
- **Tests need `TEST_DATABASE_URL`**: `conftest.py` refuses any URL whose database name does not end in `_test`. Set up a test DB once with `docker compose up -d db` then `docker exec pick-db psql -U pick -d pick -c "CREATE DATABASE pick_test;"`.
- **Never run two pytest sessions against the same test database** — the `test_engine` fixture drops every table on teardown.
- **Pure-logic tests need no DB**: `tests/test_export_snapshot.py`, `tests/test_export_guard.py`. Run one test with `.venv/bin/python -m pytest tests/test_export_guard.py::test_refuses_an_empty_snapshot_over_a_full_one`.
- **Wiki tests**: `tests/test_scrape_resilience.py` reads `tests/fixtures/*.wiki` instead of hitting the wiki. Keep that property. Verify with `MEDIAWIKI_API_URL="http://invalid.invalid/api.php" .venv/bin/python -m pytest -q` (with `TEST_DATABASE_URL` and `DATABASE_URL` set).
- **Frontend tests**: vitest in node environment; `describe`, `it`, `expect` imported from `vitest` explicitly; DOM tests opt in via `// @vitest-environment jsdom` docblock. `jsdom` is not installed yet.
- **`ruff format` fails on `alembic/`** (4 files) — pre-existing, outside CI scope. Do not fix inside an unrelated change.
- **Mypy is not in strict mode**: `mypy --strict app/ scrapers/ scripts/` reports 42 errors. The seven error codes `arg-type`, `assignment`, `attr-defined`, `call-arg`, `index`, `misc`, `var-annotated` are on by default. Do not re-add `disable_error_code` list.
- **`SNAPSHOT_SCHEMA_VERSION` is declared twice**: in `app/services/snapshot.py` and `frontend/src/lib/snapshot.ts`. `tests/test_snapshot_contract.py` fails if they drift. Bump both when payload shape changes.
- **`build_snapshot()` gives every query an explicit `ORDER BY`**. Any new query needs one. `_comparable()` also sorts rows before comparing.
- **Soft-delete, never hard-delete**: Items removed from a page get `is_active = false`.
- **Slugs are namespaced by type**: `type_prefixed_slug()` in `app/services/reconcile.py` keeps same-name items across types distinct.
- **Fragment types**: Eight types are `is_fragment`: `museum_ore`, `blueprint`, `mutation_catalyst`, `excavation_reward`, `museum_display`, `museum_info`, `merchant_item`, `consumable`. Parsers emit them for reconciliation. `FOLDS` table in `reconcile.py` covers four; the rest have dedicated code.
- **Slugs are globally unique**: `items.slug` is unique. Same game object on several wiki pages is stored once.
- **No `src/api/` directory**: Do not recreate one. ESLint config lists it in `ignorePatterns`; harmless leftover.
- **`npm ci` works without `--legacy-peer-deps`**: Lockfile resolves cleanly against React 19 peer ranges. CI does not pass it. `--legacy-peer-deps` is harmless but no longer needed.
- **Vite resolves tsconfig `paths` natively** (`resolve.tsconfigPaths`), so `@/` alias needs no plugin. `vite-tsconfig-paths` was removed.
- **`frontend/public/404.html` is a hand-written SPA fallback** for deep links. GitHub Pages has no rewrite rules.
- **`scripts/refresh_site.sh` refuses to run on a dirty tree** (checks `git status --porcelain`). Keep checkout clean. A stray edit makes the pull fail with a message that reads like a network problem, or gets left behind by the commit.
- **`scripts/refresh_site.sh` commits only the snapshot**. It ends in `git push origin HEAD:master`, which redeploys the site.
- **`scripts/refresh_site.sh` parses `.env` line by line** rather than sourcing it.
- **`docker compose up -d db` starts Postgres 16** on `localhost:5432` with user `pick`, password `pick`, DB `pick`. The scraper and exporter both need `DATABASE_URL` pointing at it.
- **`alembic/env.py` sets `transaction_per_migration=True`**, so each revision gets its own transaction. That lets one revision add an enum value and a later one use it. Keep this setting.
- **`tests/conftest.py` builds the test database's enum from `ITEM_TYPE_VALUES`** in `app/models/item.py`, and `tests/test_snapshot_contract.py` compares `snapshot.schema.json` against it.
- **`tests/test_schema_parity.py` compares models' columns, nullability, defaults with the migrated database.** Production runs migrations; tests use `Base.metadata.create_all`. A mismatch means tests can pass against a schema the site never runs on.
- **`tests/test_schema_constraints.py` asserts the database rejects rows that break constraints.** A rule that exists only in Python fails no test, so put it in the database.
- **`items` has three check constraints**: `ck_items_name_not_empty`, `ck_items_data_object`, `ck_items_slug_prefix`. The slug constraint is important: a slug is the type prefix, hyphenated, plus the name.
- **`items.data` is JSONB** with `jsonb_typeof(data) = 'object'`. That check is added by hand in `app/models/item.py`.
- **`app/models/*.py` declare columns with `Mapped[T]` and `mapped_column()`, not `Column()`**. That makes query results typed.
- **`Item.type` is `Mapped[str]`, not an enum.** The reconciler compares and assigns it as a string.
- **`app/taxonomy.py` reads it through `load_taxonomy(db)`**, an async loader. The exporter and scraper both already have a session.
- **`items.type` is a PostgreSQL enum** over the same 33 values. A type not in the table cannot be written.
- **`taxonomy` table holds every type** with its area, group, label, kind, display order and whether it is a fragment.
- **Soft-delete**: Items removed from a page are soft-deleted (`is_active = false`), never deleted.
- **`type_prefixed_slug()` in `app/services/reconcile.py`** keeps an NPC and a quest with the same name distinct.
- **`items.slug` is globally unique.** The same game object on several wiki pages is stored once.
- **A fragment with nothing to fold into stays active.** `mutation_catalyst` for "Frosthorn Pendant" is an example, and the client needs a label for it.
- **`FOLDS` table in `app/services/reconcile.py` covers four fragment types**: `museum_ore`, `blueprint`, `mutation_catalyst`, `excavation_reward`. Add a fold there rather than writing a bespoke merge.
- **The other four fragment types have dedicated code**: `_merge_museum_displays`, the merchant merge, and the consumable-to-relic reclassification.
- **`scrapers/registry.py`**: `TRACKED_PAGES` and `PARSERS` are separate. A page can be tracked with `PARSERS[page] = None` (currently `Codes`, `Changelog`, `Guides`). It is counted but never fetched. When adding a page, add its parser too.
- **Parsers return `ParsedItem`** (`scrapers/types.py`). It requires `id`, `type`, `name`, `slug`, `data`, `image_url`. `description` is `NotRequired` because some parsers put it inside `data`. A parser that builds a different shape gets its own TypedDict. Do not loosen `ParsedItem`.
- **A page is re-parsed only when its wikitext or `PARSER_VERSION` changes.** Bump `PARSER_VERSION` when a parser, or the shared renderer `scrapers/wikitext.py`, changes shape. Adding a parser also means bumping it. Otherwise stored data keeps the old shape.
- **`pages_scraped` is not "pages fetched".** It counts the titles that did not raise, and that includes pages with no parser, which are never fetched. When every fetch fails, `pages_scraped` is the number of no-parser pages (currently 3), not 0, so a guard on it never fires. `pages_ok` means "the run actually reached a page". `scripts/scraper.py` guards on `pages_ok == 0`. Do not swap them.
- **`SNAPSHOT_SCHEMA_VERSION` is declared twice**: in `app/services/snapshot.py` and in `frontend/src/lib/snapshot.ts`. `tests/test_snapshot_contract.py` fails if they drift. Bump both when the payload shape changes.
- **`build_snapshot()` in `app/services/snapshot.py` gives every query an explicit `ORDER BY`**. Without one, PostgreSQL returns rows in plan order. The same items then come back in a different order each run, the file differs every time, and the refresh job commits it daily for no reason. Any new query in `build_snapshot()` needs an `ORDER BY`. `_comparable()` also sorts rows before comparing them.
- **`_comparable()` in `scripts/export_snapshot.py` serialises the whole snapshot and strips an explicit list of volatile keys**: scrape timestamps, `data.merchant.last_seen`, and the `last_scrape` counters. Everything else is compared, including the taxonomy. It is an exclusion list on purpose. The old inclusion list missed the taxonomy, so a taxonomy change never published. The current list fails loud instead: an unnecessary commit, not a stale site. A field that changes on every run goes in the volatile list. Do not stop comparing it.
- **`scripts/refresh_site.sh` runs the whole cycle**: start DB, migrate, scrape, seed, export, commit, push. It publishes from this checkout. It is fail-closed. The scraper exits non-zero if it reached no page. The exporter refuses to write a snapshot that would erase the catalogue. `--dry-run` exercises the cycle without writing or publishing anything. It refuses to run on a dirty tree (it checks `git status --porcelain` before pulling). Keep the checkout clean. A stray edit makes the pull fail with a message that reads like a network problem, or gets left behind by the commit. It commits only the snapshot. It ends in `git push origin HEAD:master`, which redeploys the site. It parses `.env` line by line rather than sourcing it.
- **The `generated-files` job in `.github/workflows/ci.yml` regenerates the snapshot types and fails if they differ from the committed file.** A generated file left stale by a change is a failed build. Regenerating with unchanged input produces no diff; check that before committing.
- **`frontend/src/lib/snapshot.types.ts` is generated from `snapshot.schema.json` by `npm run generate:snapshot-types`.** Never hand-edit it. Everything else under `src/` is hand-written.
- **The item type is the generated `Item`.** Import it from `@/lib/snapshot.types` or `@/lib/snapshot`. `Item.type` is the `ItemType` union, `Item.data` is non-nullable, and there is no `wiki_id`.
- **Calculator result types are hand-written** and live in the modules that compute them. `calculators.ts` exports `EVOutput`, `TTGOutput`, `ModifierOddsOutput` and `BestPanOutput` (camelCase), plus their `*Inputs` types. `museum.ts` exports `MuseumComparatorOutput`, `MuseumOptimizerOutput` and `UnlockCostsOutput`. They are not in a generated file.
- **There is no `src/api/` directory and no API client.** Do not recreate one. The ESLint config still lists `src/api` in `ignorePatterns`; that is a leftover and is harmless.
- **`npm ci` and `npm install` work without `--legacy-peer-deps`.** The lockfile resolves cleanly against the React 19 peer ranges. `--legacy-peer-deps` is harmless but is no longer needed, and CI does not pass it.
- **The Vite `base` is `/PICK/`**, matching the GitHub Pages repo path.
- **Vite 8 resolves the tsconfig `paths` aliases natively** (`resolve.tsconfigPaths`), so the `@/` alias needs no plugin. `vite-tsconfig-paths` was removed.
- **`frontend/public/404.html` is a hand-written SPA fallback for deep links.** GitHub Pages has no rewrite rules.
- **Gates**: `npm run typecheck`, `npm run test`, `npm run lint`, `npm run build`.
- **`npm run lint` runs ESLint.** There is no oxlint in this project, and no `frontend/README.md` — the stock Vite template README that described one is gone.
- **`src/lib/calculators.ts` and `src/lib/museum.ts` are the only implementation.** They run in the browser. `calculators.ts` uses `decimal.js` for precision.
- **There is no oracle.** The Python implementation they came from is gone, so the tests pin current behaviour, not a known-good result.
- **`calculateEV` is a documented placeholder.** It uses `base_price` as a proxy for the drop chance and ignores `luck` and `quality`. Its test is marked `TODO`. Tracked as issue #6. The snapshot holds real drop chances at `data.chances[]` (`chance_percent`, `one_in`).
- **Museum calculator bugs are tracked as issue #1.**
- **`src/lib/calculators.ts` and `src/lib/museum.ts` use tabs.** Everything else under `src/` uses two spaces. `.prettierrc` says `tabWidth: 2`, but CI never runs `prettier --check`. Match the file you are editing. Do not run `npm run format` across `src/`: it rewrites those two files and buries real changes in whitespace. Tracked as issue #7. Each `*.test.ts` sits next to the module it tests.
- **`npm run test` runs vitest.** Config: `frontend/vitest.config.ts`. It runs in the **node** environment. The modules under test (`calculators.ts`, `museum.ts`, `taxonomy.ts`, `snapshot.ts`) are pure. Only `lib/idb.ts` touches `indexedDB`, and it is not under test. Import `describe`, `it` and `expect` from `vitest` explicitly. Do not rely on globals. This needs no tsconfig change and keeps ESLint's `no-undef` quiet. A test that needs the DOM opts in with a `// @vitest-environment jsdom` docblock. `jsdom` is not installed yet.
- **`conftest.py` refuses any URL whose database name does not end in `_test`**, and raises `UnsafeTestDatabaseError` when `TEST_DATABASE_URL` is unset. This is deliberate: a run must never drop a real database. Without `TEST_DATABASE_URL` these files error, because they need a database: `test_integration`, `test_merges`, `test_schema_constraints`, `test_schema_parity`, `test_scrape_resilience`, `test_snapshot_order`, `test_taxonomy`. Set up a test database once with `docker compose up -d db` then `docker exec pick-db psql -U pick -d pick -c "CREATE DATABASE pick_test;"`. Run the suite with `TEST_DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick_test" DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick" .venv/bin/python -m pytest -q`. Never run two pytest sessions against the same test database at once. The `test_engine` fixture drops every table on teardown, so parallel runs tear each other down mid-run and fail in ways that look like real bugs. Run them one after another, or give each its own `_test` database. Pure-logic tests need no database, for example `tests/test_export_snapshot.py` and `tests/test_export_guard.py`. Run one test with `.venv/bin/python -m pytest tests/test_export_guard.py::test_refuses_an_empty_snapshot_over_a_full_one`. GitHub runners get `403 Forbidden` from Miraheze for every request. So `tests/test_scrape_resilience.py` reads `tests/fixtures/*.wiki` instead. Keep that property. The suite must pass with an unreachable wiki, and the live-wiki tests skip via `requires_wiki`. Verify with `TEST_DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick_test" DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick" MEDIAWIKI_API_URL="http://invalid.invalid/api.php" .venv/bin/python -m pytest -q`.
- **`.venv` hard-codes its own absolute path.** Renaming or moving the checkout breaks every script in `.venv/bin`. If paths look wrong, delete `.venv` and recreate it: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt`. Invoke tools as `.venv/bin/python -m <tool>`, not `.venv/bin/<tool>`. The shebangs in `.venv/bin` are what break. `requirements.txt` holds the runtime dependencies and `requirements-dev.txt` the test and lint tools. `pyproject.toml` reads its dependency list from `requirements.txt`, so there is one list. The local `.venv` is Python 3.14. CI runs 3.11 and 3.12. `pyproject.toml` pins `target-version = "py311"` and `python_version = "3.11"`. `deploy/systemd/*.service` hard-code the checkout path. Update them alongside any move.
- **`scripts/refresh_site.sh` parses `.env` line by line** rather than sourcing it. Values such as `USER_AGENT=PICK/1.0 (Prospecting Information & Community Kit)` contain spaces and parentheses. Do not `source .env` in a shell. `app/config.py` reads the same file through `pydantic-settings` (`env_file=".env"`). A value already set in the environment wins over the file.
- **The scrape runs locally from a systemd timer.** The unit files are in `deploy/systemd/`, and the install steps and deploy-key setup are in `SETUP.md`.
- **`ruff format --check` fails on `alembic/`** (4 files). Outside CI's scope. Issue #8.
- **mypy is not in strict mode.** The seven type-error codes are on and the gate is green, but `mypy --strict` reports 42 errors. Do not claim the typecheck is strict. Issue #13.
- **106 items in the committed snapshot carry raw wiki markup in `data`, and 455 of 853 have no `image_url`.** Both pass the schema contract. Issue #9, issue #10. See [snapshot-and-publishing.md](docs/agent-instructions/snapshot-and-publishing.md).
- **`Codes`, `Changelog` and `Guides` are tracked with no parser, so they are never fetched.** Issue #11.
- **`.kilo/plans/` is git-ignored scratch space.** A plan is written when work starts and deleted when it lands. Never read one as a description of the current tree.
- **`master` is the deploy branch.** Pushing it triggers CI and the Pages deploy.
- **No HTTP API.** Do not add a server for data the site already has as a file. The dataset is `snapshot.json`, described by `snapshot.schema.json`.
- **Never hand-edit `frontend/src/lib/snapshot.types.ts`.** It is generated; CI fails if it is stale. Regenerate with `cd frontend && npm run generate:snapshot-types`.
- **The wiki is reachable only from the local machine.** Miraheze returns 403 to GitHub runners. Add no scrape workflows to CI, and no test may depend on the wiki.
- **Target Python 3.11.** Local `.venv` is 3.14; CI runs 3.11 and 3.12. No 3.12+ syntax.
- **`docs/agent-instructions/` holds per-area guidance.** `SETUP.md` is the operational guide.
- **`app/` models, services and the MediaWiki client.** `scrapers/` parses wiki wikitext into items. `scripts/` holds the CLI entry points. `frontend/` is the published site. `frontend/public/snapshot.json` is the dataset and it is committed. `.kilo/plans/` is git-ignored scratch space.
- **`scripts/refresh_site.sh` fails-closed**: scraper exits non-zero if it reached no page; exporter refuses to write a snapshot that would erase the catalogue.
- **`scripts/refresh_site.sh` refuses to run on a dirty tree** (checks `git status --porcelain` before pulling). Keep checkout clean.
- **`scripts/refresh_site.sh` commits only the snapshot.** It ends in `git push origin HEAD:master`, which redeploys the site.
- **`scripts/refresh_site.sh` parses `.env` line by line** rather than sourcing it.
- **`docker compose up -d db` starts Postgres 16** on `localhost:5432` with user `pick`, password `pick` and database `pick`. The scraper and the exporter both need `DATABASE_URL` pointing at it.
- **Migrations live in `alembic/versions/`.** Run them with `.venv/bin/python -m alembic upgrade head`. `alembic/env.py` sets `transaction_per_migration=True`, so each revision gets its own transaction. That is what lets one revision add an enum value and a later one use it; see [data-model.md](data-model.md). For schema changes, see [data-model.md](data-model.md).
- **`.env` is dotenv, not shell.** `scripts/refresh_site.sh` parses `.env` line by line rather than sourcing it. Values such as `USER_AGENT=PICK/1.0 (Prospecting Information & Community Kit)` contain spaces and parentheses. Do not `source .env` in a shell. `app/config.py` reads the same file through `pydantic-settings` (`env_file=".env"`). A value already set in the environment wins over the file.
- **The scrape runs locally from a systemd timer.** The unit files are in `deploy/systemd/`, and the install steps and deploy-key setup are in `SETUP.md`.
- **The `generated-files` job in `.github/workflows/ci.yml` regenerates the snapshot types and fails if they differ from the committed file.** A generated file left stale by a change is a failed build. Regenerating with unchanged input produces no diff; check that before committing.
- **`frontend/src/lib/snapshot.types.ts` is generated from `snapshot.schema.json` by `npm run generate:snapshot-types`.** Never hand-edit it. Everything else under `src/` is hand-written.
- **The item type is the generated `Item`.** Import it from `@/lib/snapshot.types` or `@/lib/snapshot`. `Item.type` is the `ItemType` union, `Item.data` is non-nullable, and there is no `wiki_id`.
- **Calculator result types are hand-written** and live in the modules that compute them. `calculators.ts` exports `EVOutput`, `TTGOutput`, `ModifierOddsOutput` and `BestPanOutput` (camelCase), plus their `*Inputs` types. `museum.ts` exports `MuseumComparatorOutput`, `MuseumOptimizerOutput` and `UnlockCostsOutput`. They are not in a generated file.
- **There is no `src/api/` directory and no API client.** Do not recreate one. The ESLint config still lists `src/api` in `ignorePatterns`; that is a leftover and is harmless.
- **`npm ci` and `npm install` work without `--legacy-peer-deps`.** The lockfile resolves cleanly against the React 19 peer ranges. `--legacy-peer-deps` is harmless but is no longer needed, and CI does not pass it.
- **The Vite `base` is `/PICK/`**, matching the GitHub Pages repo path.
- **Vite 8 resolves the tsconfig `paths` aliases natively** (`resolve.tsconfigPaths`), so the `@/` alias needs no plugin. `vite-tsconfig-paths` was removed.
- **`frontend/public/404.html` is a hand-written SPA fallback for deep links.** GitHub Pages has no rewrite rules.
- **Gates**: `npm run typecheck`, `npm run test`, `npm run lint`, `npm run build`.
- **`npm run lint` runs ESLint.** There is no oxlint in this project, and no `frontend/README.md` — the stock Vite template README that described one is gone.
- **`src/lib/calculators.ts` and `src/lib/museum.ts` are the only implementation.** They run in the browser. `calculators.ts` uses `decimal.js` for precision.
- **There is no oracle.** The Python implementation they came from is gone, so the tests pin current behaviour, not a known-good result.
- **`calculateEV` is a documented placeholder.** It uses `base_price` as a proxy for the drop chance and ignores `luck` and `quality`. Its test is marked `TODO`. Tracked as issue #6. The snapshot holds real drop chances at `data.chances[]` (`chance_percent`, `one_in`).
- **Museum calculator bugs are tracked as issue #1.**
- **`src/lib/calculators.ts` and `src/lib/museum.ts` use tabs.** Everything else under `src/` uses two spaces. `.prettierrc` says `tabWidth: 2`, but CI never runs `prettier --check`. Match the file you are editing. Do not run `npm run format` across `src/`: it rewrites those two files and buries real changes in whitespace. Tracked as issue #7. Each `*.test.ts` sits next to the module it tests.
- **`npm run test` runs vitest.** Config: `frontend/vitest.config.ts`. It runs in the **node** environment. The modules under test (`calculators.ts`, `museum.ts`, `taxonomy.ts`, `snapshot.ts`) are pure. Only `lib/idb.ts` touches `indexedDB`, and it is not under test. Import `describe`, `it` and `expect` from `vitest` explicitly. Do not rely on globals. This needs no tsconfig change and keeps ESLint's `no-undef` quiet. A test that needs the DOM opts in with a `// @vitest-environment jsdom` docblock. `jsdom` is not installed yet.
- **`conftest.py` refuses any URL whose database name does not end in `_test`**, and raises `UnsafeTestDatabaseError` when `TEST_DATABASE_URL` is unset. This is deliberate: a run must never drop a real database. Without `TEST_DATABASE_URL` these files error, because they need a database: `test_integration`, `test_merges`, `test_schema_constraints`, `test_schema_parity`, `test_scrape_resilience`, `test_snapshot_order`, `test_taxonomy`. Set up a test database once with `docker compose up -d db` then `docker exec pick-db psql -U pick -d pick -c "CREATE DATABASE pick_test;"`. Run the suite with `TEST_DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick_test" DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick" .venv/bin/python -m pytest -q`. Never run two pytest sessions against the same test database at once. The `test_engine` fixture drops every table on teardown, so parallel runs tear each other down mid-run and fail in ways that look like real bugs. Run them one after another, or give each its own `_test` database. Pure-logic tests need no database, for example `tests/test_export_snapshot.py` and `tests/test_export_guard.py`. Run one test with `.venv/bin/python -m pytest tests/test_export_guard.py::test_refuses_an_empty_snapshot_over_a_full_one`. GitHub runners get `403 Forbidden` from Miraheze for every request. So `tests/test_scrape_resilience.py` reads `tests/fixtures/*.wiki` instead. Keep that property. The suite must pass with an unreachable wiki, and the live-wiki tests skip via `requires_wiki`. Verify with `TEST_DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick_test" DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick" MEDIAWIKI_API_URL="http://invalid.invalid/api.php" .venv/bin/python -m pytest -q`.
- **`.venv` hard-codes its own absolute path.** Renaming or moving the checkout breaks every script in `.venv/bin`. If paths look wrong, delete `.venv` and recreate it: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt`. Invoke tools as `.venv/bin/python -m <tool>`, not `.venv/bin/<tool>`. The shebangs in `.venv/bin` are what break. `requirements.txt` holds the runtime dependencies and `requirements-dev.txt` the test and lint tools. `pyproject.toml` reads its dependency list from `requirements.txt`, so there is one list. The local `.venv` is Python 3.14. CI runs 3.11 and 3.12. `pyproject.toml` pins `target-version = "py311"` and `python_version = "3.11"`. `deploy/systemd/*.service` hard-code the checkout path. Update them alongside any move.
- **`scripts/refresh_site.sh` parses `.env` line by line** rather than sourcing it. Values such as `USER_AGENT=PICK/1.0 (Prospecting Information & Community Kit)` contain spaces and parentheses. Do not `source .env` in a shell. `app/config.py` reads the same file through `pydantic-settings` (`env_file=".env"`). A value already set in the environment wins over the file.
- **The scrape runs locally from a systemd timer.** The unit files are in `deploy/systemd/`, and the install steps and deploy-key setup are in `SETUP.md`.
- **`ruff format --check` fails on `alembic/`** (4 files). Outside CI's scope. Issue #8.
- **mypy is not in strict mode.** The seven type-error codes are on and the gate is green, but `mypy --strict` reports 42 errors. Do not claim the typecheck is strict. Issue #13.
- **106 items in the committed snapshot carry raw wiki markup in `data`, and 455 of 853 have no `image_url`.** Both pass the schema contract. Issue #9, issue #10. See [snapshot-and-publishing.md](docs/agent-instructions/snapshot-and-publishing.md).
- **`Codes`, `Changelog` and `Guides` are tracked with no parser, so they are never fetched.** Issue #11.
- **`.kilo/plans/` is git-ignored scratch space.** A plan is written when work starts and deleted when it lands. Never read one as a description of the current tree.
- **`master` is the deploy branch.** Pushing it triggers CI and the Pages deploy.
- **No HTTP API.** Do not add a server for data the site already has as a file. The dataset is `snapshot.json`, described by `snapshot.schema.json`.
- **Never hand-edit `frontend/src/lib/snapshot.types.ts`.** It is generated; CI fails if it is stale. Regenerate with `cd frontend && npm run generate:snapshot-types`.
- **The wiki is reachable only from the local machine.** Miraheze returns 403 to GitHub runners. Add no scrape workflows to CI, and no test may depend on the wiki.
- **Target Python 3.11.** Local `.venv` is 3.14; CI runs 3.11 and 3.12. No 3.12+ syntax.
- **`docs/agent-instructions/` holds per-area guidance.** `SETUP.md` is the operational guide.
- **`app/` models, services and the MediaWiki client.** `scrapers/` parses wiki wikitext into items. `scripts/` holds the CLI entry points. `frontend/` is the published site. `frontend/public/snapshot.json` is the dataset and it is committed. `.kilo/plans/` is git-ignored scratch space.
- **`scripts/refresh_site.sh` fails-closed**: scraper exits non-zero if it reached no page; exporter refuses to write a snapshot that would erase the catalogue.
- **`scripts/refresh_site.sh` refuses to run on a dirty tree** (checks `git status --porcelain` before pulling). Keep checkout clean.
- **`scripts/refresh_site.sh` commits only the snapshot.** It ends in `git push origin HEAD:master`, which redeploys the site.
- **`scripts/refresh_site.sh` parses `.env` line by line** rather than sourcing it.
- **`docker compose up -d db` starts Postgres 16** on `localhost:5432` with user `pick`, password `pick` and database `pick`. The scraper and the exporter both need `DATABASE_URL` pointing at it.
- **Migrations live in `alembic/versions/`.** Run them with `.venv/bin/python -m alembic upgrade head`. `alembic/env.py` sets `transaction_per_migration=True`, so each revision gets its own transaction. That is what lets one revision add an enum value and a later one use it; see [data-model.md](data-model.md). For schema changes, see [data-model.md](data-model.md).
- **`.env` is dotenv, not shell.** `scripts/refresh_site.sh` parses `.env` line by line rather than sourcing it. Values such as `USER_AGENT=PICK/1.0 (Prospecting Information & Community Kit)` contain spaces and parentheses. Do not `source .env` in a shell. `app/config.py` reads the same file through `pydantic-settings` (`env_file=".env"`). A value already set in the environment wins over the file.
- **The scrape runs locally from a systemd timer.** The unit files are in `deploy/systemd/`, and the install steps and deploy-key setup are in `SETUP.md`.
- **The `generated-files` job in `.github/workflows/ci.yml` regenerates the snapshot types and fails if they differ from the committed file.** A generated file left stale by a change is a failed build. Regenerating with unchanged input produces no diff; check that before committing.
- **`frontend/src/lib/snapshot.types.ts` is generated from `snapshot.schema.json` by `npm run generate:snapshot-types`.** Never hand-edit it. Everything else under `src/` is hand-written.
- **The item type is the generated `Item`.** Import it from `@/lib/snapshot.types` or `@/lib/snapshot`. `Item.type` is the `ItemType` union, `Item.data` is non-nullable, and there is no `wiki_id`.
- **Calculator result types are hand-written** and live in the modules that compute them. `calculators.ts` exports `EVOutput`, `TTGOutput`, `ModifierOddsOutput` and `BestPanOutput` (camelCase), plus their `*Inputs` types. `museum.ts` exports `MuseumComparatorOutput`, `MuseumOptimizerOutput` and `UnlockCostsOutput`. They are not in a generated file.
- **There is no `src/api/` directory and no API client.** Do not recreate one. The ESLint config still lists `src/api` in `ignorePatterns`; that is a leftover and is harmless.
- **`npm ci` and `npm install` work without `--legacy-peer-deps`.** The lockfile resolves cleanly against the React 19 peer ranges. `--legacy-peer-deps` is harmless but is no longer needed, and CI does not pass it.
- **The Vite `base` is `/PICK/`**, matching the GitHub Pages repo path.
- **Vite 8 resolves the tsconfig `paths` aliases natively** (`resolve.tsconfigPaths`), so the `@/` alias needs no plugin. `vite-tsconfig-paths` was removed.
- **`frontend/public/404.html` is a hand-written SPA fallback for deep links.** GitHub Pages has no rewrite rules.
- **Gates**: `npm run typecheck`, `npm run test`, `npm run lint`, `npm run build`.
- **`npm run lint` runs ESLint.** There is no oxlint in this project, and no `frontend/README.md` — the stock Vite template README that described one is gone.
- **`src/lib/calculators.ts` and `src/lib/museum.ts` are the only implementation.** They run in the browser. `calculators.ts` uses `decimal.js` for precision.
- **There is no oracle.** The Python implementation they came from is gone, so the tests pin current behaviour, not a known-good result.
- **`calculateEV` is a documented placeholder.** It uses `base_price` as a proxy for the drop chance and ignores `luck` and `quality`. Its test is marked `TODO`. Tracked as issue #6. The snapshot holds real drop chances at `data.chances[]` (`chance_percent`, `one_in`).
- **Museum calculator bugs are tracked as issue #1.**
- **`src/lib/calculators.ts` and `src/lib/museum.ts` use tabs.** Everything else under `src/` uses two spaces. `.prettierrc` says `tabWidth: 2`, but CI never runs `prettier --check`. Match the file you are editing. Do not run `npm run format` across `src/`: it rewrites those two files and buries real changes in whitespace. Tracked as issue #7. Each `*.test.ts` sits next to the module it tests.
- **`npm run test` runs vitest.** Config: `frontend/vitest.config.ts`. It runs in the **node** environment. The modules under test (`calculators.ts`, `museum.ts`, `taxonomy.ts`, `snapshot.ts`) are pure. Only `lib/idb.ts` touches `indexedDB`, and it is not under test. Import `describe`, `it` and `expect` from `vitest` explicitly. Do not rely on globals. This needs no tsconfig change and keeps ESLint's `no-undef` quiet. A test that needs the DOM opts in with a `// @vitest-environment jsdom` docblock. `jsdom` is not installed yet.
- **`conftest.py` refuses any URL whose database name does not end in `_test`**, and raises `UnsafeTestDatabaseError` when `TEST_DATABASE_URL` is unset. This is deliberate: a run must never drop a real database. Without `TEST_DATABASE_URL` these files error, because they need a database: `test_integration`, `test_merges`, `test_schema_constraints`, `test_schema_parity`, `test_scrape_resilience`, `test_snapshot_order`, `test_taxonomy`. Set up a test database once with `docker compose up -d db` then `docker exec pick-db psql -U pick -d pick -c "CREATE DATABASE pick_test;"`. Run the suite with `TEST_DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick_test" DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick" .venv/bin/python -m pytest -q`. Never run two pytest sessions against the same test database at once. The `test_engine` fixture drops every table on teardown, so parallel runs tear each other down mid-run and fail in ways that look like real bugs. Run them one after another, or give each its own `_test` database. Pure-logic tests need no database, for example `tests/test_export_snapshot.py` and `tests/test_export_guard.py`. Run one test with `.venv/bin/python -m pytest tests/test_export_guard.py::test_refuses_an_empty_snapshot_over_a_full_one`. GitHub runners get `403 Forbidden` from Miraheze for every request. So `tests/test_scrape_resilience.py` reads `tests/fixtures/*.wiki` instead. Keep that property. The suite must pass with an unreachable wiki, and the live-wiki tests skip via `requires_wiki`. Verify with `TEST_DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick_test" DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick" MEDIAWIKI_API_URL="http://invalid.invalid/api.php" .venv/bin/python -m pytest -q`.
- **`.venv` hard-codes its own absolute path.** Renaming or moving the checkout breaks every script in `.venv/bin`. If paths look wrong, delete `.venv` and recreate it: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt`. Invoke tools as `.venv/bin/python -m <tool>`, not `.venv/bin/<tool>`. The shebangs in `.venv/bin` are what break. `requirements.txt` holds the runtime dependencies and `requirements-dev.txt` the test and lint tools. `pyproject.toml` reads its dependency list from `requirements.txt`, so there is one list. The local `.venv` is Python 3.14. CI runs 3.11 and 3.12. `pyproject.toml` pins `target-version = "py311"` and `python_version = "3.11"`. `deploy/systemd/*.service` hard-code the checkout path. Update them alongside any move.
- **`scripts/refresh_site.sh` parses `.env` line by line** rather than sourcing it. Values such as `USER_AGENT=PICK/1.0 (Prospecting Information & Community Kit)` contain spaces and parentheses. Do not `source .env` in a shell. `app/config.py` reads the same file through `pydantic-settings` (`env_file=".env"`). A value already set in the environment wins over the file.
- **The scrape runs locally from a systemd timer.** The unit files are in `deploy/systemd/`, and the install steps and deploy-key setup are in `SETUP.md`.
- **`ruff format --check` fails on `alembic/`** (4 files). Outside CI's scope. Issue #8.
- **mypy is not in strict mode.** The seven type-error codes are on and the gate is green, but `mypy --strict` reports 42 errors. Do not claim the typecheck is strict. Issue #13.
- **106 items in the committed snapshot carry raw wiki markup in `data`, and 455 of 853 have no `image_url`.** Both pass the schema contract. Issue #9, issue #10. See [snapshot-and-publishing.md](docs/agent-instructions/snapshot-and-publishing.md).
- **`Codes`, `Changelog` and `Guides` are tracked with no parser, so they are never fetched.** Issue #11.
- **`.kilo/plans/` is git-ignored scratch space.** A plan is written when work starts and deleted when it lands. Never read one as a description of the current tree.
- **`master` is the deploy branch.** Pushing it triggers CI and the Pages deploy.
- **No HTTP API.** Do not add a server for data the site already has as a file. The dataset is `snapshot.json`, described by `snapshot.schema.json`.
- **Never hand-edit `frontend/src/lib/snapshot.types.ts`.** It is generated; CI fails if it is stale. Regenerate with `cd frontend && npm run generate:snapshot-types`.
- **The wiki is reachable only from the local machine.** Miraheze returns 403 to GitHub runners. Add no scrape workflows to CI, and no test may depend on the wiki.
- **Target Python 3.11.** Local `.venv` is 3.14; CI runs 3.11 and 3.12. No 3.12+ syntax.
- **`docs/agent-instructions/` holds per-area guidance.** `SETUP.md` is the operational guide.
- **`app/` models, services and the MediaWiki client.** `scrapers/` parses wiki wikitext into items. `scripts/` holds the CLI entry points. `frontend/` is the published site. `frontend/public/snapshot.json` is the dataset and it is committed. `.kilo/plans/` is git-ignored scratch space.

## Detailed guidance

Read the linked file before changing its area (not loaded automatically).

| Working on | Read |
| --- | --- |
| Scraper, parsers, `PARSER_VERSION` | [scraper.md](docs/agent-instructions/scraper.md) |
| Models, migrations, item types, taxonomy, typecheck | [data-model.md](docs/agent-instructions/data-model.md) |
| Snapshot, exporter, refresh cycle, contract | [snapshot-and-publishing.md](docs/agent-instructions/snapshot-and-publishing.md) |
| Vite app, calculators, generated types | [frontend.md](docs/agent-instructions/frontend.md) |
| Running or writing tests | [testing.md](docs/agent-instructions/testing.md) |
| Virtualenv, Postgres, `.env`, systemd | [environment.md](docs/agent-instructions/environment.md) |
| Commits, issues, docs, slash commands | [git-and-issues.md](docs/agent-instructions/git-and-issues.md)