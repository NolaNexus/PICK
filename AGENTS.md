# AGENTS.md

Guidance for agents working in this repository. Verify anything not stated here against
`pyproject.toml`, `.github/workflows/ci.yml`, and the code itself.

## What this is

Two deployables in one repo:

- **Backend** — FastAPI + async SQLAlchemy + PostgreSQL (`app/`). Scrapes the Prospecting!
  wiki, stores items/formulas/wiki pages, serves a REST API.
- **Frontend** — React + TypeScript + Vite (`frontend/`), published as a static site on
  GitHub Pages.

The published site reads the **committed** `frontend/public/snapshot.json`, not the API.
The API is local-only. See `README.md` and `SETUP.md` for narrative docs.

## The API surface

`app/api/__init__.py` mounts five routers under `/api/v1`:

| Route | Router | Serves |
| --- | --- | --- |
| `/api/v1/items` | `items.py` | Items, plus `/taxonomy` (the type list), `/types`, `/type/{type}` and `/{slug}` |
| `/api/v1/formulas` | `formulas.py` | Game formulas and their confidence levels |
| `/api/v1/meta` | `meta.py` | Database counts, the last scrape, the current game version |
| `/api/v1/search` | `search.py` | Full-text search across items |
| `/api/v1/export` | `export.py` | The public dataset snapshot (no response model — it streams the snapshot dict) |

`app/main.py` adds `/` (a status object), `/metrics` (Prometheus), and mounts the
health router at `/api/v1/health`.

**The health paths carry a doubled `health` segment.** `app/main.py` mounts
`health_router` at `/api/v1/health` and `app/monitoring.py` declares
`APIRouter(prefix="/health")`, so the real URLs are `/api/v1/health/health`,
`/api/v1/health/health/ready` and `/api/v1/health/health/live`. The natural guess
of `/api/v1/health/ready` is a 404. These paths are published in `openapi.json` and
in the generated `frontend/src/api/pick.ts`, so changing the prefix means
regenerating both.

**`/metrics` is served by `metrics_endpoint` in `app/main.py`, not by the router in
`app/monitoring.py`.** That router is mounted nowhere, so its `@router.get("")`
metrics handler is dead code — do not "fix" the wrong one.

## Layout

| Path | Purpose |
| --- | --- |
| `app/` | FastAPI app: `api/` routers, `services/` domain logic, `models/` SQLAlchemy models, `schemas/` Pydantic, `taxonomy.py`, `config.py` |
| `app/monitoring.py` | Prometheus metrics, the health router, and the request-metrics middleware |
| `app/logging_config.py` | `setup_logging`; JSON logs unless `settings.debug` |
| `scrapers/` | One module per wiki page; each exposes a `parse_*` function. `registry.py` maps page titles → parsers and holds `TRACKED_PAGES`; `types.py` holds `ParsedItem` |
| `scripts/` | CLI entry points: `scraper.py`, `export_snapshot.py`, `seed_formulas.py`, `coverage_report.py`, `refresh_site.sh` |
| `frontend/` | Vite app. `src/api/pick.ts` is **generated** by orval; `src/lib/snapshot.types.ts` is **generated** by json-schema-to-typescript; `src/lib/snapshot.ts` loads the static snapshot |
| `alembic/versions/` | Migrations, numbered sequentially (currently `001`–`007`) |
| `snapshot.schema.json` | The contract for the published file. The exporter writes it, the client reads it, CI checks it |
| `tests/` | pytest. `tests/fixtures/*.wiki` holds captured page wikitext |

## Commands

Run backend commands with `.venv/bin/python -m ...` (the `-m` form, not the console
scripts — see *Virtualenv* below).

```bash
# Backend gates — use these exact scopes, they match CI
.venv/bin/ruff check app scrapers scripts tests
.venv/bin/ruff format --check app scrapers scripts tests
.venv/bin/mypy app/ scrapers/ scripts/

# Frontend gates
cd frontend && npm run typecheck && npm run test && npm run lint && npm run build

# Migrations
.venv/bin/python -m alembic upgrade head
```

### Tests

**`pytest` needs a test database and errors out without one.** `tests/conftest.py` refuses
any URL whose database name does not end in `_test` and raises
`UnsafeTestDatabaseError` when `TEST_DATABASE_URL` is unset — this is deliberate, so a
run can never drop a real database. Without it the suite reports **335 passed, 77
errors** (the DB-backed files are `test_api`, `test_integration`, `test_merges`,
`test_schema_constraints`, `test_schema_parity`, `test_scrape_resilience`,
`test_snapshot_order`, `test_taxonomy`).

