# Plan — Work on Open Issues

## Context (verified)
- `master` at `4438b51`, pushed. Theme WIP files stay uncommitted and out of scope.
- **NPC duplicates:** `scrapers/npcs.py:145` slugs NPCs by name only. The same name in several regions (e.g. Merchant x8) collides. `tests/test_npcs.py:55` already expects duplicates across regions, so my `scrape_page` first-wins dedupe contradicts the test's intent.
- **Formulas empty:** no workflow runs `scripts/seed_formulas.py`, so the published snapshot has `formulas: 0`.
- **Regression I introduced:** `scripts/seed_formulas.py:7` imports `engine` and `async_session_factory` from `app.database` at import time. Both are `None` since the lazy `get_engine()` change, so the script crashes at `engine.begin()`. Other scripts (`scraper.py`, `news_scraper.py`, `export_snapshot.py`) call `await get_engine()` first and are fine.
- **Double deploy:** `render.yaml` sets `autoDeploy: true` on `pick-api`, and `deploy-api.yml` also deploys on push.
- **Ungated deploy:** `deploy-api.yml` runs on push to `master` without waiting for `ci.yml`, and uses `johnbatista/render-deploy@v0.4.1`.
- **Unsafe test fixture:** `tests/test_api.py:22` defaults `TEST_DATABASE_URL` to the app DB `pick` and runs `drop_all`.

## Decisions (resolved)
1. NPCs are distinct items per region. Slug = `slugify(f"{region}-{name}")`. Regionless NPCs use prefix `global`.
2. Deploy runs only after CI passes on `master`, via `workflow_run`. The third-party action is replaced by a direct Render API call.
3. `render.yaml` sets `autoDeploy: false`. The GitHub workflow is the only API deploy path.
4. Tests run only against a DB explicitly named by `TEST_DATABASE_URL` whose name ends in `_test`. No default.
5. Formula seeding runs in `daily-scrape.yml` before `export_snapshot`.

## Ordered Tasks

### 1. NPC region-prefixed slugs
- `scrapers/npcs.py`: set `slug` and `id` to the prefixed slug. Keep `name` unchanged.
- `tests/test_npcs.py`: make slug uniqueness strict. Replace the "allow duplicates" comment. Add a test that `Merchant` appears under at least two regions with distinct slugs.
- Add a regression test asserting the NPC fixture yields zero duplicate slugs.
- Keep the `scrape_page` dedupe as a safety net, but it should never fire for NPCs now.
- Old unprefixed NPC rows are soft-deactivated by the existing `scrape_page` logic on the next full scrape. Verify with an integration test.
- Grep `frontend/src` and `app/` for hard-coded NPC slugs or `/items/<npc>` links and update them.

### 2. Fix `scripts/seed_formulas.py`
- Replace the module-level imports with `import app.database as app_database`.
- Call `engine = await app_database.get_engine()` and use `app_database.async_session_factory()`, matching `scraper.py`.
- Verify: run against `pick_snapshot`, expect `Seeded N formulas`. Run a second time, expect no new rows.

### 3. Add formula seeding to the daily pipeline
- `.github/workflows/daily-scrape.yml`: add `python -m scripts.seed_formulas` before the `export_snapshot` step.
- Run order: scrape, news, seed, export.

### 4. Gate and harden API deploy
- `.github/workflows/deploy-api.yml`:
  - Trigger: `workflow_run` on workflow `CI`, types `completed`, branch `master`, and only when `conclusion == success`. Keep `workflow_dispatch`.
  - Replace the third-party action with a `curl` `POST` to the Render deploys endpoint using `RENDER_API_KEY` and `RENDER_APP_ID`. **Before writing it, confirm the exact endpoint and auth header against the Render API docs.**
  - Remove the notify steps that print hard-coded URLs, or keep only a verified health check.
- `render.yaml`: set `autoDeploy: false` on `pick-api`.

### 5. Test DB isolation
- `tests/test_api.py` and `tests/test_integration.py`: read `TEST_DATABASE_URL` with no default. Raise if it is unset, or if the database name does not end in `_test`. Check for any other fixtures that read `DATABASE_URL` the same way.
- `.github/workflows/ci.yml` test job: create a `pick_test` database in the Postgres service and set `TEST_DATABASE_URL` to it. Confirm nothing else in the job depends on `DATABASE_URL`.

### 6. Validation
- Backend: `pytest` (against `pick_test`), `ruff check`, `ruff format --check`, `mypy app scrapers scripts`.
- Migrations: fresh DB through `004`.
- Scraper: after the NPC change, re-run `scripts.scraper --full` on a fresh DB. Expect zero "Duplicate slug" warnings.
- Snapshot: re-export. Expect `formulas > 0` after seeding, and NPC items with region prefixes.
- Frontend: `npm run typecheck`, `npm run lint`, `npm run build`. Regenerate the API client only if `openapi.json` changes.
- Workflows: validate all changed YAML files parse.

### 7. Commit and push (only after user confirms)
- Commit backend and workflow changes separately from the theme WIP.
- Push to `origin/master`. Check CI and Pages runs with `gh run list` once `gh` is authenticated.

## Risks
- **Slug change breaks links:** any external `/items/<npc-slug>` link stops resolving. Mitigation: grep in task 1. The old rows are deactivated, so 404s are expected.
- **Render API shape unverified:** task 4 requires checking the endpoint before writing it.
- **`workflow_run` needs the default-branch workflow file:** the deploy workflow must be on `master` before it fires.

## Out of Scope
- Theme WIP files (`index.css`, `footer.tsx`, `badge`, `button`, `card`, `lib/theme.ts`, `assets/icons/`, `package-lock.json`).
- Reddit credentials, which are manual. News stays at `0` until they are set.
- `gh auth login`, which is a user action.
- Tightening the blanket mypy `disable_error_code` list in `pyproject.toml`.
- Product features, dark mode, PWA, i18n, GraphQL, WebSockets.

## Validation Done When
- All gates in task 6 pass.
- A full scrape on a fresh DB produces zero duplicate-slug warnings.
- `formulas > 0` in the exported snapshot.
- `deploy-api.yml` runs only after a successful `CI` on `master`, and `render.yaml` has `autoDeploy: false`.
- `pytest` refuses to run against any DB whose name does not end in `_test`.
