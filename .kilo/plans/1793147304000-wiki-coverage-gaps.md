# PICK — Wiki Coverage & Item Page Enrichment

## Goal

Use the wiki's full page list (the `allpages` API behind `Special:AllPages`) plus its categories to
find what the site is missing, fix the missing items, and enrich existing items from their own pages.

## Decisions (resolved with the user)

1. **Scope**: detection **and** fixes **and** enrichment from item pages.
2. **Conflicts**: enrichment only fills fields the index left empty. When the page and the index
   disagree, the index value is kept and the conflict is reported for a human to resolve.
3. **Enrichment breadth**: every item page that exists — not a fixed type list.
4. **Report behaviour stays report-only**: it never fails the scrape, because page classification is
   a heuristic and the wiki is external.

## Verified current state (evidence)

- The coverage report **already calls `allpages`** (`MediaWikiClient.get_all_pages`,
  `scripts/coverage_report.py:129`), so the page list is wired up. The gap is in classification.
- **Title-matching bug**: `TRACKED_PAGES` uses underscores (`Traveling_Merchant`, `Treasure_Map`,
  `Stat_Systems_Guide`) while `allpages` returns spaces, so `Traveling Merchant` is wrongly reported
  as untracked (`coverage_report.py:134` compares raw lowercased titles).
- **Noisy classification**: `looks_like_item_list` (`coverage_report.py:65`) flags shop pages
  (`Alchemist`, `Prospector's Shop`, `Shard Merchant`) as untracked item lists.
- **Categories exist and vary in completeness**: `Category:Minerals` ≈ 110 pages,
  `Category:Traveling Merchant Items` = 8, but `Category:Equipment` = 1 and `Category:Items` = 14.
- **A real missing item**: `Firefly Flare` (page 1063, `Category:Items` + `Category:Consumables`) is
  on no page we parse and is absent from the snapshot.
- **Existing items with empty fields**: `Moonspire` is stored as
  `{value: 45000000, locations: [], description: "", tier: "Exotic"}` while its page supplies both
  the description and `Haunted Creek` plus drop chances and recipes.
- **Where item pages exist**: minerals (`{{Mineral}}`), tools (`{{PanInfobox}}`,
  `{{ShovelInfobox}}`, `{{SluiceInfobox}}`), the Traveling Merchant items
  (`Solar Token`, `Void Shard`, `Meteor Fragment`, `Perfect Reforge Token`, `Traveler's Backpack`)
  and consumables (`Firefly Flare`). **Equipment, most relics, geodes and trinkets have no pages**
  (`Gold Ring`, `Cosmic Resonator`, `Haunted Creek Geode`, `Duplicator` all return `missing`).
- **Tools already carry their stats** from the index (`Rusty Pan` has price/luck/capacity/strength/
  speed/location), so their pages add prose rather than numbers.
- **A real conflict**: `Iron Shovel` price is `2,000` from the Shovels index but `3,000` on its page.
- Item pages are prose with `== Obtainment ==` / `== Usage ==` / `== Trivia ==` sections
  (`Solar Token`, `Traveler's Backpack`, `Firefly Flare`) — the same shape the relic parser handles.

---

## Phase 1 — Page inventory and classification

1. Add to `MediaWikiClient`:
   - `get_category_members(category, limit=500)` — paginated via `cmcontinue`.
   - `get_pages_with_content(titles)` — fetch wikitext for many titles at once with
     `action=query&prop=revisions&rvprop=content|ids&rvslots=main&redirects=1`, 50 titles per
     request. This is what keeps enrichment to a handful of requests instead of ~200.
2. Add a `title_key()` normalizer used everywhere pages and items are compared:
   lowercase, underscores → spaces, straight and curly apostrophes unified, `%26` decoded,
   punctuation dropped, whitespace collapsed.
