# PICK — Core Simplification and Pipeline Hardening

**Status:** implemented and committed. (The status line previously said "not
committed"; that was stale. Verified at `5f9ca0d`: the work is in history and
pushed — `SNAPSHOT_SCHEMA_VERSION` is 6 in both `app/services/snapshot.py:17` and
`frontend/src/lib/snapshot.ts:104`, change detection is the exclusion-list form
(`scripts/export_snapshot.py:47` `_strip_volatile`), and the reconcile/taxonomy
fold is the single declarative `FOLDS` table at
`app/services/reconcile.py:313`.)

## Outcome

All five tasks are done and the gates are green: 428 passed, ruff check/format and mypy
clean, frontend typecheck/lint/build clean, and the offline suite passes with the wiki
unreachable (424 passed, 4 skipped).

What it removed:

| | before | after |
| --- | ---: | ---: |
| `app/api/calculators.py` | 655 | 181 |
| `app/schemas/calculator.py` | 1206 | 535 |
| `app/services/stats.py` | 190 | 55 |
| `frontend/src/api/pick.ts` (generated) | 3956 | 2421 |
| `openapi.json` | ~2900 | 2250 |
| taxonomy entries published | 32 | 25 |

## Deviation from the plan

The plan said a fragment "whose target item is missing from the wiki stays active" and
implied fragments are rare leftovers. In the live data exactly one is active:
`mutation_catalyst` for "Frosthorn Pendant", whose equipment has no wiki page. The
plan's wording was right about the behaviour but understated how much it matters, so
`FRAGMENT_TYPES` is documented with that case, `tests/test_merges.py` pins it, and
`AGENTS.md` records that the rule "no fragment is active" does **not** hold.

The plan also implied `excavation_level` was a fragment. It is not: it is a real
published item (15 of them) that `details.tsx` renders, so it stays in `TAXONOMY`.

## Goal

Simplify and strengthen the core — wiki → parse → reconcile → snapshot → static site — before
building any new features. Four things: delete the dead calculator surface, close the two
silent-staleness holes in export change detection, single-source the snapshot contract, and fold
the reconcile/taxonomy fragments into one declarative mechanism. Then actually schedule the
refresh. The "excess" (custom domain, dark mode, News page, live API) stays deferred.

## Verified state (from the audit)

- The shipped product is the static site reading the committed `frontend/public/snapshot.json`
  (853 items, 25 wiki pages, 8 formulas). The FastAPI backend is local-only.
- `frontend/src/pages/CalculatorsPage.tsx:5-15` imports the client-side `@/lib/calculators` and
  `@/lib/museum`; it calls **no** API hook. `frontend/src/api/pick.ts` (3,956 lines, generated)
  is imported nowhere — only *types* from `pick.schemas.ts` are used, by two pages.
- 9 of 15 calculator endpoints return nothing useful. `app/services/stats.py:81-180` is nine
  stubs returning `[]`/`None`; `app/api/calculators.py:348-356` (`hunt-locations`) queries the
  whole database, computes tier weights, then discards the result into a stub.
- `scripts/export_snapshot.py` `_comparable` is a hand-picked inclusion list. It omits `taxonomy`
  entirely, so a taxonomy-only change is never published, and any field added to a snapshot row
  is silently ignored. Both fail toward serving stale data while reporting success.
- `SNAPSHOT_SCHEMA_VERSION = 5` is declared twice: `app/services/snapshot.py:17` and
  `frontend/src/lib/snapshot.ts:111`. Nothing fails if they drift.
- Eight types are stored then folded away by `reconcile.py` and never appear as active items
  (verified against the snapshot): `museum_ore`, `blueprint`, `mutation_catalyst`,
  `excavation_reward`, `museum_display`, `museum_info`, `merchant_item`, `consumable`.
  `excavation_level` is **not** one of them — it is a real published item rendered by
  `frontend/src/components/item-detail/details.tsx:1124`.
- `deploy/systemd/` holds the units, but they are not installed (`~/.config/systemd/user/` is
  absent) and `loginctl` reports `Linger=no`. The refresh timer never fires today.
  Install steps already exist at `SETUP.md:109-121`.

## Decisions (resolved with the user)

1. Keep the local API; remove only the dead surface.
2. Delete the 9 non-functional endpoints, their stubs, schemas and tests, and drop the
   always-`False` `r_used` field and `is_available()`.
3. Invert change detection: serialise the whole snapshot and **exclude** an explicit volatile
   list, so a newly added field is compared by default and a mistake fails loud (a noisy commit)
   rather than silent (a stale site).
4. This plan includes the reconcile/taxonomy refactor.
5. Keep orval emitting types **and** hooks; it shrinks automatically once the endpoints go.

## Tasks

### 0. Land the in-flight work first

There are uncommitted changes from the previous session. Review, then commit before starting:

