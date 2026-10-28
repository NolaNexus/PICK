# Remaining Work Plan — PICK Project Completion

**Status:** LARGELY SUPERSEDED — check each item against the current tree before
acting. Verified at `5f9ca0d`:

- **Reddit News (Priority 1, Phase 4)** — the scraper was **deleted**, not merely
  awaiting credentials. There is no `app/services/news_scraper.py`, no
  `scripts/news_scraper.py`, and no `REDDIT_*` variable in `.env.example`. This is
  greenfield work now, not a credentials task.
- **CI enhancements (T2.1)** — done. `ci.yml` has the Python 3.11/3.12 matrix and
  `mypy app/ scrapers/ scripts/`.
- **Backend calculators (T4.1)** — the backend was deleted in `5af31c5`; there are no
  Python calculator functions left to test. The frontend maths is the only
  implementation, and it is covered by `frontend/src/lib/calculators.test.ts`.
- **`render.yaml` (T2.2) and the deploy-api workflow (T2.3)** — moot. There is no
  longer an application to deploy: `app/api/`, `app/main.py`, `app/schemas/`,
  `app/monitoring.py`, `openapi.json` and the orval client were all removed. The
  project is a scraper plus a static site, and the site needs no server.
- **Phase 2 polish (Priority 3)** — the soft-delete behaviour, the single-source
  `TRACKED_PAGES`, the taxonomy fold and the `SNAPSHOT_SCHEMA_VERSION` bump are all
  done; see `.kilo/plans/1793173475507-core-simplification.md`.
- **OpenAPI docs (Priority 5)** — moot. There is no OpenAPI spec and no API. The
  published file's contract is `snapshot.schema.json`, which is generated from and
  validated against the exporter.
- **Calculator test coverage (T4.1)** — the frontend now has 126 tests across 4
  files.

## Current State Summary

| Phase | Status | Notes |
|-------|--------|-------|
| **Phase 2** — Scraper & Data Pipeline | ✅ Complete | 23 parsers, 933 items, idempotent runs |
| **Phase 3** — REST API + Calculators | ✅ Complete | All endpoints implemented |
| **Phase 4** — Reddit News | ⚠️ Partial | Code implemented; **Reddit credentials needed** |
| **Phase 5** — CI/CD + Render | 🟡 Partial | CI exists; Render config & deploy missing |
| **Phase 6** — Frontend | ✅ Complete | 6 pages implemented, deployed |
| **LSP Support** | ✅ Complete | Pyright config + VS Code settings |

---

## Priority 1: Reddit News Scraper (Phase 4 Blocking)

**Problem**: `app/services/news_scraper.py` has OAuth2 client credentials flow, but `.env` lacks:
- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`

Public Reddit API returns 403 (blocked). OAuth2 required.

### Tasks (Manual)
- **T1.1**: Create Reddit "Script App" at <https://developers.reddit.com/>
  - Name: `PICK News Scraper`
  - Type: Script App
  - Redirect URI: `http://localhost:8080`
- **T1.2**: Extract Client ID & Client Secret from app dashboard
- **T1.3**: Add to `.env`:
  ```bash
  REDDIT_CLIENT_ID=your_client_id_here
  REDDIT_CLIENT_SECRET=your_client_secret_here
  ```
- **T1.4**: Add to GitHub Actions secrets (for CI/CD)
- **T1.5**: Verify: `.venv/bin/python -m scripts.news_scraper` fetches posts

### Required Actions (Manual)

The core code is implemented and working. You just need:

1. **Create Reddit App** at <https://developers.reddit.com/>
   - Click "Create App" → Choose "Script App" 
   - Fill name/description, redirect URI = `http://localhost:8080`
   - Accept Developer Terms

2. **Copy credentials**:
   - Client ID (visible on app page)
   - Client Secret (click "Edit" → show secret)

3. **Add to `.env`**:
   ```bash
   REDDIT_CLIENT_ID=your_client_id_here
   REDDIT_CLIENT_SECRET=your_client_secret_here
   ```

4. **Add to GitHub Actions secrets** (for CI/CD): `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`

**Current status:** Code is complete, just needs credentials to work.

## Priority 2: CI/CD Enhancements (Phase 5)

### 2.1 Add Python matrix & typecheck to CI
- [ ] **T2.1**: Update `.github/workflows/ci.yml`:
  - Add Python 3.12 matrix (if compatible)
  - Add `mypy` typecheck step (install mypy, run on `app/`, `scrapers/`, `scripts/`)
  - Add `ruff format --check` step

### 2.2 Create Render deployment config
- [~] **T2.2**: MOOT — there is no application to deploy. The API was removed
  (see the status note above). The scraper runs locally via a systemd timer
  (`deploy/systemd/`) and the site is published by the `static.yml` workflow.

### 2.3 Add API deploy workflow
- [~] **T2.3**: MOOT — same reason as T2.2. There is no API and no
  `deploy-api.yml`.

---

## Priority 3: Phase 2 Polish (Optional, Low Priority)

| Issue | Fix |
|-------|-----|
| Stale items never deleted | Add soft-delete logic in `run_daily_scrape`: mark items not in current scrape as `is_active=false` |
| `TRACKED_PAGES` duplicated | Single source of truth in `scrapers/registry.py`; import in `scraper.py` |
| Changelog double-fetch | Skip Changelog in `_run_scrape` if already checked in full scrape |
| Parser `id` field unused | Remove or use for dedup instead of `slug` only |

---

## Priority 4: Test Coverage

### 4.1 Calculator Unit Tests
- [ ] **T4.1**: Test core math in `app/services/calculators.py`:
  - `shakes_per_second`
  - `digs_per_pan`
  - `pans_per_hour`
  - `calculate_ev`
  - `calculate_ttg`
  - `modifier_distribution`
  - Museum functions

### 4.2 API Integration Tests
- [ ] **T4.2**: Add integration tests using `httpx.AsyncClient` + test DB
- Test all endpoints: items, formulas, calculators, news, meta, search

### 4.3 Coverage Target
- [ ] **T4.3**: Ensure ≥80% coverage on new code (calculators + API)

---

## Priority 5: Documentation

- [~] **T5.1**: MOOT — there is no OpenAPI spec and no Pydantic response models.
- [~] **T5.2**: MOOT — there are no endpoints to group.
- [~] **T5.3**: MOOT — `openapi.json` no longer exists. The published file's
  contract is `snapshot.schema.json`, and `tests/test_snapshot_contract.py`
  validates the committed snapshot against it.

---

## Dependencies & Risks

| Dependency | Risk |
|------------|------|
| Reddit OAuth2 credentials | Only if the News feature is rebuilt from scratch — the scraper was deleted. |
| PostgreSQL 16 in CI | Already working in daily/weekly scrape workflows |

---

## Validation Checklist

Most of these criteria no longer apply — they were written when there was a Reddit
scraper, a Render deployment, an OpenAPI spec and a backend calculator. The ones
that still stand:

| Criterion | How Verified |
|-----------|--------------|
| CI pipeline passes (lint + typecheck + test) | GitHub Actions green |
| Calculator tests added, coverage ≥80% | `cd frontend && npm run test` — 126 tests across 4 files |

---

## Recommended Execution Order

1. **CI enhancements** — done.
2. **Tests** — done for the frontend. The backend has no calculators left to test.
3. **Phase 2 polish** — done.
4. **Documentation** — the OpenAPI items are moot; the contract is
   `snapshot.schema.json`.

---

## Out of Scope (Future)
- GraphQL API
- WebSocket real-time updates
- User accounts / saved builds
- Dark mode toggle
- PWA / offline support
- Internationalization