# Phase 2 — Core Scraper & Data Pipeline 🔄 IN PROGRESS
**Goal**: Scrape wiki pages, detect changes, upsert into PostgreSQL.

### Tasks
- [x] Implement `utils/mw_api.py` — MediaWiki API client with rate-limit handling
- [x] Create `scrapers/registry.py` — PARSERS dict mapping page titles → parser functions
- [x] Create stub parsers for all tracked pages
- [ ] **Implement actual parsers** using mwparserfromhell for wikitext template parsing:
  - [ ] pans.py — {{Pan row ...}}
  - [ ] shovels.py — {{Shovel row ...}}
  - [ ] minerals.py — {{Mineral row ...}}
  - [ ] equipment.py — {{Equipment row ...}} + tabber
  - [ ] modifiers.py — == Modifier Name == sections
  - [ ] locations.py — location tables
  - [ ] enchanting.py — <tabber> Pans/Shovels tables
  - [ ] trinkets.py — wikitable
  - [ ] formulas.py — Stat Systems Guide tables
  - [ ] blueprints.py — Blueprint tabber
  - [ ] relics.py
  - [ ] runes.py
- [x] Implement `services/scraper.py` — `run_daily_scrape()` orchestrator
- [x] Implement change detection: hash-based diff (only scrape if wikitext changed)
- [x] Write `scripts/scraper.py` — CLI entry point
- [ ] Test scraper: run locally, verify items upsert into DB

### Exit Criteria
- `python -m scripts.scraper` runs and fetches 20+ tracked pages
- Re-running on unchanged wiki produces 0 new DB writes
- At least 3 parser types produce valid JSON in DB