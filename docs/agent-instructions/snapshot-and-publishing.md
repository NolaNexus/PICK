# Snapshot, Exporter and Publishing

Covers `snapshot.schema.json`, `app/services/snapshot.py`, `scripts/export_snapshot.py`,
`scripts/refresh_site.sh` and the `generated-files` job in `.github/workflows/ci.yml`.

## The contract

- `snapshot.schema.json` describes `frontend/public/snapshot.json`: every key and every
  type, with `additionalProperties: false`. An undeclared field is a failure.
- `tests/test_snapshot_contract.py` validates the committed file against the schema, and
  checks that a deliberately broken snapshot is rejected.
- When the shape changes, change the schema first, then regenerate the frontend types
  (see [frontend.md](frontend.md)).
- `SNAPSHOT_SCHEMA_VERSION` is declared twice: in `app/services/snapshot.py` and in
  `frontend/src/lib/snapshot.ts`. `tests/test_snapshot_contract.py` fails if they drift.
  Bump both when the payload shape changes.

## Row ordering

- `build_snapshot()` in `app/services/snapshot.py` gives every query an explicit
  `ORDER BY`. Without one, PostgreSQL returns rows in plan order. The same items then come
  back in a different order each run, the file differs every time, and the refresh job
  commits it daily for no reason.
- Any new query in `build_snapshot()` needs an `ORDER BY`.
- `_comparable()` also sorts rows before comparing them.

## Change detection

- `_comparable()` in `scripts/export_snapshot.py` serialises the whole snapshot and strips
  an explicit list of volatile keys: scrape timestamps, `data.merchant.last_seen`, and the
  `last_scrape` counters. Everything else is compared, including the taxonomy.
- It is an exclusion list on purpose. The old inclusion list missed the taxonomy, so a
  taxonomy change never published. The current list fails loud instead: an unnecessary
  commit, not a stale site.
- A field that changes on every run goes in the volatile list. Do not stop comparing it.

## Refresh cycle

`scripts/refresh_site.sh` runs the whole cycle: start DB, migrate, scrape, seed, export,
commit, push. It publishes from this checkout.

- It is fail-closed. The scraper exits non-zero if it reached no page (see
  [scraper.md](scraper.md)). The exporter refuses to write a snapshot that would erase the
  catalogue.
- `--dry-run` exercises the cycle without writing or publishing anything.
- It refuses to run on a dirty tree (it checks `git status --porcelain` before pulling).
  Keep the checkout clean. A stray edit makes the pull fail with a message that reads like
  a network problem, or gets left behind by the commit.
- It commits only the snapshot. It ends in `git push origin HEAD:master`, which redeploys
  the site.
- It parses `.env` line by line rather than sourcing it (see
  [environment.md](environment.md)).

## CI check

The `generated-files` job in `.github/workflows/ci.yml` regenerates the snapshot types and
fails if they differ from the committed file. A generated file left stale by a change is
a failed build. Regenerating with unchanged input produces no diff; check that before
committing.
