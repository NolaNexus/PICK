# PICK — Prospecting Information & Community Kit

A self-updating backend for Prospecting! game resources, tools, and calculators.
Built as a fast, navigable replacement for the official Miraheze wiki.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| API Framework | FastAPI |
| Database | PostgreSQL (async SQLAlchemy) |
| Deployment | Render |
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
├── requirements.txt     # Python dependencies
├── pyproject.toml       # Project metadata
├── render.yaml          # Render deployment config
└── README.md            # This file
```

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 16+

### Local Development

```bash
# Clone the repo
git clone <repository-url>
cd PICK

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy env config
cp .env.example .env
# Edit .env with your DATABASE_URL and other settings

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Visit the API docs
open http://localhost:8000/docs
```

### Running the Scraper

```bash
python -m scripts.scraper
```

### Seeding Formulas

```bash
python -m scripts.seed_formulas
```

## Roadmap

See `ROADMAP.md` for the detailed implementation phases:

1. **Phase 1**: Foundation (models, DB schema, CI) — [in progress]
2. **Phase 2**: Core scraper + change detection
3. **Phase 3**: REST API + calculators
4. **Phase 4**: News aggregation (Reddit)
5. **Phase 5**: CI/CD + Render deployment
6. **Phase 6**: Validation & iteration

## License

MIT License