# Phase 5 Plan — Verify Render Deployment & CI/CD

## Goal
Take the existing `render.yaml` and GitHub Actions configs from "exists on paper" to "verified working in production."

## Current State (Already Done)
- `render.yaml`: Web service + 2 cron jobs + PostgreSQL
- `.github/workflows/ci.yml`: Lint + test with PostgreSQL
- `.github/workflows/daily-scrape.yml`: Daily cron scrape
- `.github/workflows/weekly-full-scrape.yml`: Weekly full scrape
- `.github/workflows/deploy.yml`: Render deploy hook trigger

## Required Actions

### T1 — Push to Main & Trigger CI
- Push current branch to `main`
- Verify GitHub Actions CI passes (lint + test)
- Fix any failures

### T2 — Create Render Resources
1. **Create Render account** (if not exists)
2. **Connect GitHub repo** to Render
3. **Create `pick-db` PostgreSQL** (free plan, Frankfurt)
4. **Create `pick-api` web service** from `render.yaml`
5. **Create `pick-daily-scrape` cron job** from `render.yaml`
6. **Create `pick-weekly-full-scrape` cron job** from `render.yaml`

### T3 — Configure Render Environment Variables
In Render dashboard, set for **all services**:
| Variable | Value |
|----------|-------|
| `MEDIAWIKI_API_URL` | `https://prospecting.miraheze.org/w/api.php` |
| `REDDIT_USER_AGENT` | `PICK/1.0 (Prospecting Information & Community Kit)` |
| `DATABASE_URL` | Auto-linked from `pick-db` |
| `WEBHOOK_SECRET` | Generate random string (for webhook verification) |
| `REDDIT_CLIENT_ID` | *(leave empty - Phase 4 deferred)* |
| `REDDIT_CLIENT_SECRET` | *(leave empty - Phase 4 deferred)* |

### T4 — Configure GitHub Secrets
In GitHub repo Settings → Secrets → Actions:
| Secret | Value |
|--------|-------|
| `RENDER_DEPLOY_HOOK` | Render deploy hook URL for `pick-api` |

### T5 — Verify End-to-End
1. **Trigger CI** — Push a commit, verify GitHub Actions passes
2. **Trigger Deploy** — Push to main, verify Render deploy hook fires, service deploys
3. **Verify Health** — `GET https://pick-api.onrender.com/api/v1/health/health` returns 200
4. **Verify API** — `GET https://pick-api.onrender.com/api/v1/meta` returns DB stats
5. **Trigger Daily Scrape** — Manually run `pick-daily-scrape` cron, verify logs show success
6. **Verify DB** — Check `pick-db` has tables populated after scrape

### T6 — Clean Up render.yaml (Since Phase 4 Deferred)
Remove unused Reddit vars from render.yaml:
- Remove `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` from web service
- Remove `REDDIT_USER_AGENT` from cron jobs (only needed for news scraper)

## Validation Criteria
- [ ] GitHub Actions CI passes on push to main
- [ ] Render web service deploys and responds to health checks
- [ ] API endpoints return data (`/meta`, `/items`, `/calculators/*`)
- [ ] Daily cron job runs successfully on schedule
- [ ] Weekly full-scrape cron job runs successfully
- [ ] GitHub Actions deploy workflow triggers Render deploy

## Risks / Notes
- **Free tier limits**: Render free tier spins down after 15 min inactivity — first request after idle may timeout (30s). Health checks keep it warm.
- **Cron timezone**: Render cron uses UTC — `0 3 * * *` = 3 AM UTC
- **Database migrations**: `alembic upgrade head` runs on every build — ensure idempotent
- **Reddit vars**: Keep in `.env.example` for local dev, remove from Render since deferred

## Out of Scope
- Custom domain / TLS
- Monitoring/alerting beyond Render built-in
- Load testing
- Phase 4 news scraping (blocked)