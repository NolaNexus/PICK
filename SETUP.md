# Setup Guide - PICK Project

## Prerequisites

- GitHub account
- Reddit developer account (for news scraper)
- PostgreSQL (for local testing)

## Step 1: Clone Repository

```bash
git clone https://github.com/NolaNexus/PICK.git
cd PICK
```

## Step 2: Configure Reddit News Scraper

### Phase 4 - Reddit News Scraper

**Status:** Code implemented, needs credentials

To enable Reddit news fetching, you need to create a Reddit "Script App":

1. **Create Reddit App**
   - Go to <https://developers.reddit.com/>
   - Accept Developer Terms
   - Click "Create App" → Choose "Script App"
   - Fill in:
     - Name: `PICK News Scraper`
     - Description: `News aggregator for r/Prospecting`
     - Redirect URI: `http://localhost:8080`

2. **Get Credentials**
   - Client ID: Copy from app dashboard
   - Client Secret: Click "Edit" → reveal

3. **Add to `.env`**
   ```bash
   REDDIT_CLIENT_ID=your_client_id_here
   REDDIT_CLIENT_SECRET=your_client_secret_here
   ```

5. **Optional:** Webhook secret for security
   ```bash
   WEBHOOK_SECRET=your_webhook_secret_here
   ```

6. **Test locally**:
   ```bash
   # Start PostgreSQL locally
   docker compose up -d

   # Run news scraper
   .venv/bin/python -m scripts.news_scraper
   ```

**Expected output**: Fetched X Reddit posts, inserted into database

## Step 3: Local Development

### Start Backend + Database

```bash
# Start all services
cd PICK
docker compose up --build -d

# Database migrations
./.venv/bin/python -m alembic upgrade head

# Run wiki scraper (test)
./.venv/bin/python -m scripts.scraper

# Run news scraper (if credentials configured)
./.venv/bin/python -m scripts.news_scraper
```

### Start Frontend

```bash
cd frontend
npm run dev
```

## Step 4: CI/CD Setup

GitHub Actions are already configured:

### CI Pipeline
- Runs on every push/PR
- Lints backend (ruff)
- Type checks backend (mypy)
- Runs tests (with PostgreSQL)
- Builds frontend
- Lints frontend (ESLint)
- Type checks frontend

### Deployment
- **Frontend**: Deploys to GitHub Pages on push to `master` via `static.yml`, using the
  official Pages Actions flow (`configure-pages` → `upload-pages-artifact` → `deploy-pages`)
- **Backend**: Deploys to Render (requires Render API key and app ID)
- **Scrapers**: Daily/Weekly scheduled runs via GitHub Actions

#### Required repository settings

1. **Settings → Pages → Build and deployment → Source → GitHub Actions**
   The `static.yml` workflow publishes through the Pages API and will not work while
   Pages is set to serve a branch.
2. **Settings → Actions → General → Workflow permissions → Read and write**
   The scrape workflows commit the refreshed `snapshot.json` back to `master`, which
   is what redeploys the site after a data refresh.
3. Optional secret `VITE_API_BASE_URL` — leave unset for a fully static site. When set,
   the app prefers the live API and falls back to the committed `snapshot.json`.

## Development Scripts

### Available Scripts

#### Backend Scripts

- `scripts.scraper`: Wiki scraper main entry point
  - Arguments: `--full` for complete rebuild
  - Settings: Database URL, MediaWiki API URL, etc.

- `scripts.news_scraper`: Reddit news scraper
  - Requires Reddit OAuth2 credentials
  - Fetches from `r/Prospecting` (configurable)
  - Deduplicates by Reddit post ID

- `scripts.export_snapshot`: Export data for frontend
  - Creates `frontend/public/snapshot.json`
  - Called by CI/CD during deployment

- `scripts.seed_formulas`: Seed formula data

#### Environment Variables (`.env`)

```bash
# MediaWiki API endpoint for Prospecting! Wiki
MEDIAWIKI_API_URL=https://prospecting.miraheze.org/w/api.php

# Reddit news scraping
REDDIT_USER_AGENT=PICK/1.0 (Prospecting Information & Community Kit)
REDDIT_SUBREDDIT=Prospecting
REDDIT_CLIENT_ID=your_reddit_app_client_id
REDDIT_CLIENT_SECRET=your_reddit_app_client_secret

# Application settings
APP_NAME=PICK
APP_VERSION=0.1.0
DEBUG=false
DATABASE_URL=postgresql+asyncpg://pick:pick@localhost:5432/pick

# CORS allowed origins (comma-separated; use "*" for dev, list domains for prod)
# CORS_ORIGINS=https://pick.example.com,https://www.pick.example.com

# Webhook secret for security (optional)
# WEBHOOK_SECRET=your_webhook_secret_here

### Frontend Scripts

#### Package.json Scripts

- `npm run dev`: Vite dev server
- `npm run build`: Production build
- `npm run lint`: ESLint
- `npm run typecheck`: TypeScript type checking
- `npm run generate:api`: Generate API client from OpenAPI spec

## Development Workflow

### 1. Make Changes
- Modify backend code in `app/`
- Modify frontend code in `frontend/src/`
- Update parsers in `scrapers/`

### 2. Test
- Backend: `ruff check app/` + `mypy app/` + `pytest tests/`
- Frontend: `npm run lint` + `npm run typecheck`

### 3. Run End-to-End Tests

```bash
# Test wiki scraper
./.venv/bin/python -m scripts.scraper

# Test news scraper (if credentials configured)
./.venv/bin/python -m scripts.news_scraper

# Check data
curl http://localhost:8000/api/v1/items?limit=10
```

### 4. Deploy

```bash
# Build and deploy frontend
cd frontend
npm run build
# Push to master (triggers GitHub Pages deploy via static.yml)

# Deploy backend to Render (if Render API key configured)
# GitHub Actions `deploy-api.yml` handles this
```

```bash
# Project Structure

```
├── app/                    # FastAPI backend
│   ├── api/              # API endpoints
│   ├── services/         # Business logic
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   └── database.py       # Database setup
├── scrapers/              # Wiki page parsers
├── scripts/               # CLI tools
├── tests/                 # Test suite
├── .github/              # GitHub Actions workflows
├── frontend/             # React + Vite frontend
│   ├── src/             # Source code
│   ├── public/          # Static files
│   └── dist/            # Build output (gitignored)
├── requirements.txt       # Python dependencies
├── pyproject.toml         # Python project config
├── README.md              # Project overview
├── ROADMAP.md             # Implementation phases
└── .kilo/                # Kilo planning system
```

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Reinitialize database
./.venv/bin/python -m alembic upgrade head
```

### Reddit News Scraper Issues

```bash
# Check .env for Reddit credentials
cat .env

# Test OAuth2 flow manually
./.venv/bin/python -c "
from app.config import settings
print('Client ID:', settings.reddit_client_id)
print('Client Secret:', '✓ configured' if settings.reddit_client_secret else '❌ missing')
"
```

### Frontend Issues

```bash
# Clear cache and rebuild
cd frontend
rm -rf node_modules dist
npm install --legacy-peer-deps
npm run build
```

### API Client Generation

```bash
# Regenerate API client from OpenAPI spec
cd frontend
npm run generate:api
```

## Support

For issues, please check:
- <https://github.com/NolaNexus/PICK/issues>
- GitHub Discussions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/ -v` and `ruff check`
5. Open a pull request

## License

MIT License - See LICENSE file for details