```bash
docker compose up -d db
docker exec pick-db psql -U pick -d pick -c "CREATE DATABASE pick_test;"
TEST_DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick_test" \
DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick" \
  .venv/bin/python -m pytest -q
```

**Never run two pytest sessions against the same test database at once.** The
`test_engine` fixture drops every table on teardown, so two runs in parallel tear
each other's tables down mid-run and fail in ways that look like real bugs. Run
them one after another, or give each its own `_test` database.

Pure-logic tests (e.g. `tests/test_export_snapshot.py`, `tests/test_export_guard.py`) need
no database and run standalone. Run one test with
`.venv/bin/python -m pytest tests/test_export_guard.py::test_refuses_an_empty_snapshot_over_a_full_one`.

**No test may depend on the wiki being reachable.** GitHub runners get `403 Forbidden`
from Miraheze for every request, so `tests/test_scrape_resilience.py` reads
`tests/fixtures/*.wiki` instead. Keep that property: the suite must pass with
`MEDIAWIKI_API_URL` pointed at an invalid host, with the live-wiki tests then skipping
via `requires_wiki`. Verify with:

```bash
TEST_DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick_test" \
DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick" \
MEDIAWIKI_API_URL="http://invalid.invalid/api.php" .venv/bin/python -m pytest -q
```

### Refreshing the data

`scripts/refresh_site.sh` is the whole cycle (start DB → migrate → scrape → seed → export
→ commit → push). It is **fail-closed**: the scraper exits non-zero if it reached no page,
and `scripts/export_snapshot.py` refuses to write a snapshot that would erase the
catalogue. Use `--dry-run` to exercise it without writing or publishing anything. It ends
in `git push origin HEAD:master`, which redeploys the site.

## Things an agent would get wrong

**The wiki is only reachable from this machine.** Miraheze answers GitHub-hosted runners
with 403, so there are no scrape workflows in CI and there must not be any. The scrape
runs locally via a systemd timer (`deploy/systemd/`, install steps in `SETUP.md`).

**`pages_scraped` is not "pages fetched".** It counts the titles that did not raise, and
that includes the pages with no parser, which are never fetched. When every fetch fails,
`pages_scraped` is the number of no-parser pages (3), not 0 — which is why guarding on
it would never fire. `pages_ok` in `app/services/scraper.py` is the counter that means
"the run actually reached a page", and `scripts/scraper.py` guards on `pages_ok == 0`.
Do not swap them.

**`openapi.json` and `frontend/src/api/pick.ts` are generated, and both are committed.**
After changing any route or schema, regenerate both:

```bash
.venv/bin/python -c "import json; from app.main import app; json.dump(app.openapi(), open('openapi.json','w'), indent=2)"
cd frontend && npm run generate:api
```

The spec is written with `indent=2` and **no trailing newline**; the orval config
(`frontend/orval.config.mjs`) reads `../openapi.json` and writes `frontend/src/api/`.
Regenerating with unchanged input produces no diff — check that before committing.

**The frontend's item type is the generated `Item`, not an API response type.**
`frontend/src/lib/snapshot.types.ts` holds `Item`, generated from
`snapshot.schema.json`, and it is the shape the site actually uses. `Item.type` is
the `ItemType` union, `Item.data` is non-nullable, and there is no `wiki_id` — the
column was dropped from the database. Import it from `@/lib/snapshot.types` (or
`@/lib/snapshot`, which re-exports it).

**The calculator result types live in the modules that compute them.**
`frontend/src/lib/calculators.ts` exports `EVOutput`, `TTGOutput`,
`ModifierOddsOutput`, `BestPanOutput` (camelCase), and `frontend/src/lib/museum.ts`
exports `MuseumOptimizerOutput` and `SlotComparison`. There is no API endpoint for
the calculators — they run in the browser — so these types are hand-written and
must not be looked for in a generated file. `frontend/src/api/pick.schemas.ts` was a
stale leftover from the orval `tags-split` era; it was deleted, and the types it
held snake_case versions of were replaced by the camelCase ones above.

