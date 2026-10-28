# Remove the API layer — the project becomes a static site plus a scraper

**Status:** implemented.

## Outcome

The API is gone. `app/api/`, `app/main.py`, `app/schemas/`, `app/monitoring.py`,
`app/utils/__init__.py`, `openapi.json`, the orval client and the `Dockerfile` were
all removed, along with the `fastapi`, `uvicorn` and `prometheus_client`
dependencies. **7,355 lines deleted, 1,197 added.**

Reddit was already gone and needed nothing.

The gates are green: ruff check and format clean, mypy clean on 54 files, 402
backend tests pass (398 with the wiki unreachable), and the frontend's 126 tests
across 4 files pass with typecheck, lint and build clean.

## Context

Two requests: remove the Reddit connection altogether, and remove the API if there is
no practical reason to keep it.

**Reddit is already gone.** There is nothing to remove:

- Zero `reddit` references anywhere outside `.kilo/plans/`.
- No `app/services/news_scraper.py`, no `scripts/news_scraper.py`.
- No `REDDIT_*` variable in `.env.example`.
- The `news_articles` table was dropped in `alembic/versions/005_drop_news_articles.py`;
  no news model remains in `app/models/`.
- The News *page* was removed too. There are seven pages: Calculators, Home, Items,
  Meta, Minerals, Search, World. The README describes no News page.

The only Reddit residue is in three stale plan files, which now say so.

**The API is fully redundant.** Every one of these was checked, not assumed:

| Check | Finding |
| --- | --- |
| Deployment | None. No `render.yaml`, no deploy-api workflow (only `ci.yml` and `static.yml`), no Render integration. The systemd units run `scripts/refresh_site.sh`, not uvicorn. |
| Frontend consumer | None. No file imports `@/api/pick`; the generated `pick.ts` is imported by nothing. `snapshot.ts` uses the raw `request()` client for `/api/v1/export/snapshot`, guarded by `if (!API_BASE_URL)` with a fallback to the committed `snapshot.json`. |
| The export pipeline | **Bypasses the API entirely.** `scripts/export_snapshot.py` imports `build_snapshot` from `app.services.snapshot` directly. `app/api/export.py` is a thin HTTP wrapper over the same function. |
| Search | Equivalent, not richer. `app/api/search.py` is `ILIKE %q%` over name/description/data. `snapshotCache.searchItems` does the same, including `JSON.stringify(i.data)` for the location filter. |
| Pagination | On both sides. API uses `page`/`size`; the frontend slices with `PAGE_SIZE = 50`. |
| Meta | Snapshot-backed. `MetaPage.tsx` reads `snapshot.meta.*`. |
| Layer imports | Nothing outside `app/api/` and `app/main.py` imports the API layer. |

The user chose **remove the API entirely**.

## What gets removed

### Backend

| Path | Lines | Why it goes |
| --- | --- | --- |
| `app/api/` (6 files) | ~430 | The routers. Nothing outside `app/main.py` imports them. |
| `app/main.py` | ~60 | The ASGI app. Only `docker-compose.yml`'s `api` service and the CI `generated-files` job reference it. |
| `app/monitoring.py` | ~130 | Prometheus metrics and the health router, mounted only by `app/main.py`. |
| `app/schemas/` (3 files) | ~120 | Pydantic response models, imported only by `app/api/`. |
| `app/utils/__init__.py` | ~30 | `get_client_ip` and `rate_limit_key` take a FastAPI `Request`. **Verified unused**: nothing imports `from app.utils import ...`. `app/utils/mw_api.py` — which IS used — does not import the package `__init__`. |
| `tests/test_api.py` | 288 | The only test that builds the ASGI app (`httpx.ASGITransport(app=app)`). |
| `openapi.json` | ~2900 | The published spec. Cannot be regenerated without the app. |
| `Dockerfile` | 24 | Exists only to run the API (`CMD uvicorn app.main:app`). Nothing else builds it — `docker-compose.yml` is its only referrer. |
| `docker-compose.yml`'s `api` service | 20 | Runs uvicorn against `app.main:app`. |

### Frontend

| Path | Why it goes |
| --- | --- |
| `frontend/src/api/pick.ts` | The orval client. Generated from `openapi.json`, imported by nothing. |
| `frontend/src/api/client.ts` | The raw `request()` helper. Imported by exactly one file: `snapshot.ts:1`. |
| `frontend/orval.config.mjs` | The orval config. Its only output was `pick.ts`. |

### Dependencies

Drop from `requirements.txt`: `fastapi`, `uvicorn[standard]`, `prometheus_client`.

**Keep `pydantic` and `pydantic-settings`** — `app/config.py` uses
`pydantic_settings.BaseSettings` and `app/config.py` is needed by `app/database.py`,
`app/utils/mw_api.py` and `tests/conftest.py`. `pydantic` itself is a transitive
dependency of `pydantic-settings`.

