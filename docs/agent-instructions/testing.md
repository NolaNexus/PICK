# Testing

## Backend: pytest needs a test database

`tests/conftest.py` refuses any URL whose database name does not end in `_test`, and
raises `UnsafeTestDatabaseError` when `TEST_DATABASE_URL` is unset. This is deliberate:
a run must never drop a real database.

Without `TEST_DATABASE_URL` these files error, because they need a database:
`test_integration`, `test_merges`, `test_schema_constraints`, `test_schema_parity`,
`test_scrape_resilience`, `test_snapshot_order`, `test_taxonomy`.

Set up a test database once:

```bash
docker compose up -d db
docker exec pick-db psql -U pick -d pick -c "CREATE DATABASE pick_test;"
```

Run the suite:

```bash
TEST_DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick_test" \
DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick" \
  .venv/bin/python -m pytest -q
```

- Never run two pytest sessions against the same test database at once. The
  `test_engine` fixture drops every table on teardown, so parallel runs tear each other
  down mid-run and fail in ways that look like real bugs. Run them one after another, or
  give each its own `_test` database.
- Pure-logic tests need no database, for example `tests/test_export_snapshot.py` and
  `tests/test_export_guard.py`.
- Run one test with:
  `.venv/bin/python -m pytest tests/test_export_guard.py::test_refuses_an_empty_snapshot_over_a_full_one`

## No test may depend on the wiki

GitHub runners get `403 Forbidden` from Miraheze for every request. So
`tests/test_scrape_resilience.py` reads `tests/fixtures/*.wiki` instead. Keep that
property. The suite must pass with an unreachable wiki, and the live-wiki tests skip via
`requires_wiki`. Verify with:

```bash
TEST_DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick_test" \
DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick" \
MEDIAWIKI_API_URL="http://invalid.invalid/api.php" .venv/bin/python -m pytest -q
```

## Frontend: vitest

- `npm run test` runs vitest. Config: `frontend/vitest.config.ts`. It runs in the **node**
  environment.
- The modules under test (`taxonomy.ts`, `snapshot.ts`) are pure. Only `lib/idb.ts` touches `indexedDB`, and it is not under test.
- Import `describe`, `it` and `expect` from `vitest` explicitly. Do not rely on globals.
  This needs no tsconfig change and keeps ESLint's `no-undef` quiet.
- A test that needs the DOM opts in with a `// @vitest-environment jsdom` docblock.
  `jsdom` is not installed yet.
