# Calculator Porting Plan — Backend Python → Frontend TypeScript

## Goal ✅ ACHIEVED
Port all calculator math from `app/services/calculators.py` to `frontend/src/lib/calculators.ts` so `CalculatorsPage.tsx` runs fully client-side. The GitHub Pages frontend now needs zero backend at runtime, reading everything from `frontend/public/snapshot.json`.

## Current State
- `CalculatorsPage.tsx` ported to run fully client-side via `frontend/src/lib/calculators.ts` and `frontend/src/lib/museum.ts`
- Backend math lives in `app/services/calculators.py` (~1007 lines) — kept for reference/API parity
- All 6 pages (Items, Formulas, News, Search, Meta, Calculators) now read from `snapshot.json`
- `VITE_API_BASE_URL` / `VITE_BASE_URL` removed from frontend code and deploy workflow
- `VITE_API_BASE_URL` / `VITE_BASE_URL` repo secrets can be removed (manual)

## Stack Decisions

| Decision | Choice |
|----------|--------|
| Math library | `decimal.js` (50 significant digits precision) |
| Calculator types | Mirror `app/schemas/calculator.py` TS types from `frontend/src/api/pick.schemas.ts` |
| Ore database | `snapshotCache` items filtered by `data` fields (`min_kg`, `bonus_stat`, `max_boost`) |
| Forms | Existing `react-hook-form` + `zod` (keep) |
| Mutations | Remove `useCalculate*EndpointApiV1Calculators*Post`; call local functions on submit |
| Tiny probabilities | All internal arithmetic uses `Decimal`; convert to `number` only at display boundary |

## Files to Create / Modify

### Create
1. `frontend/src/lib/calculators.ts` — Port of `app/services/calculators.py` pure math (Decimal.js)
2. `frontend/src/lib/museum.ts` — Port of museum comparison/projection/weight-gate/unlock-cost logic (Decimal.js)
3. `.kilo/plans/calculator-port-frontend.md` — This plan (kept up to date)

### Modify
1. `frontend/src/lib/snapshot.ts` — Add helpers to look up item `data` (ore bonuses) by slug/name for museum ore database
2. `frontend/src/pages/CalculatorsPage.tsx` — Replace API mutations with local calc calls
3. `frontend/src/api/client.ts` — Remove `VITE_API_BASE_URL` dependency (fallback to `''`)
4. `frontend/vite.config.ts` — Remove `VITE_BASE_URL` env read, hardcode `'/'`
5. `.github/workflows/deploy-frontend.yml` — Remove `VITE_API_BASE_URL` / `VITE_BASE_URL` env vars
6. `frontend/package.json` — Add `decimal.js` dependency

## Porting Details

### calculators.ts (from `app/services/calculators.py`)
Constants:
- `SHAKE_SPEED_STEPS` — array of `[min_pct, max_pct, multiplier]`
- `MODIFIER_BASE_DISTRIBUTION` — modifier name → base pct (e.g. `Perfect: 0.002%`)
- `MODIFIER_PRICE_MULTIPLIERS` — modifier name → price mult

All functions use `Decimal` internally:
- `shakesPerSecond`, `digsPerPan`, `digTimePerDig`, `itemsPerPan`
- `weightMultiplier`, `sellMultiplier`, `modifierLuck`
- `effectiveModifierBoost`, `pctOresModified`, `modifierDistribution`
- `qualityMultiplier`, `pansPerHour`
- `calculateEV`, `calculateTTG`, `calculateModifierOdds`, `calculateBestPan`

Inputs are `number` (from forms), converted to `Decimal` internally. Outputs converted back to `number` at display boundary. This preserves precision for tiny drop chances like Key of Life at Lifespring Oasis (~1.549e-11, ~1 in 65 billion).

### museum.ts (from `app/services/calculators.py` museum section)
Constants:
- `MUSEUM_DISPLAYS`, `RARITY_ORDER`, `MODIFIER_BASE_BONUSES`, `MODIFIER_RARITY_MULTIPLIERS`

All functions use `Decimal` internally:
- `getModifierRider`, `weightFactor`, `parseBonusStat`
- `calculateEffectiveBoost`
- `calculateMuseumComparison`, `calculateMuseumProjection`
- `calculateWeightGate`, `calculateUnlockCosts`, `calculateMuseumOptimizer`

## Calculator Page Tab Mapping

| Tab | Backend Endpoint | Frontend Function | Inputs | Outputs |
|-----|-----------------|-------------------|--------|---------|
| EV | POST /calculators/ev | `calculateEV()` | drop table, luck, MB, quality, autopan, mastered, solar, surge | ev_per_pan, items_per_pan, quality_mult, eff_mb, pct_modified, mod_dist |
| TTG | POST /calculators/ttg | `calculateTTG()` | goal_value, location_ev_per_pan, capacity, dig_strength, dig_speed, shake_strength, shake_speed | hours_to_goal, pans_per_hour, ev_per_hour, ev_per_pan, digs_per_pan, dig_time_per_dig, shake_time |
| Modifier Odds | POST /calculators/modifier-odds | `calculateModifierOdds()` | panel_MB, solar_magnifier, modifier_surge | eff_mb_job1, eff_mb_job2, pct_modified, modifier_distribution, note |
| Best Pan | POST /calculators/best-pan | `calculateBestPan()` | pans[], dig_strength, shake_strength, shake_speed, target_capacity, min_luck, min_size_boost, min_modifier_boost | recommendations[], criteria |
| Museum | POST /calculators/museum | `calculateMuseumOptimizer()` | available_ores, unlocked_displays, target_stats, size_boost | slot_recommendations, total_stats, by_rarity, unlock_costs, weight_gate_info |