**Keep `httpx`** — `app/utils/mw_api.py` uses it for the wiki client, and
`tests/conftest.py` uses it for the live-wiki check.

**Keep `jsonschema`** — `tests/test_snapshot_contract.py` validates the committed
snapshot against `snapshot.schema.json`, which stays.

## What stays, and why

The scraper, the database models, the reconciler, the taxonomy, the exporter and the
frontend are the product. None of them touch the API layer:

- `app/services/scraper.py`, `reconcile.py`, `enrichment.py`, `snapshot.py`,
  `seed_formulas.py` — unchanged.
- `app/models/` — unchanged. The schema is the database's, not the API's.
- `app/config.py`, `app/database.py`, `app/taxonomy.py`, `app/logging_config.py`,
  `app/utils/mw_api.py` — unchanged.
- `app/api/export.py` was the only API module with real logic, and that logic is
  `build_snapshot`, which lives in `app/services/snapshot.py` and stays.
- `scripts/export_snapshot.py` — unchanged. It never went through the API.
- `scripts/refresh_site.sh` — unchanged. It starts only the `db` compose service.
- `snapshot.schema.json` and the generated `frontend/src/lib/snapshot.types.ts` —
  unchanged. The snapshot contract is independent of the API.

## The changes

### 1. Delete the API layer

```bash
git rm -r app/api app/schemas
git rm app/main.py app/monitoring.py app/utils/__init__.py
git rm tests/test_api.py openapi.json Dockerfile
```

### 2. Trim `docker-compose.yml`

Remove the `api` service. The `db` service and the `pick_db_data` volume stay —
the scraper needs the database.

### 3. Trim `requirements.txt`

Remove `fastapi==0.162.0`, `uvicorn[standard]==0.54.0`, `prometheus_client==0.26.0`.
`pyproject.toml` reads its dependency list from `requirements.txt`, so it follows
automatically.

### 4. Reduce the CI `generated-files` job

It currently regenerates `openapi.json` from `app.main.app`, runs
`npm run generate:api`, and diffs three files. After the removal there is one
generated file left: `frontend/src/lib/snapshot.types.ts`.

The job becomes:

```yaml
  generated-files:
    # The frontend's snapshot types are generated from snapshot.schema.json and
    # committed. Nothing else keeps them honest, so a change to the schema can
    # leave the committed types describing a shape that no longer exists. This
    # job regenerates them and fails if they differ.
    needs: [lint, typecheck]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - name: Install frontend dependencies
        run: npm ci --legacy-peer-deps
        working-directory: frontend
      - name: Regenerate the snapshot types
        run: npm run generate:snapshot-types
        working-directory: frontend
      - name: Check that the generated files are unchanged
        run: git diff --exit-code frontend/src/lib/snapshot.types.ts
```

The Python setup step goes too — the job no longer needs Python.

### 5. Remove the frontend's API path

`frontend/src/lib/snapshot.ts` is the only consumer. It currently:

```ts
import request from "@/api/client";
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
```

and in `fetch()`:

```ts
try {
  if (!API_BASE_URL) {
    throw new Error("No API base URL configured");
  }
  const apiData = await request<RawSnapshot>({ url: "/api/v1/export/snapshot", method: "GET" });
  data = normalizeSnapshot(apiData);
} catch {
  const response = await fetch(`${import.meta.env.BASE_URL}snapshot.json`);
  ...
}
```

With no API to talk to, the `try` branch goes and the static fetch becomes the only
path. `RawSnapshot` is then only used by the static fetch — check whether it is
still needed or collapses into the response type.

**Also remove** `frontend/src/api/` entirely, the `generate:api` script from
`frontend/package.json`, and the `orval` devDependency (and `@tanstack/react-query`
if nothing else uses it — check `frontend/src/lib/queryClient.ts` and `App.tsx`,
which wrap the app in a `QueryClientProvider` that nothing consumes).

`frontend/src/lib/snapshot.ts` also caches to IndexedDB via `lib/idb.ts`; that stays.

### 6. Remove `VITE_API_BASE_URL` from the deploy workflow

`.github/workflows/static.yml` passes it as a build env var. With the API gone there
is nothing to point it at, so the env block and its comment go.

### 7. Update the docs

- **`README.md`** — remove "Exposes a REST API (FastAPI) for items, formulas, search
  and metadata" from "What it does", and the FastAPI entry in the tech stack.
- **`SETUP.md`** — remove the API section: the `curl http://localhost:8000/...`
  example, the "API Client Generation" section, `npm run generate:api`, and the
  `app/api/` line in the tree listing. Keep the `VITE_API_BASE_URL` mention removed.
- **`AGENTS.md`** — this is the big one. It documents the API surface, the doubled
  health path, `openapi.json`/`pick.ts` as generated files, the `generated-files` job,
  and `app/monitoring.py`/`app/logging_config.py`. All of that must go, and the
  "Backend — FastAPI" description must become "Backend — scraper and exporter".
