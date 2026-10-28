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

## Known data-quality gaps

These are in the published data, not in the contract. The contract is satisfied; the
content is not always clean. Check the committed file before assuming a field is good.

- **Raw wiki markup leaks into `data`.** 106 of 853 items carry unrendered markup.
  104 minerals have `</div>` and `chances =` inside `data.chances[].location`, because
  the item-page enrichment appends the drop table to the location text instead of
  replacing it. 2 equipment items have a stray `}}</span>` in a quest reward.
  `render_item_data()` in `scrapers/wikitext.py` handles the common cases but not these.
- **Most items have no picture.** 455 of 853 items have `image_url: null`. Entire types
  have none (enchantments, events, formulas, geodes, mastery, quests, treasure chests);
  minerals are 90% covered. `image_url` is nullable in the schema, so this passes the
  contract. `ItemImage` in the frontend renders a null source for every one of them.
- **Seven types in the taxonomy have no items.** `blueprint`, `consumable`,
  `merchant_item`, `museum_ore`, `excavation_reward`, `museum_display` and `museum_info`
  are fragment types whose rows are folded into other items and then retired. They are in
  the taxonomy so the client can name them, and they are not browsable.
- **Eight minerals have no area.** `mineral-ashvein`, `mineral-aurorite`,
  `mineral-borealite`, `mineral-emerald`, `mineral-forgotten-totem`, `mineral-iridium`,
  `mineral-meteoric-gold` and `mineral-nautilus-shell` have no `data.areas`, so the
  Minerals page cannot filter them. Seven of them have an empty `data.locations`; the
  eighth names "Seashell Beach", which no location holds. The rest (106 of 114) resolve.

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
