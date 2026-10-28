# Frontend

Covers `frontend/`: a React + TypeScript + Vite app published to GitHub Pages. The site
is static. It reads the committed `frontend/public/snapshot.json` and never calls the
backend.

## Setup and build

- `npm ci` and `npm install` need `--legacy-peer-deps` (React 19 peer ranges).
- The Vite `base` is `/PICK/`, matching the GitHub Pages repo path.
- `frontend/public/404.html` is a hand-written SPA fallback for deep links. GitHub Pages
  has no rewrite rules.
- Gates: `npm run typecheck`, `npm run test`, `npm run lint`, `npm run build`.

## Types

- `frontend/src/lib/snapshot.types.ts` is generated from `snapshot.schema.json` by
  `npm run generate:snapshot-types`. Never hand-edit it. Everything else under `src/` is
  hand-written.
- The item type is the generated `Item`. Import it from `@/lib/snapshot.types` or
  `@/lib/snapshot`. `Item.type` is the `ItemType` union, `Item.data` is non-nullable, and
  there is no `wiki_id`.
- Calculator result types are hand-written and live in the modules that compute them.
  `calculators.ts` exports `EVOutput`, `TTGOutput`, `ModifierOddsOutput` and
  `BestPanOutput` (camelCase). `museum.ts` exports `MuseumOptimizerOutput` and
  `SlotComparison`. They are not in a generated file.
- There is no `src/api/` directory and no API client. Do not recreate one.

## Calculators

- `frontend/src/lib/calculators.ts` and `frontend/src/lib/museum.ts` are the only
  implementation. They run in the browser. `calculators.ts` uses `decimal.js` for precision.
- There is no oracle. The Python implementation they came from is gone, so the tests pin
  current behaviour, not a known-good result.
- `calculateEV` is a documented placeholder. It uses `base_price` as a proxy for the drop
  chance and ignores `luck` and `quality`. Its test is marked `TODO`. Tracked as issue #6.
  The snapshot holds real drop chances at `data.chances[]` (`chance_percent`, `one_in`).
- Museum calculator bugs are tracked as issue #1.

## Indentation

- `src/lib/calculators.ts` and `src/lib/museum.ts` use tabs. Everything else under `src/`
  uses two spaces.
- `.prettierrc` says `tabWidth: 2`, but CI never runs `prettier --check`.
- Match the file you are editing. Do not run `npm run format` across `src/`: it rewrites
  those two files and buries real changes in whitespace. Tracked as issue #7.
- Each `*.test.ts` sits next to the module it tests.