**Never hand-edit `frontend/src/api/pick.ts` or `frontend/src/lib/snapshot.types.ts`.**
They are generated and are overwritten. `frontend/src/api/client.ts` is hand-written,
not generated. `frontend/src/api/pick.ts` is generated but **not yet imported by any
frontend code** — the site reads the committed snapshot, and `frontend/src/lib/snapshot.ts`
calls the API through the raw `request()` client instead. It is still committed and
CI-checked because it is the typed client for the published OpenAPI spec. Do not
"clean it up" without also dropping `openapi.json` and the `generated-files` job.

**CI checks that the generated files are current.** The `generated-files` job in
`.github/workflows/ci.yml` regenerates the OpenAPI spec, the orval client and the
snapshot types, and fails if any of them differs from what is committed. So a
generated file left behind by a change is a failed build, not a surprise later.

**The refresh job refuses to publish from a dirty tree.** `scripts/refresh_site.sh`
checks `git status --porcelain` before it pulls, and refuses to commit anything but
the snapshot. It publishes from this checkout, so the checkout has to be clean — a
stray edit would otherwise fail the pull with a message that reads like a network
problem, or be left behind by the commit.

**The calculators live in the frontend, not the API.** `frontend/src/lib/calculators.ts`
and `frontend/src/lib/museum.ts` hold the only implementation, and they run in the
browser. There is no backend calculator: the API serves the data — items, formulas,
search, metadata, and the snapshot export — and nothing else. The site is static and
never calls the API. `frontend/src/lib/calculators.ts` uses `decimal.js` for precision.

