# Phase 2 — Core Scraper & Data Pipeline ✅ COMPLETE
**Goal**: Scrape wiki pages, detect changes, upsert into PostgreSQL. All exit criteria met (see Phase 2 completion plan).

### Tasks
- [x] Implement `utils/mw_api.py` — MediaWiki API client with rate-limit handling
- [x] Create `scrapers/registry.py` — PARSERS dict mapping page titles → parser functions
- [x] Create stub parsers for all tracked pages
- [x] **Implement actual parsers** using mwparserfromhell for wikitext template parsing:
  - [x] pans.py — {{Pan row ...}}
  - [x] shovels.py — {{Shovel row ...}}
  - [x] minerals.py — {{Mineral row ...}}
  - [x] equipment.py — {{Equipment row ...}} + tabber
  - [x] modifiers.py — == Modifier Name == sections
  - [x] locations.py — location tables
  - [x] enchanting.py — <tabber> Pans/Shovels tables
  - [x] trinkets.py — wikitable
  - [x] formulas.py — Stat Systems Guide tables
  - [x] blueprints.py — Blueprint tabber
  - [x] relics.py
  - [x] runes.py
- [x] Implement `services/scraper.py` — `run_daily_scrape()` orchestrator
- [x] Implement change detection: hash-based diff (only scrape if wikitext changed)
- [x] Write `scripts/scraper.py` — CLI entry point
- [x] Test scraper: run locally, verify items upsert into DB

### Exit Criteria ✅ All met
- `python -m scripts.scraper` runs and fetches 20+ tracked pages (26 scraped, 0 errors)
- Re-running on unchanged wiki produces 0 new DB writes (pages_changed == 0, items count unchanged)
- At least 3 parser types produce valid JSON in DB (23 types, 933 items, 0 empty data rows)