3. Classify every page from `allpages`:
   - **item page** — has an item infobox (`{{Mineral`, `{{PanInfobox`, `{{ShovelInfobox`,
     `{{SluiceInfobox`, `{{EquipmentInfobox`, `{{RuneInfobox`, `{{RelicInfobox`, `{{ItemInfobox`,
     `{{ConsumableInfobox`, or a generic `{{Infobox`) **or** is in `Category:Items`,
     `Category:Consumables`, `Category:Minerals`, `Category:Traveling Merchant Items`,
     `Category:Enchant Books`, `Category:Blueprints`.
   - **index page** — the existing wikitable-with-an-`Item`-header heuristic.
   - **other** — everything else (guides, shops, locations, NPCs, events).
4. Add an allowlist file `scripts/coverage_allowlist.json` of pages known **not** to be item data
   (guides, shop pages, event pages). Seed it with the current false positives: `Alchemist`,
   `Prospector's Shop`, `Shard Merchant`, `Blueprint`, `Geodes`, `Treasure Map`. The report skips
   allowlisted pages so it converges instead of repeating the same noise.

## Phase 2 — Rework the coverage report

`scripts/coverage_report.py` becomes the single source of truth for gaps. It reports these classes:

| Class | Meaning |
|---|---|
| `missing_item` | an item page whose title matches no scraped item (e.g. `Firefly Flare`) |
| `missing_rows` | a tracked index page with more table rows than parsed items (existing check) |
| `no_parser` | a tracked page with no parser (`Codes`, `Mutations`) |
| `untracked_index` | an untracked page that looks like an index (allowlist applied) |
| `conflict` | a page value that disagrees with the stored index value |
| `empty_field` | an item field left empty where its page has a value (enrichment backlog) |

Requirements:
- Fix the title comparison with `title_key()` so `Traveling_Merchant` matches `Traveling Merchant`.
- Include the item name on `missing_item` rows, not just a count.
- Keep writing Markdown to `$GITHUB_STEP_SUMMARY` and keep exit code 0 on gaps.
- Add `--strict` (non-zero exit when any gap exists) for local/manual runs only; the workflow keeps
  using the report-only mode.

## Phase 3 — Consumables: the missing items

1. Add item type `consumable` for item pages in `Category:Consumables` that match no existing item.
   - `Firefly Flare` is the known case; the implementation must report the full set it finds.
2. Parse the prose shape: lead sentence, `== Obtainment ==`, `== Usage ==`, `== Notes ==` /
   `== Trivia ==`, image, and a cost when `{{$|…}}` / `{{Meteor Shards|…}}` appears.
3. **Promote merchant-only items that have a page**: `Traveler's Backpack` is currently a
   `merchant_item`; its page says it is a consumable, so it becomes a `consumable` and the existing
   `reconcile_items` merge attaches the merchant listing to it (`MERCHANT_TYPES` are excluded from
   candidates, so any real type wins).
4. Slug: `consumable-<name>`, through the existing `_type_prefixed_slug`.
5. `app/services/reconcile.py`: add `"consumable"` to `CANONICAL_PREFERENCE` so a consumable is
   preferred over a merchant listing.

## Phase 4 — Enrich existing items from their pages

1. New `scrapers/item_page.py` with `parse_item_page(title, wikitext) -> dict | None` returning
   `{"name", "type_hint", "fields", "modifiers", "prose"}`:
   - **Infobox** — read the named parameters of the matched infobox template
     (`{{Mineral}}`: name, image, description, rarity, value, locations, chances, recipes;
     `{{PanInfobox}}`/`{{ShovelInfobox}}`/`{{SluiceInfobox}}`: Color, Image, Obtained, Price,
     Luck/Capacity/Strength/Speed/Efficiency/Toughness, Location).
   - **Prose** — `== Overview ==`, `== Stats ==`, `== Obtainment ==`, `== Usage ==`,
     `== Museum Usage ==`, `== Trivia ==`.
   - **Minerals** — parse `chances` into `[{location, chance_percent, one_in}]` and `recipes` into
     `[{station, rarity, ingredients: [...]}]`.
   - Reuse `scrapers/wikitext.render_text` and `scrapers/stats.parse_modifier_list`; extend
     `_STAT_NAMES`/aliases with `Capacity (Pans)`, `Capacity (Sluices)`, `Dig Strength`, `Toughness`,
     `Efficiency`.
