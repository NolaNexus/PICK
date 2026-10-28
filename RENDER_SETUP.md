# Render Deployment Configuration

This file deploys the PICK backend API to [Render](https://render.com) with scheduled scrapers.

A ready-to-use Render Blueprint lives at [`render.yaml`](render.yaml). It defines the
web service, PostgreSQL database, and daily/weekly cron jobs. In the Render
dashboard choose **New → Blueprint** and point it at this repository.

`DATABASE_URL` supplied by Render (for example `postgres://...`) is normalized to the
`postgresql+asyncpg://` driver automatically by the app and Alembic.

## Services

### web (FastAPI)
- Build: Docker (`Dockerfile` — installs `requirements.txt`; the optional R bridge is not built)
- Start: `python -m app.main`
- Environment variables from `.env` (or Render secrets)
- Health checks at `/api/v1/health/health/ready`

### postgres
- Official PostgreSQL 16 image
- Persistent volume for data
- Database: `pick`

### redis (optional)
- For future caching/session storage

## Cron Jobs

### Daily Scrape (6-hour interval)
- Schedule: `*/6 * * * *`
- Triggers `python -m scripts.scraper`
- Updates database with latest wiki data

### Weekly Full Scrape
- Schedule: `0 4 * * 0` (Sunday 04:00 UTC)
- Triggers `python -m scripts.scraper --full`
- Complete wiki rebuild

## Environment Variables

### Required
- `DATABASE_URL`: PostgreSQL connection string
- `MEDIAWIKI_API_URL`: MediaWiki API endpoint
- `USER_AGENT`: User-Agent sent to the wiki API
- `VITE_API_BASE_URL`: Frontend API base URL (for snapshot export)
- `WEBHOOK_SECRET`: Webhook signature verification secret (optional)

### Optional
- `DEBUG`: Enable debug mode (false)
- `APP_NAME`, `APP_VERSION`: Application metadata
- `CORS_ORIGINS`: CORS allowed origins (default: `["*"]`)

## Deployment

```bash
# Deploy from GitHub Actions or manually:
render deploy

# Set secrets in Render dashboard:
# - VITE_API_BASE_URL (from GitHub secret)
# - WEBHOOK_SECRET (optional)
```

## Monitoring

- Logs: Render logs dashboard
- Health: `/api/v1/health/health/ready`, `/api/v1/health/health/live`
- Metrics: `/api/v1/meta` (scrape stats)
- Backups: Configure PostgreSQL automated backups

## CI/CD Integration

GitHub Actions `deploy-api.yml` deploys to Render on push to `master`.

Required GitHub Actions secrets:
- `RENDER_API_KEY`
- `RENDER_APP_ID`

```yaml
deploy:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Deploy to Render
      uses: johnbatista/render-deploy@v0.4.1
      with:
        render_api_key: ${{ secrets.RENDER_API_KEY }}
        render_app_id: ${{ secrets.RENDER_APP_ID }}
```

## Scaling

- Web service: Auto-scales based on CPU/memory
- Database: Use Render's managed PostgreSQL (scalable)
- CDN: Frontend served from GitHub Pages