- `app/services/snapshot.py` — `ORDER BY` on the snapshot queries.
- `scripts/export_snapshot.py`, `scripts/refresh_site.sh`, `tests/test_export_snapshot.py`.
- `tests/test_snapshot_order.py` (new), `AGENTS.md` (new), `.kilo/command/` (new).
- `frontend/src/pages/HomePage.tsx` — staleness wording.

### 1. Remove the dead calculator surface

Delete these 9 endpoint handlers from `app/api/calculators.py` (keep `/ev`, `/ttg`,
`/modifier-odds`, `/best-pan`, `/museum`, and `/stats/modifier-distribution`):

1. `POST /stats/monte-carlo-ev`
2. `POST /stats/gear-recommendations`
3. `POST /stats/hunt-locations`
4. `POST /stats/exotic-locations`
5. `POST /stats/optimize-luck-cap`
6. `POST /stats/optimize-luck-cap-continuous`
7. `POST /stats/modifier-fraction`
8. `POST /stats/quest-survival`
9. `POST /stats/ev-pareto-frontier`

Delete from `app/services/stats.py`: `monte_carlo_ev`, `score_gear_r`, `score_hunt_locations_r`,
`score_exotic_locations_r`, `optimize_luck_cap_r`, `optimize_luck_cap_continuous_r`,
`fit_modifier_fraction_r`, `quest_survival_r`, `ev_pareto_frontier_r`, and `is_available()`.
Keep `fit_modifier_distribution`.

Delete the matching request/response models from `app/schemas/calculator.py`
(`MonteCarloEV*`, `GearRecommendation*`, `HuntList*`/`HuntRecommendation*`, `ExoticHunt*`,
`LuckCapOptimization*`, `LuckCapContinuous*`, `ModifierFractionFit*`, `QuestSurvival*`,
`EVPareto*`) and remove `r_used` from `ModifierDistributionFitResponse` and its endpoint. Also
update `app/api/calculators.py` imports and `app/services/__init__.py` re-exports.

Delete the stub and endpoint tests in `tests/test_calculator_stats.py`; keep the
`fit_modifier_distribution` coverage and drop the `r_used` assertions.

Then regenerate, and confirm both are clean on a second run:

```bash
.venv/bin/python -c "import json; from app.main import app; json.dump(app.openapi(), open('openapi.json','w'), indent=2)"
cd frontend && npm run generate:api
```

Acceptance: `grep -c r_used openapi.json` is `0`, and `frontend/src/api/pick.ts` is materially
smaller. `app/services/calculators.py` (the 5 real calculators) is untouched.

Optional follow-up: `frontend/src/components/item-detail/details.tsx:1128` maps
`merchant_item: MerchantItemDetail`, a type that is never an active item. Harmless; remove it
while there if convenient.

### 2. Invert change detection

Rewrite `_comparable` in `scripts/export_snapshot.py` to:

1. deep-copy the snapshot;
2. sort `items` by `slug`, `formulas` by `formula_id`, `wiki_pages` by `title`;
3. delete the volatile keys;
4. `json.dumps(..., sort_keys=True)`.

Volatile keys to exclude (everything else is compared):

- top level: `generated_at`, `last_scrape`
- `game_version.detected_at`
- `items[].created_at`, `items[].updated_at`, `items[].data.merchant.last_seen`
- `formulas[].created_at`
- `wiki_pages[].last_scraped`

Tests (in `tests/test_export_snapshot.py`), each asserting a property that the old inclusion
list got wrong:

- a `taxonomy`-only change **is** a change (the regression that motivated this)
- a new top-level key **is** a change (proves the fail-loud direction)
- reordering `items` is **not** a change
- adding or removing an item **is** a change
- an item `data` change **is** a change
- timestamps alone and `merchant.last_seen` alone are **not** changes

### 3. Single-source the snapshot contract

Keep `SNAPSHOT_SCHEMA_VERSION` authoritative in `app/services/snapshot.py`. Add a test that reads
`frontend/src/lib/snapshot.ts`, extracts the numeric `SNAPSHOT_SCHEMA_VERSION`, and asserts it
equals the backend constant. (Pragmatic guard against drift; a codegen step would be the
alternative if this proves fragile.)

### 4. Reconcile and taxonomy refactor

**Taxonomy split** — in `app/taxonomy.py`:

- Add `FRAGMENT_TYPES = frozenset({...})` covering `museum_ore`, `blueprint`,
  `mutation_catalyst`, `excavation_reward`, `museum_display`, `museum_info`, `merchant_item`,
  `consumable`, documented as "a parser emits these only for reconciliation to fold into another
  row; none may be active after reconcile".
- Remove those 8 entries from `TAXONOMY` (currently `app/taxonomy.py:74-82`), so the published
  taxonomy only describes types that can be items. Keep `excavation_level`.