2. New `app/services/enrichment.py` with `enrich_items_from_pages(db, client)`:
   - Build the candidate title set from the scraped item names, fetch existing pages in batches,
     parse, then merge.
   - **Match by `title_key` to the canonical item only**: prefer types in `CANONICAL_PREFERENCE`;
     never write to `excavation_reward`, `npc`, `quest`, `event` or `merchant_item` rows.
   - **Fill-empty-only merge**:
     - write a field only when the stored value is missing/empty/`[]`/`""`;
     - never overwrite a non-empty value (this keeps `Iron Shovel` at `2,000`);
     - when both exist and differ, append `{field, stored, page}` to a conflicts list.
   - `modifiers` are merged by `(stat, unit)`; a stored modifier wins.
   - Return `{"enriched": n, "fields_filled": n, "conflicts": [...], "missing_pages": n}`.
3. Wire it into `_run_scrape` after the index pages and before `reconcile_items`, and expose the
   summary in the scrape result so it shows in the run log and the report.
4. Store the new prose keys on the item (`overview`, `obtained`, `trivia`, `museum_usage`,
   `chances`, `recipes`) only when present.
5. Bump `PARSER_VERSION` so the pages already parsed are re-processed.

## Phase 5 — Frontend

1. New `ConsumableDetail` in `frontend/src/components/item-detail/details.tsx` and register it for
   `consumable`.
2. Extend `MineralDetail` with **Drop chances** (location, chance %, 1-in-N) and **Recipes**
   (station, rarity, ingredient list), and **Museum usage**.
3. Extend `ToolDetail` with the prose sections (`Overview`, `Obtained`, `Trivia`) when present.
4. Extend `RelicDetail`/`ConsumableDetail` to show `usage` and `notes` when present.
5. All new fields optional; the existing `FallbackDetail` still covers unknown types.

## Phase 6 — Rollout

1. Bump `SNAPSHOT_SCHEMA_VERSION` (`app/services/snapshot.py`) to 3 and `SNAPSHOT_SCHEMA_VERSION`
   in `frontend/src/lib/snapshot.ts` to match, so cached clients discard the old snapshot.
2. Run the scrape, export the snapshot, and run the coverage report; commit the refreshed
   `frontend/public/snapshot.json`.
3. The daily workflow already runs the report; no change needed beyond the enrichment step living
   inside the scrape.

---

## Files

**New**: `scrapers/item_page.py`, `app/services/enrichment.py`, `scripts/coverage_allowlist.json`,
`tests/test_item_page.py`, `tests/fixtures/item_pages/*.wiki` (mineral, pan, shovel, sluice,
consumable page samples).

**Edit**: `app/utils/mw_api.py` (batch + category helpers), `scripts/coverage_report.py`,
`app/services/scraper.py`, `app/services/reconcile.py`, `app/services/snapshot.py`,
`scrapers/registry.py`, `scrapers/stats.py`, `scrapers/__init__.py`,
`frontend/src/lib/snapshot.ts`, `frontend/src/components/item-detail/details.tsx`,
`frontend/src/components/item-detail/primitives.tsx`, `tests/test_coverage_report.py`.

## Risks

- **Wrong-item merges.** Names repeat across types (`Solar Token` is both a relic and an
  excavation drop). Mitigation: match only canonical types, never link rows.
- **Silent data changes.** A careless merge would overwrite index values. Mitigation:
  fill-empty-only, plus a regression test using the `Iron Shovel` 2,000/3,000 conflict.
- **Name normalization.** Curly apostrophes (`Merchant’s Potion`), `(Pans)` suffixes and
  `%26` in titles break matching. Mitigation: one `title_key()` used by both sides, with tests.
- **Request volume / rate limits.** ~200 pages. Mitigation: batch 50 titles per request and reuse
  the client's existing maxlag handling.
