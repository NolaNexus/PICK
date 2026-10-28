# Setup Guide - PICK Project

## Prerequisites

- GitHub account
- PostgreSQL (for local testing)

## Step 1: Clone Repository

```bash
git clone https://github.com/NolaNexus/PICK.git
cd PICK
```

## Step 2: Configure the Environment

Copy `.env.example` to `.env` and fill in the values you need:

```bash
cp .env.example .env
```

The file is read by `python-dotenv` and by `scripts/refresh_site.sh`, which parses it
line by line rather than sourcing it: `USER_AGENT` contains spaces and parentheses,
so it is not shell syntax.

## Step 3: Local Development

### Python dependencies

`requirements.txt` is all you need for the standard setup:

```bash
pip install -r requirements.txt
```

### A note on the old R bridge

There is no R dependency any more. `app/services/r_stats.py`, the `R/` scripts and
`requirements-r.txt` were removed; the calculators' Python implementations live in
`app/services/stats.py` and always run.

The endpoints that could only ever return an empty result were removed along with it,
rather than left answering with nothing. The six calculators that do work are
`/calculators/ev`, `/ttg`, `/modifier-odds`, `/best-pan`, `/museum` and
`/calculators/stats/modifier-distribution`.

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
- **Data**: refreshed by the local job described in [Refreshing the data](#refreshing-the-data)
- **Backend**: runs locally through Docker Compose; the published site does not use it

#### Required repository settings

1. **Settings → Pages → Build and deployment → Source → GitHub Actions**
   The `static.yml` workflow publishes through the Pages API and will not work while
   Pages is set to serve a branch.
2. Optional secret `VITE_API_BASE_URL` — leave unset for a fully static site. When set,
   the app prefers the live API and falls back to the committed `snapshot.json`.

## Refreshing the data

GitHub-hosted runners cannot scrape the wiki: Miraheze answers every request from
them with `403 Forbidden`, which is why the scheduled scrape workflows were removed.
The scrape runs on the machine that holds this checkout, which can reach the wiki.

`scripts/refresh_site.sh` performs the whole cycle: start Postgres, migrate, scrape,
seed formulas, export `frontend/public/snapshot.json`, and commit and push it when it
changed. It is **fail-closed** — a scrape that reaches no page, or an export that
would erase the catalogue, aborts before anything is committed.

### Install the schedule (once)

1. **Deploy key.** Create an SSH key with no passphrase, add the public half to
   *Settings → Deploy keys* with write access, and confirm that `git push` works from
   this machine without prompting.
2. **Environment.** The script sources the repository `.env`. Add `NTFY_TOPIC` there
   (see `.env.example`) to receive a push when a run fails or the data goes stale.
3. **Install the units.**
   ```bash
   mkdir -p ~/.config/systemd/user
   cp deploy/systemd/pick-refresh.service ~/.config/systemd/user/
   cp deploy/systemd/pick-refresh-full.service ~/.config/systemd/user/
   cp deploy/systemd/pick-refresh.timer ~/.config/systemd/user/
   cp deploy/systemd/pick-refresh-full.timer ~/.config/systemd/user/
   systemctl --user daemon-reload
   systemctl --user enable --now pick-refresh.timer pick-refresh-full.timer
   loginctl enable-linger "$USER"
   ```
   `enable-linger` is what lets the timer fire while you are not logged in.
4. **Check it.**
   ```bash
   systemctl --user list-timers
   journalctl --user -u pick-refresh -f
   ```

Run it by hand at any time with `bash scripts/refresh_site.sh`, adding `--full` for a
complete rebuild. The units use `%h/Desktop/PICK`; if the checkout moves, update them.

## Development Scripts

### Available Scripts

#### Backend Scripts

- `scripts.scraper`: Wiki scraper main entry point
  - Arguments: `--full` for complete rebuild
  - Settings: Database URL, MediaWiki API URL, etc.

- `scripts.export_snapshot`: Export data for frontend
  - Creates `frontend/public/snapshot.json`
  - Refuses to write a snapshot that would erase the catalogue (`--force` overrides)
  - Called by `scripts/refresh_site.sh`

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

# The backend runs locally through Docker Compose; it is not deployed.
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