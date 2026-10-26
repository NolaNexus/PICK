# PICK — Prospecting Information & Community Kit

PICK is a passion project built by and for players of [Prospecting!](https://www.roblox.com/games/1298271121136),
a Roblox simulator where you sift sand to find minerals and build your fortune.

It exists to give back to the community and help players understand more of the game's mechanics and systems —
items, minerals, pans, shovels, relics, runes, formulas, calculators, and community news — in one fast,
searchable place.

## PICK is not the wiki

PICK does not replace the official [Prospecting! Wiki](https://prospecting.miraheze.org/). It scrapes the wiki and
depends entirely on the work of its maintainers and contributors. If something is missing or wrong on the wiki,
it will be missing or wrong here too.

Think of PICK as a companion layer on top of the wiki: structured data, calculators, and search that make the
wiki's information easier to use while you play.

## Who it's for

- **New players** learning how luck, stats, and equipment work
- **Miners and collectors** looking up item values, spawn locations, and crafting recipes
- **Theorycrafters** running odds and optimization calculators
- **Anyone** who wants quick answers without digging through wiki pages

## What it does

- Scrapes the official Prospecting! wiki on a schedule and keeps a local copy of pages, items, and formulas
- Exposes a REST API (FastAPI) for items, formulas, calculators, news, and metadata
- Powers calculators for modifier odds, expected value, best pan, museum optimization, and time-to-goal
- Aggregates community news from Reddit
- Serves a React + Vite frontend on GitHub Pages

## Tech stack

- Python 3.11+, FastAPI, PostgreSQL (async SQLAlchemy)
- React + TypeScript + Vite frontend
- Docker Compose for local development
- GitHub Actions for CI/CD and frontend deployment

## Local development

```bash
git clone <repository-url>
cd PICK
cp .env.example .env
docker compose up --build
open http://localhost:8000/docs
```

Run the wiki scraper:

```bash
docker compose exec api python -m scripts.scraper
```

## Deployment

The frontend deploys to GitHub Pages via GitHub Actions. Set the `VITE_API_BASE_URL` repository secret to your
backend's public URL (or a local tunnel such as ngrok/cloudflared), then push to `main`.

The backend and database run locally via Docker Compose and are not exposed to the public internet by default.

## Roadmap

See `ROADMAP.md` for the implementation phases.

## License

MIT License