- **Classification noise.** The report could drown in false positives. Mitigation: the allowlist,
  `item page` signals, and a seeded run that the implementation reviews before committing.
- **New type leaks into filters/calculators.** Mitigation: the detail registry falls back safely;
  the museum optimizer only reads `rarity`, which consumables do not set.
- Live-wiki tests must keep the existing `requires_wiki` skip guard.

## Validation

1. Coverage report:
   - `Traveling Merchant` no longer appears as untracked;
   - `Firefly Flare` appears as `missing_item` before the fix and disappears after;
   - allowlisted shop pages no longer appear;
   - `Iron Shovel` is listed as a conflict, and its stored price is still `2,000`.
2. Data:
   - `Moonspire` has a non-empty `description` and `locations`, plus `chances`/`recipes`;
   - `consumable` items exist (Firefly Flare) and `Traveler's Backpack` is no longer
     `merchant_item`;
   - a second export reports `changed: false` (idempotent).
3. Backend: `ruff`, `ruff format --check`, `mypy`, full `pytest` with and without R.
4. Frontend: `typecheck`, `lint`, `build`; browser check of a mineral, a tool, a consumable and a
   relic detail view, with no console errors.
5. CI green; the Pages deploy succeeds and the live snapshot reports `schema_version: 3`.

## Open questions

- The allowlist needs a maintained home; default is `scripts/coverage_allowlist.json`, reviewed by
  hand when the report surfaces a new page.
- The exact set of `missing_item` pages will only be known after the first classification run; the
  implementation should report it before writing fixes, so the list can be sanity-checked.

## Implementation note

This plan needs source edits, new files, a scrape/export, and git commands. Switch to an
implementation-capable agent to execute it.

---

## Execution outcome (completed)

**Status: implemented.** The site is now 1023 items (was 1022): `Firefly Flare` was added,
`Traveler's Backpack` became an item of its own instead of a merchant listing, and 929 fields
across 172 items were filled in from the pages that describe them.

### What shipped

`f90d3ac` — page classification and the reworked report, the item page parser, the enrichment
pass, the consumable type, the image name fix, and the detail views for the new fields.

### Results

- **`Firefly Flare` is on the site.** The report names the items that have a page but are not
  on the site, and the report no longer lists any.
- **929 fields filled across 172 items**: descriptions, obtainment, usage, trivia, drop
  chances, recipes and museum usage.
- **`Moonspire`** went from `locations: []` and `description: ""` to having its description,
  `Haunted Creek`, a 1-in-4,626,836,341 drop chance and its recipe.
- **`Traveler's Backpack`** is a `consumable` with its picture; the merchant's live stock is
  merged into it by the existing reconciliation.
- **89 more pictures resolve.** A file name the wiki stores with a space in it was never found.
- **The Iron Shovel keeps its index price of 2,000**, not the 3,000 on its page, and the
  difference is reported.

### Defects found and fixed along the way

- The report compared page titles literally, so `Traveling_Merchant` was reported as untracked.
- The category names were compared with and without their `Category:` prefix, so no page was
  ever recognised as an item page.
- A page's infobox leaked into its description, and a bolded picture caption was read as the
  item's name, which created an item called `]]`.
- `{{Stat|Luck|value=30}}` rendered as `30`, so a sluice's overview read "With 25000 and 200"
  instead of "With Luck (25000) and Capacity (200)".
- A file name the wiki stores with a space in it never resolved to a picture.

### Remaining gaps (reported by the tool, not items)

- `Codes` (28 rows) and `Mutations` are tracked but have no parser. They are not item data.
- `Stat_Systems_Guide` is missing about 20 rows. It holds formulas, not items.

### Verification

- Backend: `ruff`, `ruff format --check` and `mypy` clean; 402 tests pass with R, 365 pass
  and 37 skip without R.
- Frontend: `typecheck` and `lint` clean, production build succeeds.
- The site was driven in a headless browser: all six routes plus the deep-link fallback render
  with zero console errors, and the detail views were opened for a mineral, a tool, a
  consumable and a relic.

