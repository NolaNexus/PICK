# Setup Guide - PICK Project

## Prerequisites

- GitHub account
- PostgreSQL (for local testing)

## Step 1: Clone Repository

```bash
git clone https://github.com/NolaNexus/PICK.git
cd PICK
```

## Step 2: Configure the Webhook Secret (optional)

The wiki can notify PICK when a page changes so only that page is re-scraped.
Without a secret the endpoint is open; with one, requests must carry it.

```bash
WEBHOOK_SECRET=your_webhook_secret_here
```

## Step 3: Local Development

### Python dependencies

`requirements.txt` is all you need for the standard setup:

```bash
pip install -r requirements.txt
```

### Optional: R statistical bridge

The R statistical bridge (`app/services/r_stats.py`, via `rpy2`) is **not installed
by default** — neither the Docker image nor CI build it. `rpy2` has no binary wheel
and must be compiled against a local R installation, and the R path is being rebuilt
together with the calculators. Until then the API uses the pure-Python
approximations and the `tests/test_r_stats.py` R-backed tests skip automatically.

To enable it locally, install R first and then the extra requirements:

```bash
# Debian/Ubuntu
sudo apt-get install -y r-base
pip install -r requirements-r.txt
```

With R + `rpy2` present, `R_AVAILABLE` becomes `True` and the R-backed tests and
calculator paths run instead of skipping.

### Start Backend + Database

```bash
# Start all services
cd PICK
docker compose up --build -d

# Database migrations
./.venv/bin/python -m alembic upgrade head

# Run wiki scraper (test)
./.venv/bin/python -m scripts.scraper
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

- `scripts.export_snapshot`: Export data for frontend
  - Creates `frontend/public/snapshot.json`
  - Called by CI/CD during deployment

- `scripts.seed_formulas`: Seed formula data

#### Environment Variables (`.env`)

```bash
# MediaWiki API endpoint for Prospecting! Wiki
MEDIAWIKI_API_URL=https://prospecting.miraheze.org/w/api.php

# User-Agent sent to the wiki API
USER_AGENT=PICK/1.0 (Prospecting Information & Community Kit)

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
├── requirements-r.txt     # Optional R statistical bridge (rpy2, numpy) — not built by default
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