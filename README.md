# PICK — Prospecting Information & Community Kit

**A community-built companion for Prospecting!** — items, minerals, pans, shovels, relics, runes, formulas, calculators, and community news in one fast, searchable place.

🔗 **[Live Site →](https://nolanexus.github.io/PICK---Prospecting-Information---Community-Kit/)** · [Report an Issue](https://github.com/NolaNexus/PICK---Prospecting-Information---Community-Kit/issues)

---

## What is PICK?

PICK is a community-built companion for players of [Prospecting!](https://www.roblox.com/games/1298271121136), a Roblox simulator where you sift sand to find minerals and build your fortune.

It exists to give back to the community and help players understand more of the game's mechanics. 
## PICK is not the wiki

PICK does not replace the official [Prospecting! Wiki](https://prospecting.miraheze.org/). It scrapes the wiki and depends entirely on the work of its maintainers and contributors. If something is missing or wrong on the wiki, it will be missing or wrong here too.

Think of PICK as a companion layer on top of the wiki: structured data, calculators, and search that make the wiki's information easier to use while you play.

## Who it's for

- **New players** learning how luck, stats, and equipment work
- **Miners and collectors** looking up item values, locations, and crafting recipes
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
- R for statistical analysis (rpy2 bridge)
- React + TypeScript + Vite frontend
- Docker Compose for local development
- GitHub Actions for CI/CD and frontend deployment

## Local development

Want to run PICK yourself or contribute? You'll need Python 3.11+ and PostgreSQL 16+.

```bash
git clone https://github.com/NolaNexus/PICK---Prospecting-Information---Community-Kit.git
cd PICK---Prospecting-Information---Community-Kit
cp .env.example .env
docker compose up --build
open http://localhost:8000/docs
```

Run the wiki scraper:

```bash
docker compose exec api python -m scripts.scraper
```
## License

MIT License