- **`.kilo/command/check.md`** — the generated-files check loses `openapi.json` and
  `frontend/src/api/pick.ts` from its diff list.
- **`.kilo/command/generate-api.md`** — this command generates the API client from
  the spec. With both gone it has no purpose; delete the file, or repoint it at the
  snapshot types if that is worth a separate command.

### 8. The stale plan files

The three that discuss a live API or a live Reddit integration are already marked
superseded (`1793066334615-remaining-work-plan.md`, `r-statistical-tiers-implementation.md`).
Update the wording of those markers to say the API and the Reddit scraper have been
removed, so nobody revives them.

## Validation

Every gate CI runs, plus the ones it will no longer run:

```bash
# Backend gates
.venv/bin/ruff check app scrapers scripts tests
.venv/bin/ruff format --check app scrapers scripts tests
.venv/bin/mypy app/ scrapers/ scripts/

# Backend tests (needs the test database)
docker compose up -d db
docker exec pick-db psql -U pick -d pick -c "CREATE DATABASE pick_test;"
TEST_DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick_test" \
DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick" \
  .venv/bin/python -m pytest -q

# Frontend gates
cd frontend
npm run typecheck
npm run test
npm run lint
npm run build

# The one remaining generated file
npm run generate:snapshot-types
cd .. && git diff --exit-code frontend/src/lib/snapshot.types.ts
```

Then confirm the site still works: `npm run build` must produce a `dist/` that
serves the snapshot, and the deployed site must still render all seven pages. The
scraper must still run: `scripts/refresh_site.sh --dry-run` must complete without
touching the removed modules.

**The test count will drop.** `tests/test_api.py` is 288 lines and holds a
meaningful number of tests; the remaining suite will be smaller. Record the new
number so `AGENTS.md` states the truth.

### What actually happened

- Backend tests: **412 → 402**. The 10 tests in `test_api.py` went with it. The
  "no database" figure is **335 passed, 67 errors** (was 77 — the 10 API errors
  went too). `AGENTS.md` now says 67 and drops `test_api` from the list.
- mypy: 66 → 54 source files.
- `ruff format --check`: 110 → 97 files.
- npm audit: **18 vulnerabilities (10 critical) → 7 high**. Removing `orval` and
  `@tanstack/react-query` took the critical ones with it.

Two things the plan did not anticipate:

- **`triggered_full_scrape` was a lie in the frontend.** `snapshot.ts` had a
  hand-written `GameVersionResponse` with a `triggered_full_scrape` field, but
  `snapshot.schema.json` explicitly excludes it — the generated `GameVersion` has
  only `version` and `detected_at`. So `MetaPage` rendered "Full scrape triggered:
  0" unconditionally. Unifying the hand-written type with the generated one
  removed the field and the dead row.
- **`@tanstack/react-query` had no consumer.** It existed only for the orval
  client's `QueryClientProvider` wrapper; no `useQuery` or `useMutation` was
  called anywhere. With the client gone, the provider, `queryClient.ts` and the
  dependency all went.


## Risks

| Risk | Mitigation |
| --- | --- |
| Something still imports the API | `grep` for `app.api`, `app.main`, `app.schemas`, `app.monitoring`, and `from app.utils import` before deleting. The only referrers found are `app/main.py` itself, `docker-compose.yml`, `tests/test_api.py`, and the CI job. `mypy` and the test suite catch the rest. |
| `pydantic` removed by mistake | It is a transitive dependency of `pydantic-settings`, and `app/config.py` needs `pydantic_settings.BaseSettings`. Verify the import still resolves before committing. |
| The frontend loses its API fetch path but keeps the `try`/`catch` shape | Remove the branch, not just the import — a silent `catch` that swallows a failed static fetch would leave the page empty with no error. |
| The `QueryClientProvider` in `App.tsx` becomes obviously dead | Remove it with `queryClient.ts` and `@tanstack/react-query`, or keep it and say why. Leaving an unexplained provider is the kind of thing that confuses the next reader. |
| `openapi.json` was a published contract | It is not published anywhere — no domain, no deployment, no documentation pointing consumers at it. Confirm no one is reading it before deleting. |
| The plan's claim that "nothing imports the API" is wrong | It was checked with grep against the current tree. Re-check after deleting, with mypy and the test suite as the backstop. |

## Out of scope

- The four open GitHub issues (#1, #6, #7, #8). Those are separate work; #1 and #6
  need their fix shape agreed first.
- The custom domain, dark mode, and a Reddit/News feature. Reddit is removed, not
  rebuilt — if News is wanted later it starts from nothing.
- Keeping a hand-maintained `openapi.json`. Nothing would regenerate it, so it
  would drift — exactly the failure the `generated-files` job exists to prevent.
- The `Render` deployment and the `render.yaml` the old plan wanted. There is no
  longer an application to deploy.
