# PICK — Prospecting Information & Community Kit

**A community-built companion for Prospecting!** — items, minerals, pans, shovels, relics, runes, formulas, and calculators in one fast, searchable place.

🔗 **[Live Site →](https://nolanexus.github.io/PICK/)** · [Report an Issue](https://github.com/NolaNexus/PICK/issues)

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
- Powers calculators for modifier odds, expected value, best pan, museum optimization, and time-to-goal, computed in the browser
- Serves a React + Vite frontend on GitHub Pages

## Tech stack

- Python 3.11+, PostgreSQL (async SQLAlchemy)
- React + TypeScript + Vite frontend
- The calculators are TypeScript in the browser (`frontend/src/lib/calculators.ts`); no R, no rpy2, no server-side maths
- Docker Compose for local development
- GitHub Actions for CI/CD and frontend deployment

## How the data is kept honest

The published site reads one file, `frontend/public/snapshot.json`, and nothing else.
Everything around it is arranged so that a mistake is caught by a build rather than
by a player.

**The database enforces its own rules.** `items.type` is a PostgreSQL enum, so a row
with a type nobody declared cannot be written. Three check constraints hold the rest
in place: a name is never empty, the payload is always a JSON object, and a slug is
always the type prefix plus the name — which is what keeps slugs unique and
deterministic whatever order the pages were scraped in.

**The taxonomy lives in the database.** The `taxonomy` table holds every type with
its area, group, label and display order, so the list of types and the column that
holds one cannot drift apart. The site reads the taxonomy out of the snapshot, and
the client can name every type, including the ones that describe part of an item.

**The published file has a contract.** `snapshot.schema.json` describes the snapshot:
every key, every type, and no undeclared fields. The committed file is validated
against it in CI, a deliberately broken snapshot is checked to be rejected, and the
frontend's TypeScript types are generated from the schema rather than written by
hand.

**Only the data that changed is published.** The export compares the whole snapshot
against the file, ignoring a short list of things that always differ — scrape
timestamps, the merchant's rotating stock. Everything else counts, including the
taxonomy, so a change to it is published rather than silently dropped.

## Item identity

The same game object can appear on several wiki pages. PICK stores it once:

- Slugs are namespaced by type (`relic-cosmic-resonator`, `npc-rubble-creek-john`), so an NPC and a quest that share a name stay distinct. The database enforces this: a slug that does not follow its type is rejected.
- Traveling Merchant stock merges into the item as `data.merchant`. Stock, price, and currency rotate every daily spawn, so these are last-seen values (`data.merchant.last_seen`).
- A row that only describes part of an item — the museum row of a mineral, the blueprint of a piece of equipment, the drop table of an excavation site — is folded into that item and retired. These are the *fragment types*: `museum_ore`, `blueprint`, `mutation_catalyst`, `excavation_reward`, `museum_display`, `museum_info`, `merchant_item`, `consumable`. A fragment whose item is missing from the wiki stays active, so its data is not lost.
- Quests link to the NPC that gives them via `data.npc_slug`.
- Items removed from a page are soft-deleted (`is_active = false`), never hard-deleted.

## Local development

Want to run PICK yourself or contribute? You'll need Python 3.11+ and PostgreSQL 16+.

```bash
git clone https://github.com/NolaNexus/PICK.git
cd PICK
cp .env.example .env
docker compose up -d db
```

Run the wiki scraper:

```bash
.venv/bin/python -m scripts.scraper
```

For a host-side virtualenv, create `.venv` **after** the checkout is in its final
location: a virtualenv hard-codes its own path, so moving or renaming the
directory breaks every script in `.venv/bin`. If that happens, delete `.venv` and
recreate it (`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`).
The systemd units for the refresh job also hard-code the path; update them if the
checkout moves.

## Frontend development

The frontend is a Vite + React app in `frontend/`. It runs standalone against the
committed snapshot, so no backend is needed for UI work.

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
- The published site reads `frontend/public/snapshot.json`.

The snapshot is refreshed by a job on the maintainer's machine, which is the
only place that can reach the wiki: Miraheze answers GitHub-hosted runners with
`403 Forbidden`, so scraping from Actions never worked. The job runs on a
systemd timer, scrapes into the local database, exports the snapshot, and
commits it, which redeploys the site. See
[SETUP.md](SETUP.md#refreshing-the-data) for the install steps.

Deep links work through `frontend/public/404.html`, which stashes the requested
route and hands it back to the app after redirecting to the entry point.

The published site is fully static: it reads the committed `snapshot.json` and needs
no backend at runtime. The scraper needs Postgres, which runs locally through Docker
Compose.

## License

MIT License

