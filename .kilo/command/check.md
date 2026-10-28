---
description: Run the full backend and frontend gate suite the way CI does
---

Run every check that CI runs, in the order CI runs them. Stop at the first failure.

```bash
cd /home/nola/Desktop/PICK

.venv/bin/ruff check app scrapers scripts tests
.venv/bin/ruff format --check app scrapers scripts tests
.venv/bin/mypy app/ scrapers/ scripts/

TEST_DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick_test" \
DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick" \
  .venv/bin/python -m pytest -q

cd frontend && npm run typecheck && npm run lint && npm run build
```

CI also checks that the generated files are current. To check that locally,
regenerate them and see whether anything changed:

```bash
cd /home/nola/Desktop/PICK
.venv/bin/python -c "import json; from app.main import app; json.dump(app.openapi(), open('openapi.json','w'), indent=2)"
cd frontend && npm run generate:api && npm run generate:snapshot-types
cd .. && git diff --exit-code openapi.json frontend/src/api/ frontend/src/lib/snapshot.types.ts
```

Notes:

- The `ruff format` scope is `app scrapers scripts tests` on purpose. `alembic/`
  has pre-existing formatting drift that is not in CI's scope — do not "fix" it
  as part of an unrelated change, and do not let it block the run.
- `pytest` needs `TEST_DATABASE_URL` to name a database ending in `_test`, or
  28 tests error with `UnsafeTestDatabaseError`. Create it once with
  `docker exec pick-db psql -U pick -d pick -c "CREATE DATABASE pick_test;"`.
- `npm ci` / `npm install` need `--legacy-peer-deps` (React 19 peer ranges).
- The Python dependencies are in `requirements.txt` and the test and lint tools
  are in `requirements-dev.txt`. Install both to work on the project.
- If the API surface changed, also regenerate the committed spec and client:
  `.venv/bin/python -c "import json; from app.main import app; json.dump(app.openapi(), open('openapi.json','w'), indent=2)"`
  then `cd frontend && npm run generate:api`.