## Tasks (Ordered)

### T1 — calculators.ts port (Decimal.js)
- [x] Create `frontend/src/lib/calculators.ts`
- [x] Port `SHAKE_SPEED_STEPS`, `MODIFIER_BASE_DISTRIBUTION`, `MODIFIER_PRICE_MULTIPLIERS`
- [x] Port `shakesPerSecond`, `digsPerPan`, `digTimePerDig`, `itemsPerPan`
- [x] Port `weightMultiplier`, `sellMultiplier`, `modifierLuck`
- [x] Port `effectiveModifierBoost`, `pctOresModified`, `modifierDistribution`
- [x] Port `qualityMultiplier`, `pansPerHour`
- [x] Port `calculateEV`, `calculateTTG`, `calculateModifierOdds`, `calculateBestPan`

### T2 — museum.ts port (Decimal.js)
- [x] Create `frontend/src/lib/museum.ts`
- [x] Port `MUSEUM_DISPLAYS`, `RARITY_ORDER`, `MODIFIER_BASE_BONUSES`, `MODIFIER_RARITY_MULTIPLIERS`
- [x] Port `getModifierRider`, `weightFactor`, `parseBonusStat`
- [x] Port `calculateEffectiveBoost`
- [x] Port `calculateMuseumComparison`, `calculateMuseumProjection`
- [x] Port `calculateWeightGate`, `calculateUnlockCosts`, `calculateMuseumOptimizer`

### T3 — snapshot.ts ore lookup helpers
- [x] Add `buildOreDatabase(data)` returning item `data` keyed by "name|rarity" for museum ore database

### T4 — Rewrite CalculatorsPage.tsx
- [x] Remove `useCalculate*EndpointApiV1Calculators*Post` imports + mutations
- [x] Replace each tab's submit handler with local calc function call
- [x] Museum tab uses `snapshotCache` items as ore database
- [x] Keep `react-hook-form` + `zod` validation
- [x] Keep result display UI (stat rows, tables, recommendations)

### T5 — Remove backend URL dependencies
- [x] `frontend/src/api/client.ts`: `BASE_URL = ''` (no env read)
- [x] `frontend/vite.config.ts`: `base: '/'` (no env read)
- [x] `.github/workflows/deploy-frontend.yml`: remove `VITE_API_BASE_URL`, `VITE_BASE_URL` env lines
- [ ] Remove `VITE_API_BASE_URL` / `VITE_BASE_URL` from repo secrets (manual)

### T6 — Verify parity
- [x] Run `tsc -b`, `eslint`, `ruff check app/` — all pass
- [x] `vite build` succeeds with Decimal.js bundle
- [ ] Compare frontend local calc output vs backend API for identical inputs (manual spot check)
- [ ] Confirm all 6 pages work offline from `snapshot.json`

## Validation Checklist

| Criterion | How Verified |
|-----------|--------------|
| `tsc -b` passes | `npx tsc -b` in frontend |
| `eslint` passes (0 errors) | `npx eslint src --ext .js,.ts,.tsx` |
| `ruff check app/` passes | `.venv/bin/ruff check app/` |
| `vite build` succeeds | `npx vite build` in frontend |
| Tiny probability precision | `Decimal(1.549e-11)` preserved through multiplication/division |
| EV/TTG/MO/BPG results match backend | Spot-check identical inputs |
| Museum optimizer matches backend | Spot-check identical inputs |
| Frontend loads without `VITE_API_BASE_URL` | Build with no env var; no console network errors |
| GitHub Pages 404 resolved | `.nojekyll` present; `index.html` at root |

## Risks / Notes

- **Floating point parity**: All internal math uses `Decimal.js` (50 significant digits), eliminating float drift for tiny probabilities like 1.549e-11. Only display boundary converts to `number`.
- **Museum ore database**: `snapshot.json` item `data` must contain `min_kg`, `bonus_stat`, `max_boost`. Verify scraper populates these.
- **Calculator forms use `any` types**: Existing code uses `any` liberally; keep consistent to avoid churn.
- **`VITE_BASE_URL` subpath**: If previously set to `/PICK/`, removing it means site deploys at root only. Confirm desired deployment path.
- **EV calculation is a stub**: Backend `calculate_ev` returns 0 for `ev_per_pan`; frontend matches. Drop chance field mapping from item `data` needs scraper schema alignment.

## Out of Scope (Future)
- PWA / offline-first (already works offline once snapshot cached)
- Real-time calculator updates
- Saved builds / user accounts
- Drop chance field alignment with scraper data schema

