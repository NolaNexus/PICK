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

## Known issues

Do not re-derive these; they are already tracked. Check `ROADMAP.md` for the full list.

- `ruff format` fails on `alembic/` (4 files). Outside CI's scope. Issue #8.
- `src/lib/calculators.ts` and `src/lib/museum.ts` use tabs; everything else uses two
  spaces. Match the file you are editing. Issue #7.
- `calculateEV` uses `base_price` as the drop chance. Issue #6.
- The museum calculator returns empty results. Issue #1.
- mypy is **not** in strict mode. The seven type-error codes are on and the gate is
  green, but `mypy --strict` reports 42 errors. Do not claim the typecheck is strict.
  Issue #13.
- 106 items in the committed snapshot carry raw wiki markup in `data`, and 455 of 853
  have no `image_url`. Both pass the schema contract. Issue #9, issue #10. See
  [snapshot-and-publishing.md](docs/agent-instructions/snapshot-and-publishing.md).
- `app/logging_config.py`, `SlotComparison` in `frontend/src/lib/museum.ts` and
  `frontend/.oxlintrc.json` are all dead. Issue #12.
- `Codes`, `Changelog` and `Guides` are tracked with no parser, so they are never
  fetched. Issue #11.

## Detailed guidance

Read the linked file before changing its area. These are not loaded automatically.

| Working on | Read |
| --- | --- |
| Scraper, parsers, `PARSER_VERSION` | [scraper.md](docs/agent-instructions/scraper.md) |
| Models, migrations, item types, taxonomy, typecheck | [data-model.md](docs/agent-instructions/data-model.md) |
| Snapshot, exporter, refresh cycle, contract | [snapshot-and-publishing.md](docs/agent-instructions/snapshot-and-publishing.md) |
| Vite app, calculators, generated types | [frontend.md](docs/agent-instructions/frontend.md) |
| Running or writing tests | [testing.md](docs/agent-instructions/testing.md) |
| Virtualenv, Postgres, `.env`, systemd | [environment.md](docs/agent-instructions/environment.md) |
| Commits, issues, docs, slash commands | [git-and-issues.md](docs/agent-instructions/git-and-issues.md) |