- `area_of`/`label_of` already tolerate unknown types, and the frontend `readTaxonomy`
  (`frontend/src/lib/taxonomy.ts:36`) humanises anything it does not find, so the payload change
  is safe.

**Declarative folds** — in `app/services/reconcile.py`:

- Replace the five bespoke merges (`_merge_museum_ores`, `_merge_blueprints`, `_merge_catalysts`,
  `_merge_excavation_drops`, `_merge_museum_displays`) with one table of fold specs — fragment
  type → target type, how to find the target, and what to write on it (a "set a key" or "append
  to a list/nested list" operation) — driven by a single loop. The existing helpers
  (`_pick_canonical`, `_site_key`, `_name_key`, `SITE_NAME_ALIASES`) are reused unchanged.
- Keep the behaviour identical; this changes structure, not results.
- Keep merchant merge, reward/chest/quest linking, and `_resolve_mineral_areas` as they are
  (they are not folds of a fragment into a target).

**Tests** (extend `tests/test_merges.py`):

- keep the existing per-fold semantics tests, updated to the new entry point;
- add an invariant: after `reconcile_items`, no active row has a type in `FRAGMENT_TYPES`;
- add idempotency: `reconcile_items` twice leaves the same active rows and data as once.

**Version** — bump `SNAPSHOT_SCHEMA_VERSION` to `6` (the taxonomy payload changes) and update the
frontend constant in the same commit (see task 3's test).

No database migration and no `PARSER_VERSION` bump: parsers are unchanged and reconcile runs on
every scrape. Existing inactive fragment rows remain in the database, which is harmless.

### 5. Schedule the refresh, fix stale docs

- Install and enable the timers using the steps already in `SETUP.md:109-121`
  (`cp deploy/systemd/* ~/.config/systemd/user/`, `systemctl --user enable --now
  pick-refresh.timer pick-refresh-full.timer`, `loginctl enable-linger "$USER"`). Confirm with
  `systemctl --user list-timers`.
- Fix `SETUP.md:15` "Step 2", which still documents the removed wiki webhook.
- Re-read `README.md` for claims that the calculator API serves the site; correct them.

## Deferred (excess — not in this plan)

Custom domain `pick.helmsfirth.online`; dark-mode toggle; Reddit/News page; Render API deployment
and `VITE_API_BASE_URL`; dependency-pinning CI check.

## Risks

- **The invert makes runs noisier if a volatile field is missed.** The symptom is a visible daily
  commit, not a silent failure, and the fix is one line in the volatile list. This is the
  intended trade.
- **Reconcile is the least-tested part of the pipeline.** `tests/test_merges.py` and the
  `tests/test_integration.py` reconcile tests pin current behaviour; add the invariant and
  idempotency tests before refactoring, and treat "same output as before" as the acceptance
  criterion. Because the fold semantics are preserved, the exported snapshot must not change
  except for the taxonomy payload.
- **Bumping `schema_version` invalidates browser caches** for one load — expected and correct.

## Validation

- Backend gates, in CI's exact scopes:
  `.venv/bin/ruff check app scrapers scripts tests`,
  `.venv/bin/ruff format --check app scrapers scripts tests`,
  `.venv/bin/mypy app/ scrapers/ scripts/`.
- Full suite with `TEST_DATABASE_URL` set to a database ending in `_test`, and the offline run
  with `MEDIAWIKI_API_URL="http://invalid.invalid/api.php"` (live-wiki tests must skip, not fail).
- Frontend: `cd frontend && npm run typecheck && npm run lint && npm run build`.
- Pipeline idempotency: after task 2 and again after task 4, run
  `.venv/bin/python -m scripts.export_snapshot --output frontend/public/snapshot.json --check`
  twice and confirm the second reports `"changed": false`; then `bash scripts/refresh_site.sh
  --dry-run` must end "Snapshot unchanged; nothing to publish" and leave the file's checksum
  unchanged.
- Guards still hold (see `.kilo/command/verify-guards.md`).
- Regeneration is clean: `/generate-api` produces no diff on a second run.

## Open questions

None blocking. The systemd install (task 5) needs the user's machine and may need `sudo` for
`loginctl enable-linger`.

## Verification notes

- The refactored reconcile was run against the live database and its output compared,
  row by row, with the original implementation's output on the same data: **zero
  differences** once the merchant's `last_seen` timestamp is set aside. The refactor is
  behaviour-preserving, not just test-passing.
- The change-detection inversion was checked by putting the old omission back: a
  taxonomy-only change then reports `changed: false`, which is the bug this fixes.
  With the fix it reports `changed: true`.
- Every new test was proven to fail against the code it replaces, so it is not a
  tautology.
- One hazard found along the way: two pytest sessions running against the same test
  database interfere, because the `test_engine` fixture drops every table on teardown.
  Run them one after another. This is recorded in `AGENTS.md`.
