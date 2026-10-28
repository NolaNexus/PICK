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

`requirements.txt` holds the runtime dependencies and `requirements-dev.txt` holds the
test and lint tools. For development you want both:

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

If you only want to run the app, `requirements.txt` on its own is enough.

### A note on the old R bridge

There is no R dependency any more. `app/services/r_stats.py`, the `R/` scripts and
`requirements-r.txt` were removed, and with them the endpoints that could only ever
return an empty result.

There is no backend calculator either. The calculators live in the site, in
`frontend/src/lib/calculators.ts` and `frontend/src/lib/museum.ts`, and they run in the
browser from the published snapshot.

### There is no API

There is no HTTP server in this project. `app/api/`, `app/main.py`, `app/schemas/`,
`app/monitoring.py` and `openapi.json` were removed: nothing deployed the API, no
frontend code called it, and the exporter writes the snapshot directly rather than
through a route. The scraper produces `frontend/public/snapshot.json`; the site
reads that file. If you need a programmatic interface, the dataset is
`snapshot.json` and its contract is `snapshot.schema.json`.

### Start the Database

```bash
cd PICK
docker compose up -d db

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

## Refreshing the data

GitHub-hosted runners cannot scrape the wiki: Miraheze answers every request from
them with `403 Forbidden`, which is why the scheduled scrape workflows were removed.
The scrape runs on the machine that holds this checkout, which can reach the wiki.

`scripts/refresh_site.sh` performs the whole cycle: start Postgres, migrate, scrape,
seed formulas, export `frontend/public/snapshot.json`, and commit and push it when it
changed. It is **fail-closed** — a scrape that reaches no page, an export that would
erase the catalogue, or a checkout with uncommitted changes, aborts before anything is
committed.

The checkout has to be clean when it runs, because it publishes from that checkout.
A stray edit would otherwise fail the update step with a message about the network,
or be left behind by the commit. Commit or stash before the timer fires.

### Install the schedule (once)

1. **Deploy key.** Create an SSH key with no passphrase, add the public half to
   *Settings → Deploy keys* with write access, and confirm that `git push` works from
   this machine without prompting.
2. **Environment.** The script reads the repository `.env` — it parses it rather than
   sourcing it, because `USER_AGENT` holds spaces and parentheses. Add `NTFY_TOPIC`
   there (see `.env.example`) to receive a push when a run fails or the data goes stale.
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
```

There is no HTTP server, so `CORS_ORIGINS` is not read by anything. It is a leftover
from the API and can be deleted.

### Frontend Scripts

#### Package.json Scripts

- `npm run dev`: Vite dev server
- `npm run build`: Production build
- `npm run lint`: ESLint
- `npm run typecheck`: TypeScript type checking
- `npm run generate:snapshot-types`: Generate the frontend's types from `snapshot.schema.json`

## Development Workflow

### 1. Make Changes
- Modify backend code in `app/`
- Modify frontend code in `frontend/src/`
- Update parsers in `scrapers/`

### 2. Test
- Backend: `ruff check app scrapers scripts tests` + `ruff format --check app scrapers scripts tests` + `mypy app/ scrapers/ scripts/` + `pytest`
- Frontend: `npm run lint` + `npm run typecheck` + `npm run build`

The backend commands need a test database, and the scopes above are the ones CI
uses. `.kilo/command/check.md` has the whole sequence with the environment
variables spelled out.

### 3. Run End-to-End Tests

```bash
# Test wiki scraper
./.venv/bin/python -m scripts.scraper

# Check the exported data
./.venv/bin/python -c "import json; d=json.load(open('frontend/public/snapshot.json')); print(len(d['items']), 'items')"
```

### 4. Deploy

```bash
# Build and deploy frontend
cd frontend
npm run build
# Push to master (triggers GitHub Pages deploy via static.yml)

# The backend runs locally through Docker Compose; it is not deployed.
```

### Project Structure

```text
├── app/                    # Scraper and exporter
│   ├── services/         # Business logic
│   ├── models/           # SQLAlchemy models
│   ├── utils/            # MediaWiki client
│   ├── taxonomy.py       # Type taxonomy loader
│   └── database.py       # Database setup
├── alembic/               # Migrations (001-007)
│   └── versions/
├── scrapers/              # Wiki page parsers
├── scripts/               # CLI tools
├── tests/                 # Test suite
├── deploy/systemd/        # Refresh-job units
├── docs/agent-instructions/  # Detailed guidance for agents
├── .github/              # GitHub Actions workflows
├── frontend/             # React + Vite frontend
│   ├── src/             # Source code
│   ├── public/          # Static files, including the committed snapshot.json
│   └── dist/            # Build output (gitignored)
├── requirements.txt       # Python runtime dependencies
├── requirements-dev.txt   # Python test and lint tools
├── pyproject.toml         # Python project config
├── snapshot.schema.json   # The published file's contract
├── README.md              # Project overview
├── ROADMAP.md             # What shipped and what is open
└── .kilo/                # Kilo planning system and slash commands
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
npm install
npm run build
```

### Snapshot Types Generation

```bash
# Regenerate the frontend's types from snapshot.schema.json
cd frontend
npm run generate:snapshot-types
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