# PICK — Prospecting Information & Community Kit

A self-updating backend for Prospecting! game resources, tools, and calculators.
Built as a fast, navigable replacement for the official Miraheze wiki.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| API Framework | FastAPI |
| Database | PostgreSQL (async SQLAlchemy) |
| Deployment | Local (Docker Compose) backend + GitHub Pages frontend |
| CI/CD | GitHub Actions |

## Project Structure

```
PICK/
├── app/                 # FastAPI application
│   ├── main.py          # FastAPI app factory
│   ├── config.py        # Pydantic settings
│   ├── database.py      # Async SQLAlchemy engine/session
│   ├── models/          # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── wiki_page.py
│   │   ├── item.py
│   │   ├── formula.py
│   │   ├── news.py
│   │   └── scraper_run.py
│   ├── schemas/         # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── item.py
│   │   ├── formula.py
│   │   ├── news.py
│   │   └── calculator.py
│   ├── api/             # FastAPI route handlers
│   │   ├── __init__.py
│   │   ├── items.py
│   │   ├── formulas.py
│   │   ├── calculators.py
│   │   ├── news.py
│   │   └── meta.py
│   ├── services/        # Business logic
│   │   ├── __init__.py
│   │   ├── scraper.py   # Wiki scraping orchestration
│   │   ├── formulas.py  # Formula implementations
│   │   └── calculators.py
│   └── utils/           # Utilities
│       ├── __init__.py
│       └── mw_api.py    # MediaWiki API client
├── scrapers/            # Wiki page parsers (one per page)
│   ├── __init__.py
│   ├── registry.py      # PARSERS dict + TRACKED_PAGES list
│   ├── pans.py
│   ├── shovels.py
│   ├── minerals.py
│   ├── equipment.py
│   ├── modifiers.py
│   ├── locations.py
│   ├── enchanting.py
│   ├── trinkets.py
│   ├── formulas.py
│   ├── blueprints.py
│   ├── relics.py
│   └── runes.py
├── scripts/             # CLI entry points
│   ├── scraper.py       # Daily wiki scraper
│   ├── news_scraper.py  # Reddit news fetcher
│   └── seed_formulas.py # One-time formula seeding
├── tests/               # Unit/integration tests
├── alembic/             # Database migrations
├── .github/workflows/   # CI/CD pipelines
├── .github/workflows/   # CI/CD pipelines (incl. frontend Pages deploy)
├── requirements.txt     # Python dependencies
├── pyproject.toml       # Project metadata
├── docker-compose.yml   # Local PostgreSQL 16 + FastAPI backend
├── Dockerfile           # Backend container image
└── README.md            # This file
```

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 16+

### Local Development (Docker Compose)

Database (PostgreSQL 16) and the FastAPI backend run locally via Docker Compose — free, no cloud required.

```bash
# Clone the repo
git clone <repository-url>
cd PICK

# Copy env config
cp .env.example .env
# Edit .env if needed (DATABASE_URL defaults to the compose service)

# Start database + API (runs migrations on startup)
docker compose up --build

# Visit the API docs
open http://localhost:8000/docs
```

Stop with `docker compose down`.

### Running the Scraper

```bash
docker compose exec api python -m scripts.scraper
```

### Seeding Formulas

```bash
docker compose exec api python -m scripts.seed_formulas
```

## Deployment

### Frontend — GitHub Pages (free, constant uptime)

Only the frontend needs to be publicly reachable at all times. It deploys to GitHub
Pages via GitHub Actions using `.github/workflows/deploy-frontend.yml`:

1. Enable GitHub Pages in the repo settings (Settings → Pages → Build and deployment →
   Source: GitHub Actions).
2. Add repository secret `VITE_API_BASE_URL` = your backend's public URL (or a tunnel
   URL such as ngrok/cloudflare if the backend runs locally).
3. Optionally add secret `VITE_BASE_URL` if serving from a subpath
   (e.g. `/PICK/`); defaults to `/`.
4. Push to `main` — the workflow builds `frontend/dist` and deploys to Pages.

GitHub Pages is free; no credit card required.

### Backend + Database — Local

Run on your own machine with `docker compose up`. Not exposed to the public internet by
default; expose it via a tunnel if the frontend needs to reach it remotely.

## Roadmap

See `ROADMAP.md` for the detailed implementation phases:

1. **Phase 1**: Foundation (models, DB schema, CI) — [in progress]
2. **Phase 2**: Core scraper + change detection
3. **Phase 3**: REST API + calculators
4. **Phase 4**: News aggregation (Reddit)
5. **Phase 5**: CI/CD + local deploy + GitHub Pages frontend
6. **Phase 6**: Validation & iteration

## License

MIT License