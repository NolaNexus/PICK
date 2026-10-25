# Phase 2 Completion Plan — Wiki Scraper End-to-End Validation

## Context / Current State

PICK is a FastAPI + PostgreSQL backend that scrapes the Prospecting! MediaWiki (Miraheze) and upserts items into the DB.

**Already done:**
- `app/utils/mw_api.py` — MediaWiki client with rate-limit/maxlag handling
- `scrapers/registry.py` — PARSERS dict mapping all 23 tracked page titles → parser functions
- All 23 parsers implemented (pans, shovels, minerals, equipment, modifiers, locations, enchanting, trinkets, formulas, blueprints, relics, runes, plus events, excavations, geodes, mastery, museum, mutations, npcs, quests, sluices, traveling_merchant). ROADMAP.md is stale — it lists several as "to implement" but they are done.
- `app/services/scraper.py` — `run_daily_scrape()` orchestrator, change detection via SHA-256 content hash, full vs. incremental scrape, Changelog version detection
- `scripts/scraper.py` — CLI entry point (`python -m scripts.scraper [--full]`)
- Unit tests exist for most parsers using live wiki fixtures in `tests/fixtures/`

**Remaining for Phase 2:**
- Run scraper end-to-end against live wiki + local PostgreSQL
- Verify items actually upsert into DB (≥3 parser types with valid JSON)
- Verify change detection (re-run on unchanged wiki = 0 new writes)
- Verify ≥20 tracked pages fetched per run
- Add missing parser unit tests (shovels, equipment have no test files)
- Meet all Phase 2 exit criteria from ROADMAP.md

## Objectives

1. Provision local PostgreSQL and run migrations so the scraper can persist data.
2. Execute a full scrape against the live wiki and confirm items upsert into `wiki_pages` and `items`.
3. Confirm at least 3 item types produce valid JSON in `items.data`.
4. Confirm idempotent re-run: second scrape on unchanged wiki produces 0 new DB writes.
5. Confirm ≥20 tracked pages fetched per run.
6. Add unit tests for shovels and equipment parsers; run full test suite + ruff lint green.
7. Declare Phase 2 complete once all ROADMAP.md exit criteria are met.

## Key Tasks (ordered by dependency)

**T1 — Environment provisioning**
- Confirm PostgreSQL 16+ is running locally (DATABASE_URL in `.env`).
- Copy `.env.example` → `.env` and set DATABASE_URL.
- Run `alembic upgrade head` to create `wiki_pages`, `items`, `scraper_runs`, `game_versions` tables.
- Verify `python -c "import app"` imports cleanly and deps (mwparserfromhell, httpx, sqlalchemy[asyncio]) are installed.

**T2 — First full scrape against live wiki**
- Run `python -m scripts.scraper --full`.
- Capture result: status, pages_scraped, pages_changed, pages_errors.
- Assert pages_scraped ≥ 20 (all 23 tracked pages attempted).

**T3 — Verify DB upserts**
- Query `wiki_pages` count (should be ≥ 20 rows with content_hash set).
- Query `items` grouped by `type`; assert ≥ 3 distinct types have ≥ 1 row with non-empty `items.data` JSON.
- Spot-check a parser with known fixture data (e.g., pans → Rusty Pan present).

**T4 — Verify change detection (idempotency)**
- Re-run `python -m scripts.scraper --full` immediately after T2.
- Assert pages_changed == 0 and pages_errors == 0 (content hashes unchanged).
- Assert no new `items` rows inserted (count unchanged).

**T5 — Add missing parser tests**
- Add `tests/test_shovels.py` mirroring `tests/test_pans.py` (count, required fields, data structure, slug uniqueness, known shovel).
- Add `tests/test_equipment.py` mirroring above (tabber rarity tiers, Equipment row templates).
- Ensure both use existing fixtures `tests/fixtures/shovels.wiki` and `tests/fixtures/Equipment.wiki`.

**T6 — Validation suite**
- Run `pytest tests/ -v` — all parser + integration tests pass.
- Run `ruff check` — clean.
- Run `python -m scripts.scraper` (incremental default) without errors.

**T7 — Closeout**
- Update ROADMAP.md Phase 2 checkboxes to complete.
- Record any deviations/known limitations.

## Milestones (ordinal; no hour/day estimates)

- **M1 Environment ready:** `.env` configured, migrations applied, imports clean.
- **M2 First scrape complete:** full scrape runs, pages_scraped ≥ 20, no unhandled exceptions.
- **M3 DB upserts verified:** ≥ 3 item types with valid JSON in `items.data`.
- **M4 Idempotency verified:** re-run yields 0 new writes.
- **M5 Tests green:** `pytest` and `ruff` pass, including new shovels/equipment tests.
- **M6 Phase 2 complete:** all ROADMAP.md exit criteria met, ROADMAP.md updated.

## Required Resources

- Local PostgreSQL 16+ instance reachable at the DATABASE_URL in `.env`.
- Python 3.11+ virtual environment with project dependencies installed (`pip install -r requirements.txt` + dev extras).
- Network access to `https://prospecting.miraheze.org/w/api.php` (live wiki). If the live wiki is unreachable or rate-limits, fall back to fixture-based offline validation for parser correctness (DB upsert still needs a live or mocked client).
- Existing fixtures in `tests/fixtures/` (all 28 wiki page fixtures present).

## Validation Plan

| Criterion | How verified |
|---|---|
| `python -m scripts.scraper` runs, fetches 20+ pages | T2 result pages_scraped ≥ 20 |
| Re-run on unchanged wiki = 0 new DB writes | T4 pages_changed == 0, items count unchanged |
| ≥3 parser types produce valid JSON in DB | T3 `items` grouped by type, ≥3 types with non-empty data |
| Tests pass | `pytest tests/ -v` green |
| Lint clean | `ruff check` clean |

## Risks / Known Limitations

- Live wiki may rate-limit or be unreachable; keep fixture-based parser tests as the offline fallback.
- Items removed from the wiki are never deleted from the DB (stale rows remain). Out of scope for Phase 2 — flagged for Phase 3+.
- `TRACKED_PAGES` is duplicated in `scrapers/registry.py` and `app/services/scraper.py`; drift risk. Out of scope — note only.
- `Changelog` is fetched twice per run (once in `check_for_game_update`, once in `_run_scrape` where its parser is `None` and it is skipped). Minor inefficiency, out of scope.
- Parser `id` field is unused by the service (dedup is by `slug`). Not a bug, but inconsistent.

## Out of Scope (Phase 3+)

- REST API endpoints and calculators (Phase 3).
- Reddit news aggregation (Phase 4).
- CI/CD and Render deployment (Phase 5).
- Item deletion when removed from wiki; deduplicating TRACKED_PAGES; Changelog double-fetch fix.
