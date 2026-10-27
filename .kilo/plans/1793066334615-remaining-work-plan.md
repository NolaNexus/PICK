# Remaining Work Plan — PICK Project Completion

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
- [ ] **T2.2**: Create `render.yaml` at repo root (referenced in Phase 3-5 plan):
  - Web service (FastAPI)
  - PostgreSQL database
  - Daily cron job (scraper)
  - Weekly cron job (full scraper)
  - Environment variables from GitHub secrets

### 2.3 Add API deploy workflow
- [ ] **T2.3**: Create `.github/workflows/deploy-api.yml`:
  - Trigger on push to master/main
  - Deploy to Render via API or GitHub integration

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

- [ ] **T5.1**: Add descriptions/examples to Pydantic models (OpenAPI)
- [ ] **T5.2**: Tag/group endpoints logically in OpenAPI
- [ ] **T5.3**: Verify `openapi.json` generation works for external consumers

---

## Dependencies & Risks

| Dependency | Risk |
|------------|------|
| Reddit OAuth2 credentials | Must be created manually at developers.reddit.com |
| GitHub Actions secrets | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `VITE_API_BASE_URL` |
| PostgreSQL 16 in CI | Already working in daily/weekly scrape workflows |
| Render account | Needed for `render.yaml` deployment |

---

## Validation Checklist

| Criterion | How Verified |
|-----------|--------------|
| Reddit news fetches & stores posts | Run `scripts.news_scraper`, check `News` table |
| CI pipeline passes (lint + typecheck + test) | GitHub Actions green |
| Render deployment works | Deploy to Render staging |
| Calculator tests added, coverage ≥80% | `pytest --cov=app/services/calculators` |
| OpenAPI docs enhanced | Browse `/docs` and `/redoc` |

---

## Recommended Execution Order

1. **Reddit credentials** (blocks Phase 4) — manual step at developers.reddit.com
2. **CI enhancements** (typecheck, matrix) — code change to `.github/workflows/ci.yml`
3. **Render config** — create `render.yaml`
4. **Tests** — add calculator unit tests + API integration tests
5. **Phase 2 polish** — if time permits
6. **Documentation** — OpenAPI enhancements

---

## Out of Scope (Future)
- GraphQL API
- WebSocket real-time updates
- User accounts / saved builds
- Dark mode toggle
- PWA / offline support
- Internationalization