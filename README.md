# PICK — Prospecting Information & Community Kit

**A community-built companion for Prospecting!** — items, minerals, pans, shovels, relics, runes, formulas, calculators, and community news in one fast, searchable place.

🔗 **[Live Site →](https://nolanexus.github.io/PICK/)** · [Report an Issue](https://github.com/NolaNexus/PICK/issues) · [Render Setup →](RENDER_SETUP.md)

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
- React + TypeScript + Vite frontend
- Optional R + rpy2 statistical bridge for the calculators (not built by default; the API falls back to pure-Python approximations — see SETUP.md)
- Docker Compose for local development
- GitHub Actions for CI/CD and frontend deployment

## Item identity

The same game object can appear on several wiki pages. PICK stores it once:

- Slugs are namespaced by type (`relic-cosmic-resonator`, `npc-rubble-creek-john`), so an NPC and a quest that share a name stay distinct.
- Traveling Merchant stock merges into the item as `data.merchant`. Stock, price, and currency rotate every daily spawn, so these are last-seen values (`data.merchant.last_seen`).
- Excavation drops keep their own per-site rows (`excavation_reward`) with drop chance and a `data.item_slug` pointing at the item.
- Quests link to the NPC that gives them via `data.npc_slug`.
- Items removed from a page are soft-deleted (`is_active = false`), never hard-deleted.

## Local development

Want to run PICK yourself or contribute? You'll need Python 3.11+ and PostgreSQL 16+.

```bash
git clone https://github.com/NolaNexus/PICK.git
cd PICK
cp .env.example .env
docker compose up --build
open http://localhost:8000/docs
```

Run the wiki scraper:

```bash
docker compose exec api python -m scripts.scraper
```

## Frontend development

The frontend is a Vite + React app in `frontend/`. It runs standalone against the
committed snapshot, so no API is needed for UI work.

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

To regenerate the static dataset the site is built from:

```bash
# with a local Postgres running and DATABASE_URL pointing at it
python -m scripts.seed_formulas
python -m scripts.export_snapshot --output frontend/public/snapshot.json
```

The export only rewrites `frontend/public/snapshot.json` when the rendered data
actually changed, so a scrape that finds no wiki changes produces no diff.

## Deployment

The site is deployed as a static GitHub Pages site from `frontend/dist`:

- `.github/workflows/static.yml` builds the frontend and publishes it with the
  official GitHub Pages Actions flow.
- The repository must have **Settings → Pages → Build and deployment → Source**
  set to **GitHub Actions**.
- The published site reads `frontend/public/snapshot.json`, which the
  `daily-scrape` and `weekly-full-scrape` workflows refresh on a schedule and
  commit back to `master`, which redeploys the site.
- Set a `VITE_API_BASE_URL` repository secret to point the app at a live API
  instead; without it the site stays fully static.

Deep links work through `frontend/public/404.html`, which stashes the requested
route and hands it back to the app after redirecting to the entry point.

The optional backend (FastAPI + Postgres) is deployed separately; see
[RENDER_SETUP.md](RENDER_SETUP.md).

## License

MIT License

