# Phase 5 Plan — Verify Local Deploy + GitHub Pages Frontend (free)

## Goal
Move off Render/Vercel to a free setup: database + backend hosted locally via Docker
Compose, frontend on GitHub Pages (free, constant uptime).

## Current State (Already Done)
- `docker-compose.yml`: Local PostgreSQL 16 + FastAPI backend
- `Dockerfile`: Backend container image
- `.env.example`: Local DATABASE_URL + VITE_API_BASE_URL
- `.github/workflows/deploy-frontend.yml`: GitHub Actions build + deploy to Pages
- `frontend/public/404.html`: SPA fallback for React Router routes
- `frontend/vite.config.ts`: dev proxy → localhost:8000; `base` configurable via `VITE_BASE_URL`
- `.github/workflows/ci.yml`: Lint + test with PostgreSQL
- `.github/workflows/daily-scrape.yml`: Daily cron scrape
- `.github/workflows/weekly-full-scrape.yml`: Weekly full scrape

## Required Actions

### T1 — Push to Main & Trigger CI
- Push current branch to `main`
- Verify GitHub Actions CI passes (lint + test)
- Fix any failures

### T2 — Verify Local Deploy (docker-compose)
- `docker compose up --build` starts db + api and runs migrations
- `GET http://localhost:8000/api/v1/health/health` returns 200
- `GET http://localhost:8000/api/v1/meta` returns DB stats

### T3 — Enable GitHub Pages Frontend (free)
1. **Enable GitHub Pages** in repo settings: Settings → Pages → Build and deployment →
   Source: GitHub Actions.
2. **Add repository secret** `VITE_API_BASE_URL` = your backend's public URL (or a tunnel
   URL such as ngrok/cloudflare if backend runs locally).
3. **Optionally add secret** `VITE_BASE_URL` if serving from a subpath (e.g. `/PICK/`);
   defaults to `/`.
4. **Push to `main`** — the workflow builds `frontend/dist` and deploys to Pages.

### T4 — Verify Frontend
- Visit the GitHub Pages URL (Settings → Pages)
- Confirm API calls reach the backend (set `VITE_API_BASE_URL` accordingly)
- Confirm React Router routes work (404.html fallback)

### T5 — Scrapers (local or GitHub Actions)
- Run scrapers locally: `docker compose exec api python -m scripts.scraper`
- Or keep GitHub Actions scheduled scrapers (they run in GH Actions, free)

## Cost Summary (keep it free)
| Component | Where | Cost |
|-----------|-------|------|
| PostgreSQL 16 | Local (docker-compose) | $0 |
| FastAPI backend | Local (docker-compose) | $0 |
| Frontend | GitHub Pages (free) | $0 |
| Scrapers | Local / GitHub Actions | $0 |

## Validation Criteria
- [ ] GitHub Actions CI passes on push to main
- [ ] `docker compose up` starts db + api, migrations run, health check returns 200
- [ ] Frontend deploys to GitHub Pages and loads
- [ ] Frontend API calls reach the backend (via `VITE_API_BASE_URL`)
- [ ] Daily scraper runs successfully
- [ ] Weekly full-scrape runs successfully

## Risks / Notes
- **GitHub Pages serves static sites only**; it cannot run the FastAPI backend or
  PostgreSQL — those stay local.
- **Frontend ↔ backend**: Pages cannot reach `localhost`. Set `VITE_API_BASE_URL`
  to a publicly reachable backend URL, or expose the local backend via a tunnel
  (ngrok / cloudflared).
- **Local host must stay on** for the backend to be reachable; if the machine sleeps,
  the API is down. For 24/7 uptime without paying, run the backend on an always-on
  home server or Raspberry Pi.
- **SPA routing**: `frontend/public/404.html` redirects unmatched routes to
  `index.html` so React Router handles them client-side.
- **Cron timezone**: GitHub Actions cron uses UTC — `0 3 * * *` = 3 AM UTC daily.

## Out of Scope
- Custom domain / TLS beyond GitHub Pages automatic
- Monitoring/alerting
- Load testing
