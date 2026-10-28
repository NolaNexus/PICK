# AGENTS.md

Guidance for agents working in this repository. Verify anything not stated here against
`pyproject.toml`, `.github/workflows/ci.yml`, and the code itself.

## What this is

Two deployables in one repo:

- **Backend** — FastAPI + async SQLAlchemy + PostgreSQL (`app/`). Scrapes the Prospecting!
  wiki, stores items/formulas/wiki pages, serves a REST API and calculators.
- **Frontend** — React + TypeScript + Vite (`frontend/`), published as a static site on
  GitHub Pages.

The published site reads the **committed** `frontend/public/snapshot.json`, not the API.
The API is local-only. See `README.md` and `SETUP.md` for narrative docs.

## Layout

| Path | Purpose |
| --- | --- |
| `app/` | FastAPI app: `api/` routers, `services/` domain logic, `models/` SQLAlchemy models, `schemas/` Pydantic, `taxonomy.py`, `config.py` |
| `scrapers/` | One module per wiki page; each exposes a `parse_*` function. `registry.py` maps page titles → parsers and holds `TRACKED_PAGES` |
| `scripts/` | CLI entry points: `scraper.py`, `export_snapshot.py`, `seed_formulas.py`, `coverage_report.py`, `refresh_site.sh` |
| `frontend/` | Vite app. `src/api/` is **generated** by orval; `src/lib/snapshot.ts` loads the static snapshot |
| `alembic/versions/` | Migrations, numbered sequentially |
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
cd frontend && npm run typecheck && npm run lint && npm run build

# Migrations
.venv/bin/python -m alembic upgrade head
```

### Tests

**`pytest` needs a test database and errors out without one.** `tests/conftest.py` refuses
any URL whose database name does not end in `_test` and raises
`UnsafeTestDatabaseError` when `TEST_DATABASE_URL` is unset — this is deliberate, so a
run can never drop a real database. 28 tests error without it.

```bash
docker compose up -d db
docker exec pick-db psql -U pick -d pick -c "CREATE DATABASE pick_test;"
TEST_DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick_test" \
DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick" \
  .venv/bin/python -m pytest -q
```

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
catalogue. Use `--dry-run` to exercise it without writing or publishing anything.

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

**`openapi.json` and `frontend/src/api/` are generated, and both are committed.** After
changing any route or schema, regenerate both:

```bash
.venv/bin/python -c "import json; from app.main import app; json.dump(app.openapi(), open('openapi.json','w'), indent=2)"
cd frontend && npm run generate:api
```

The spec is written with `indent=2` and **no trailing newline**; the orval config
(`frontend/orval.config.mjs`) reads `../openapi.json` and writes `frontend/src/api/`.
Regenerating with unchanged input produces no diff — check that before committing.

**Never hand-edit `frontend/src/api/pick.ts` or `pick.schemas.ts`.** They are orval
output and are overwritten.

**`ruff format --check` fails on `alembic/` today.** That drift is pre-existing and
outside CI's scope (`ruff format --check app scrapers scripts tests`). Do not "fix" it as
part of an unrelated change, and do not let it block you — match CI's scopes.

**`PARSER_VERSION` (`scrapers/registry.py`) controls re-parsing.** A page is only re-parsed
when its wikitext or this version changes. Bump it when a parser or the shared renderer
(`scrapers/wikitext.py`) changes shape, or the stored data keeps the old shape.

**`TRACKED_PAGES` and `PARSERS` are separate.** A page can be tracked with `PARSERS[page] =
None` (currently `Codes`, `Changelog`, `Guides`): it is counted but never fetched. When
adding a page, add the parser too.

**Item identity is by slug, namespaced by type.** `type_prefixed_slug()` in
`app/services/reconcile.py` keeps an NPC and a quest with the same name distinct.
`items.slug` is globally unique; the same game object on several wiki pages is stored
once. Items removed from a page are soft-deleted (`is_active = false`), never deleted.

**`data.merchant.last_seen` is volatile.** Merchant stock rotates daily, so
`_comparable` in `scripts/export_snapshot.py` explicitly strips it before comparing. The
same function ignores scrape timestamps and the per-run `last_scrape` telemetry
(`pages_scraped`/`pages_changed`/`pages_errors`) entirely — they differ on every run, so
including them would make each run look like a change and commit the file daily.

**Snapshot rows must be ordered.** `build_snapshot()` in `app/services/snapshot.py` has an
explicit `ORDER BY` on every query, and `_comparable` sorts the rows before comparing
them. Without both, PostgreSQL returns rows in plan order, which is not stable between
runs: the same 853 items come back in a different order, the file differs every time, and
the refresh job commits it daily for no reason. If you add a query to `build_snapshot`,
give it an `ORDER BY`.

**`.env` is dotenv, not shell.** `scripts/refresh_site.sh` parses it line by line rather
than sourcing it, because `USER_AGENT=PICK/1.0 (Prospecting Information & Community Kit)`
contains spaces and parentheses. Do not `source .env` in a shell.

## Virtualenv

`.venv` hard-codes its own absolute path. **Renaming or moving the checkout breaks every
script in `.venv/bin`** — this has already happened once in this repo. If paths look
wrong, delete `.venv` and recreate it:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

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
never edit an applied migration.

## Frontend

`npm ci` and `npm install` need `--legacy-peer-deps` (React 19 peer ranges). The Vite
`base` is `/PICK/`, matching the GitHub Pages repo path. `frontend/public/404.html` is a
hand-written SPA fallback for deep links — GitHub Pages has no rewrite rules.

The site works with no API at all: it fetches the committed `snapshot.json`. Setting
`VITE_API_BASE_URL` points it at a live API instead.

## Git

Conventional Commit prefixes, as used throughout the history: `feat:`, `fix:`, `chore:`,
`docs:`, `ci:`, `test:`, `refactor:`. Write the body as the *why* — several commits
record the failure mode they prevent.

`master` is the deploy branch; pushing to it triggers the CI workflow and the GitHub
Pages deploy.

## Docs

`README.md` is the overview, `SETUP.md` the operational guide (including the systemd
install and the deploy-key setup), `.kilo/plans/` holds dated working plans. Plans are
committed history, not current documentation: they describe intent at a point in time, and
several describe code that was later removed or rewritten. Only one carries a
`**Status:**` line. Re-verify any plan's claims against the current code before acting
on it. `SETUP.md` still describes the removed wiki webhook in its "Step 2"; that section
is stale.

`.kilo/command/` holds slash commands for this repo: `/check`, `/check-offline`,
`/refresh`, `/generate-api`, `/verify-guards`. They carry the exact working invocations
and the traps that go with them.
