---
description: Run the full backend and frontend gate suite the way CI does
---

Run every check that CI runs, in the order CI runs them. Stop at the first failure.

```bash
cd /home/nola/Desktop/PICK

.venv/bin/python -m ruff check app scrapers scripts tests
.venv/bin/python -m ruff format --check app scrapers scripts tests
.venv/bin/python -m mypy app/ scrapers/ scripts/

TEST_DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick_test" \
DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick" \
  .venv/bin/python -m pytest -q

cd frontend && npm run typecheck && npm run test && npm run lint && npm run build
```

CI also checks that the generated snapshot types are current. To check that locally,
regenerate them and see whether anything changed:

```bash
cd /home/nola/Desktop/PICK/frontend && npm run generate:snapshot-types
cd .. && git diff --exit-code frontend/src/lib/snapshot.types.ts
```

Notes:

- The `ruff format` scope is `app scrapers scripts tests` on purpose. `alembic/`
  has pre-existing formatting drift that is not in CI's scope — do not "fix" it
  as part of an unrelated change, and do not let it block the run.
- `pytest` needs `TEST_DATABASE_URL` to name a database ending in `_test`, or
  67 tests error with `UnsafeTestDatabaseError`. Create it once with
  `docker exec pick-db psql -U pick -d pick -c "CREATE DATABASE pick_test;"`.
- `npm ci` / `npm install` work without `--legacy-peer-deps`. The lockfile resolves
  cleanly; the flag is not needed.
- The Python dependencies are in `requirements.txt` and the test and lint tools
  are in `requirements-dev.txt`. Install both to work on the project.
- There is no API client to regenerate. The only generated file is
  `frontend/src/lib/snapshot.types.ts`, produced from `snapshot.schema.json`.