**`ruff format --check` fails on `alembic/` today** (4 files would be reformatted).
That drift is pre-existing and outside CI's scope (`ruff format --check app scrapers
scripts tests`, which passes with 110 files already formatted). Do not "fix" it as
part of an unrelated change, and do not let it block you — match CI's scopes.
Tracked as issue #8.

**`PARSER_VERSION` (`scrapers/registry.py`) controls re-parsing.** A page is only re-parsed
when its wikitext or this version changes. Bump it when a parser or the shared renderer
(`scrapers/wikitext.py`) changes shape, or the stored data keeps the old shape.

**`TRACKED_PAGES` and `PARSERS` are separate.** A page can be tracked with `PARSERS[page] =
None` (currently `Codes`, `Changelog`, `Guides`): it is counted but never fetched. When
adding a page, add the parser too. There are 24 parsers; adding one means updating
`PARSER_VERSION` as well.

**Item identity is by slug, namespaced by type.** `type_prefixed_slug()` in
`app/services/reconcile.py` keeps an NPC and a quest with the same name distinct.
`items.slug` is globally unique; the same game object on several wiki pages is stored
once. Items removed from a page are soft-deleted (`is_active = false`), never deleted.

**The taxonomy lives in the database, not in Python.** The `taxonomy` table holds every
type with its area, group, label, kind, display order and whether it is a fragment.
`app/taxonomy.py` reads it through `load_taxonomy(db)` — an async loader, because the
rows are in the database. The taxonomy is read that way in the API and the exporter;
both already have a session. A type that is not in the table cannot be written to
`items.type`, because that column is a PostgreSQL enum over the same 33 values.

**Fragment types are not items.** Eight types are marked `is_fragment` in the taxonomy
table: `museum_ore`, `blueprint`, `mutation_catalyst`, `excavation_reward`,
`museum_display`, `museum_info`, `merchant_item`, `consumable`. A parser emits them so
reconciliation can fold them into another row. They are not browsable, but the client
still needs a label for one of them: `mutation_catalyst` for "Frosthorn Pendant" has no
equipment to fold into, so it stays active. The folds are described by the `FOLDS` table
in `app/services/reconcile.py`; add one there rather than writing a new bespoke merge.
Only four types are in `FOLDS` (`museum_ore`, `blueprint`, `mutation_catalyst`,
`excavation_reward`); the other four are handled by dedicated code
(`_merge_museum_displays`, the merchant merge, and the consumable→relic reclassification).

**The database enforces the rules the code assumes.** `items` has three check
constraints — `ck_items_name_not_empty`, `ck_items_data_object` and
`ck_items_slug_prefix` — and the slug one is the important one: a slug must be the type
prefix (with hyphens, so `enchant_book` gives `enchant-book-…`) plus the name. That is
what keeps `items.slug` unique and deterministic whatever order the pages were scraped
in. `tests/test_schema_constraints.py` asserts the database rejects rows that break
each of them, so a rule that is only in Python fails the build. The `items.data` column
is `JSONB` with `jsonb_typeof(data) = 'object'`; the check is added by hand in
`app/models/item.py` because the function that reads a JSON value's type is named
differently in PostgreSQL and SQLite.

**Change detection is an exclusion list, not an inclusion list.** `_comparable()` in
`scripts/export_snapshot.py` serialises the *whole* snapshot and strips an explicit list
of volatile keys (scrape timestamps, `data.merchant.last_seen`, the `last_scrape`
counters). Anything else is compared, including the taxonomy. The old inclusion list
silently missed the taxonomy, so a taxonomy change never published; the new one fails
loud instead (an unnecessary commit, not a stale site). If you add a field that changes
every run, add it to the volatile list — do not stop comparing it.

**Snapshot rows must be ordered.** `build_snapshot()` in `app/services/snapshot.py` has an
explicit `ORDER BY` on every query, and `_comparable` sorts the rows before comparing
them. Without both, PostgreSQL returns rows in plan order, which is not stable between
runs: the same 853 items come back in a different order, the file differs every time, and
the refresh job commits it daily for no reason. If you add a query to `build_snapshot`,
give it an `ORDER BY`.

**`SNAPSHOT_SCHEMA_VERSION` is declared twice** — `app/services/snapshot.py` (currently
6) and `frontend/src/lib/snapshot.ts` (currently 6). `tests/test_snapshot_contract.py`
fails if they drift. Bump both when the payload shape changes.

**The published file has a contract.** `snapshot.schema.json` describes
`snapshot.json`: every key, every type, `additionalProperties: false` so an
undeclared field is a failure rather than a surprise. `tests/test_snapshot_contract.py`
validates the committed file against it, and checks that a deliberately broken
snapshot is rejected. The schema's `itemType` list and the database's `item_type` enum
must hold the same values; the test asserts it. The frontend's types are **generated**
from the schema by `npm run generate:snapshot-types` into
`frontend/src/lib/snapshot.types.ts` — never hand-edit that file. When the shape
changes, change the schema first, regenerate, then regenerate the API spec.

**`.env` is dotenv, not shell.** `scripts/refresh_site.sh` parses it line by line rather
than sourcing it, because `USER_AGENT=PICK/1.0 (Prospecting Information & Community Kit)`
contains spaces and parentheses. Do not `source .env` in a shell. `app/config.py` reads
the same file through `pydantic-settings` (`env_file=".env"`), so a value already set in
the environment wins over the file.

**The typecheck is strict — do not widen it.** `pyproject.toml` used to disable seven
error codes (`arg-type`, `assignment`, `attr-defined`, `call-arg`, `index`, `misc`,
`var-annotated`) because the models used the legacy SQLAlchemy 1.x `Column()` form,
which left every query result untyped, and the parsers returned `dict[str, Any]`. Both
are fixed, so all seven are on. To see what one would catch, run
`mypy app/ scrapers/ scripts/ --enable-error-code=<code>`.

**The models use `Mapped[]`, not `Column()`.** `app/models/*.py` declare their columns
with `Mapped[T]` and `mapped_column()`. That is what makes a query result
`list[Item]` rather than `list[Any]`, which is what the typecheck checks against.
`Item.type` is `Mapped[str]`, not an enum type: the column is a database enum but
Python sees the string, and the reconciler compares and assigns it as one.

**The parsers return `ParsedItem`.** `scrapers/types.py` declares the shape a page
parser produces, and the 24 parsers in `scrapers/registry.py` are annotated with it.
`ParsedItem` requires `id`, `type`, `name`, `slug`, `data` and `image_url`;
`description` is `NotRequired` because some parsers put it inside `data` instead.
A parser that builds a different shape needs its own TypedDict, not a loosened one.

**The models and the migrations must describe the same schema.**
`tests/test_schema_parity.py` compares the columns, nullability and defaults the
models declare with the ones the database has. The database is created by the
migrations in production and by `Base.metadata.create_all` in the tests, so a
disagreement means a test can pass against a schema the site never runs on.

**The frontend has a test runner: vitest.** `npm run test` runs it; the files live
next to the code they test, as `src/lib/*.test.ts`. The config is
`frontend/vitest.config.ts` and it runs in the **node** environment, because the
modules under test (`calculators.ts`, `museum.ts`, `taxonomy.ts`, `snapshot.ts`) are
pure — only `lib/idb.ts` touches `indexedDB`, and it is not under test. Import
`describe`/`it`/`expect` from `vitest` explicitly rather than using globals: it
needs no tsconfig change and keeps ESLint's `no-undef` quiet. A test that needs
the DOM opts in with a `// @vitest-environment jsdom` docblock, and `jsdom` is not
installed yet.

**The calculators have no oracle.** The Python implementation they were ported
from is gone, so the tests pin the *current* behaviour rather than a known-good
one. `calculateEV` has a documented placeholder — it uses `base_price` as a proxy
for the drop chance and ignores `luck` and `quality` — and its test is marked with
a `TODO` so the expected value is visibly provisional.

## Virtualenv

`.venv` hard-codes its own absolute path. **Renaming or moving the checkout breaks every
script in `.venv/bin`** — this has already happened once in this repo. If paths look
wrong, delete `.venv` and recreate it:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
```

`requirements.txt` holds the runtime dependencies and `requirements-dev.txt` the test and
lint tools. `pyproject.toml` reads its dependency list from `requirements.txt`, so there is
one list rather than two that can disagree.

Invoke through `.venv/bin/python -m ...` rather than `.venv/bin/<tool>`, whose shebangs
are the part that breaks. `deploy/systemd/*.service` also hard-code the checkout path and
must be updated alongside.

The local `.venv` is Python 3.14; CI runs 3.11 and 3.12. `pyproject.toml` pins
`target-version = "py311"` and `python_version = "3.11"` — do not use 3.12+ syntax.

## Database

`docker compose up -d db` starts Postgres 16 on `localhost:5432` with credentials
`pick`/`pick` and database `pick`. The API and the exporter both need `DATABASE_URL`
pointing at it.

Migrations live in `alembic/versions/`. Add a new numbered revision for schema changes;
never edit an applied migration. The taxonomy rows and the `item_type` enum live in
`006_enforce_schema_invariants.py` — that is the file to edit when a type is added.

## Frontend

`npm ci` and `npm install` need `--legacy-peer-deps` (React 19 peer ranges). The Vite
`base` is `/PICK/`, matching the GitHub Pages repo path. `frontend/public/404.html` is a
hand-written SPA fallback for deep links — GitHub Pages has no rewrite rules.

**The frontend has mixed indentation.** `src/lib/calculators.ts` and `src/lib/museum.ts`
use tabs; everything else under `src/` uses two spaces. `.prettierrc` says
`tabWidth: 2`, but CI never runs `prettier --check`, so the drift never fails a
build. **Match the file you are editing** — do not run `npm run format` across
`src/`, because it rewrites those two files wholesale and buries a real change in
whitespace. Each `*.test.ts` matches the module it tests. Tracked as issue #7.

The site works with no API at all: it fetches the committed `snapshot.json`. Setting
`VITE_API_BASE_URL` points it at a live API instead.

## Git

Conventional Commit prefixes, as used throughout the history: `feat:`, `fix:`, `chore:`,
`docs:`, `ci:`, `test:`, `refactor:`. Write the body as the *why* — several commits
record the failure mode they prevent.

`master` is the deploy branch; pushing to it triggers the CI workflow and the GitHub
Pages deploy.

## Issues

`.github/ISSUE_TEMPLATE/` holds three forms — `bug_report.yml`, `feature_request.yml`
and `task.yml` — and each sets its own label. Use one of them rather than a blank
issue; `config.yml` sets `blank_issues_enabled: false`.

**Issue types do not work on this repository.** GitHub's issue types are an
organisation feature, and `NolaNexus/PICK` is user-owned, so
`GET /repos/NolaNexus/PICK/issue-types` lists the three defaults but assigning one
is a silent no-op — the REST and GraphQL calls return `200` and leave `issueType`
null, with no event on the issue's timeline. Use the **labels** instead: `bug`,
`enhancement`, `documentation`. The templates already do this.

## Docs

`README.md` is the overview, `SETUP.md` the operational guide (including the systemd
install and the deploy-key setup), `.kilo/plans/` holds dated working plans. Plans are
committed history, not current documentation: they describe intent at a point in time, and
several describe code that was later removed or rewritten. Some carry a `**Status:**`
line saying whether they were implemented. Re-verify any plan's claims against the
current code before acting on it.

`.kilo/command/` holds slash commands for this repo: `/check`, `/check-offline`,
`/refresh`, `/generate-api`, `/verify-guards`. They carry the exact working invocations
and the traps that go with them.
