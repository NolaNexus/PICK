# AGENTS.md

PICK scrapes the Prospecting! wiki into PostgreSQL and exports a committed
`frontend/public/snapshot.json`, which a static React + Vite site reads. The site never
calls the backend. Verify anything here against `pyproject.toml`, `.github/workflows/ci.yml`
and the code.

## Commands

Run backend tools as `.venv/bin/python -m <tool>` ([details](docs/agent-instructions/environment.md)).
The scopes match CI.

```bash
.venv/bin/python -m ruff check app scrapers scripts tests
.venv/bin/python -m ruff format --check app scrapers scripts tests
.venv/bin/python -m mypy app/ scrapers/ scripts/
cd frontend && npm run typecheck && npm run test && npm run lint && npm run build
.venv/bin/python -m alembic upgrade head
```

## Rules for every task

- **No HTTP API.** Do not add a server for data the site already has as a file.
  The dataset is `snapshot.json`, described by `snapshot.schema.json`.
- **`master` is the deploy branch.** Pushing it triggers CI and the Pages deploy.
- **Never hand-edit `frontend/src/lib/snapshot.types.ts`.** It is generated; CI fails if
  it is stale. Regenerate with `cd frontend && npm run generate:snapshot-types`.
- **The wiki is reachable only from the local machine.** Miraheze returns 403 to GitHub
  runners. Add no scrape workflows to CI, and no test may depend on the wiki.
- **Target Python 3.11.** Local `.venv` is 3.14; CI runs 3.11 and 3.12. No 3.12+ syntax.

## Known issues (tracked; do not re-derive)

- `ruff format` fails on `alembic/` (#8); tabs remain in `museum.ts` (#7).
- Museum calculator returns empty results (#1); `calculateEV` is a placeholder (#6).
- `mypy --strict` reports 42 errors; mypy is not strict (#13).
- 455 of 853 items lack `image_url` (#10).
- Dead code: `app/logging_config.py`, `SlotComparison`, `frontend/.oxlintrc.json` (#12).
- `Codes`, `Changelog`, `Guides` are tracked with no parser (#11).

## Non-obvious commands

- Single backend test: `.venv/bin/python -m pytest tests/test_export_snapshot.py -q`
- DB-backed tests need `TEST_DATABASE_URL` ending in `_test`; start Postgres with `docker compose up -d db`.
- Full refresh (fail-closed, commits only `snapshot.json`, pushes `master`):
  `./scripts/refresh_site.sh [--dry-run|--full]`
- Single frontend test: `cd frontend && npm run test -- src/lib/snapshot.test.ts`

## Detailed guidance

Read the linked file before changing its area. These are not loaded automatically.

| Working on | Read |
| --- | --- |
| Scraper, parsers, `PARSER_VERSION` | [scraper.md](docs/agent-instructions/scraper.md) |
| Models, migrations, item types, taxonomy, typecheck | [data-model.md](docs/agent-instructions/data-model.md) |
| Snapshot, exporter, refresh cycle, contract | [snapshot-and-publishing.md](docs/agent-instructions/snapshot-and-publishing.md) |
| Vite app, generated types | [frontend.md](docs/agent-instructions/frontend.md) |
| Running or writing tests | [testing.md](docs/agent-instructions/testing.md) |
| Virtualenv, Postgres, `.env`, systemd | [environment.md](docs/agent-instructions/environment.md) |
| Commits, issues, docs, slash commands | [git-and-issues.md](docs/agent-instructions/git-and-issues.md) |
