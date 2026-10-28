# Roadmap

The project is launched. The site is live at <https://nolanexus.github.io/PICK/> and the
scraper publishes to `master` daily. This file records what shipped and what is still
open. The live source of truth for day-to-day work is `AGENTS.md` and
`docs/agent-instructions/`.

## Shipped

### Data pipeline

- **Phase 2 — Core scraper.** `scrapers/registry.py` tracks 28 wiki pages and maps 25 of
  them to parsers; `app/services/scraper.py` runs the cycle, hashes page content to
  detect changes, and `scripts/scraper.py` is the CLI. The scraper is fail-closed: a run
  that reaches no page exits non-zero rather than publishing an empty catalogue.
- **Change detection.** A page is re-parsed only when its wikitext or `PARSER_VERSION`
  changes. A parser change therefore re-shapes the stored data without a full scrape.
- **Item identity.** Slugs are namespaced by type and enforced by a database check
  constraint. Rows that describe part of another item (the eight *fragment types*) are
  folded into it and retired. Removed items are soft-deleted, never deleted.
- **Taxonomy.** `items.type` is a PostgreSQL enum over 33 values; the `taxonomy` table
  holds each type's area, group, label and display order. The site reads the taxonomy
  out of the snapshot, so the client can name every type.
- **Coverage report.** `scripts/coverage_report.py` names the pages and rows the wiki has
  that the site does not, and `scripts/coverage_allowlist.json` records the pages that
  legitimately hold no items.
- **Contract.** `snapshot.schema.json` describes the published file. The exporter
  validates against it, CI checks the committed file against it, and the frontend's
  types are generated from it.

### Site

- **Phase 3-5 — React + Vite frontend.** Seven routes (`/`, `/items`, `/minerals`,
  `/world`, `/calculators`, `/meta`, `/search`), the Prospecting! theme in light mode,
  and the SPA 404 fallback that makes deep links work on GitHub Pages.
- **Calculators.** Expected value, time-to-goal, modifier odds, best pan, museum
  comparison and museum optimization, all in TypeScript in the browser. There is no
  server-side maths and no oracle: the tests pin current behaviour, not a known-good
  result.
- **Deployment.** `.github/workflows/static.yml` publishes `frontend/dist` through the
  official GitHub Pages Actions flow on every push to `master`.

### Operations

- **Refresh job.** `scripts/refresh_site.sh` runs the whole cycle (migrate, scrape, seed
  formulas, export, commit, push) from the maintainer's machine, driven by a systemd
  timer. It is fail-closed and refuses to publish from a dirty checkout.
- **Gates.** CI runs `ruff check`, `ruff format --check`, `mypy`, `pytest` (402 tests,
  86% coverage) and the four frontend gates on Python 3.11 and 3.12.

## Open

Ordered by how much they cost right now.

### Correctness

- **`calculateEV` is a placeholder** ([issue #6](https://github.com/NolaNexus/PICK/issues/6)).
  It uses `base_price` as a proxy for the drop chance, so EV per pan is price squared,
  and it ignores `luck` and `quality`. The real drop chances are in the snapshot at
  `data.chances[]` (`chance_percent`, `one_in`), so the fix is data the pipeline
  already collects.
- **The museum calculator returns empty results** ([issue #1](https://github.com/NolaNexus/PICK/issues/1)).
  Rarity casing, nested ore data and a discarded ore database.

### Data quality

- **Raw wiki markup leaks into item data**
  ([issue #9](https://github.com/NolaNexus/PICK/issues/9)). 106 items carry unrendered
  markup in `data`: 104 minerals have `</div>` and `chances =` inside
  `data.chances[].location`, and 2 equipment items have a stray `}}</span>` in a quest
  reward. The `render_item_data` renderer handles the common cases but not these.
- **455 of 853 items have no picture, and 8 minerals have no area**
  ([issue #10](https://github.com/NolaNexus/PICK/issues/10)). Entire types are missing a
  picture (enchantments, events, formulas, geodes, mastery, quests), while minerals
  are 90% covered. The 8 area-less minerals cannot be filtered on the Minerals page.
- **Three tracked wiki pages have no parser**
  ([issue #11](https://github.com/NolaNexus/PICK/issues/11)). `Codes`, `Changelog` and
  `Guides` are tracked but have no parser, so they are skipped on every scrape.
  `Codes` alone holds 28 items the site is missing.
- **The coverage report names gaps it will not fix.** `Stat_Systems_Guide` reports 20
  missing rows. The site ships 27 `formula`-type items from that page, and 8 rows in
  the `formulas` table. The Formulas reference reads both, so the two counts are not
  in conflict — but they are different things: an item is a browsable entry, a formula
  row is one the calculator can compute with.

### Tooling

- **`ruff format` fails on `alembic/`** ([issue #8](https://github.com/NolaNexus/PICK/issues/8)).
  Four files would be reformatted and CI does not check that directory, so the drift is
  invisible. Either widen CI's scope or exclude the directory explicitly.
- **The frontend has mixed indentation**
  ([issue #7](https://github.com/NolaNexus/PICK/issues/7)). `src/lib/calculators.ts` and
  `src/lib/museum.ts` use tabs; everything else uses two spaces. CI never runs
  `prettier --check`, so `npm run format` rewrites ~790 lines and buries real changes.
- **mypy is not strict** ([issue #13](https://github.com/NolaNexus/PICK/issues/13)).
  The seven type-error codes are on and the gate is green, but
  `mypy --strict app/ scrapers/ scripts/` reports 42 errors across 16 files, mostly
  `type-arg` and `no-untyped-def`.
- **Dead code** ([issue #12](https://github.com/NolaNexus/PICK/issues/12)).
  `app/logging_config.py` is imported by nothing. `SlotComparison` in
  `frontend/src/lib/museum.ts` is exported but referenced nowhere. `frontend/.oxlintrc.json`
  configures a linter that is not installed and not run.
- **Vite 8 resolves tsconfig paths natively**
  ([issue #14](https://github.com/NolaNexus/PICK/issues/14)). The `vite-tsconfig-paths`
  plugin is now redundant, and it is a second implementation of resolution that has to
  agree with `tsc -b`.

### Platform

- **Custom domain `pick.helmsfirth.online`.** Adding it changes the router basename
  and the Vite `base` from `/PICK` to `/`, and adds `frontend/public/CNAME`.
- **Dark mode.** The `.dark` token block is kept for later; no toggle ships.
- **Reddit credentials** would let the News page carry content instead of `news: 0`.
- **Dependabot and a changelog** are not set up.
