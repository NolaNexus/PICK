# Phase 6 Plan — Frontend (React + Vite + TypeScript on Vercel)

## Goal
Build a React + TypeScript frontend that consumes the deployed PICK API, covering the full API surface with 6 pages, deployed to Vercel.

## Current State
- API deployed at `https://pick-api.onrender.com` (or custom domain)
- OpenAPI spec available at `/openapi.json` or `https://pick-api.onrender.com/openapi.json`
- 20+ endpoints, all tested and working

## Stack Decisions (User-Confirmed)

| Decision | Choice |
|----------|--------|
| Framework | React 18 + Vite + TypeScript |
| Styling | Tailwind CSS (utility-first, fast dev) |
| State | TanStack Query (server state) + Zustand (client state) |
| Routing | React Router v6 |
| API Client | Orval (generates TanStack Query hooks from OpenAPI) |
| Hosting | Vercel (auto-deploy from GitHub) |
| Auth | None (MVP) |
| Real-time | Polling (30s) via TanStack Query `refetchInterval` |

---

## Pages / Routes

| Route | Purpose | API Endpoints |
|-------|---------|---------------|
| `/` | **Item Browser** — paginated list, type filter, search, detail modal | `GET /items`, `GET /items/types`, `GET /items/{slug}`, `GET /search` |
| `/calculators` | **Calculator Dashboard** — 5 tabs: EV, TTG, Modifier Odds, Best Pan, Museum | `POST /calculators/ev`, `/ttg`, `/modifier-odds`, `/best-pan`, `/museum` |
| `/formulas` | **Formula Reference** — list + detail view | `GET /formulas`, `GET /formulas/{id}` |
| `/news` | **News Feed** — paginated, tag filter, latest sidebar | `GET /news`, `GET /news/latest`, `GET /news/tags` |
| `/meta` | **Meta/Status Dashboard** — scrape stats, game version, health | `GET /meta`, `GET /health/health`, `/health/ready` |
| `/search` | **Search Page** — full-text with type/location filters | `GET /search` |

---

## Component Architecture

```
src/
├── api/                    # Orval-generated client (auto-generated)
│   ├── client.ts           # Base fetch wrapper
│   └── *.ts                # Endpoint hooks
├── components/
│   ├── ui/                 # Reusable primitives (Button, Input, Modal, Table, Tabs, Card, Badge)
│   ├── layout/             # Header, Footer, Sidebar, Container
│   ├── items/              # ItemCard, ItemTable, ItemFilters, ItemDetailModal
│   ├── calculators/        # EVForm, TTGForm, ModifierOddsForm, BestPanForm, MuseumForm, ResultDisplay
│   ├── formulas/           # FormulaList, FormulaDetail
│   ├── news/               # NewsList, NewsItem, TagFilter
│   ├── meta/               # ScrapeStats, GameVersionCard, HealthStatus
│   └── search/             # SearchBar, SearchResults, SearchFilters
├── hooks/
│   ├── usePolling.ts       # Custom hook for 30s refetch
│   └── useDebounce.ts      # Search debounce
├── pages/                  # One per route above
├── stores/
│   ├── uiStore.ts          # Global UI state (modals, sidebar, toasts)
│   └── filterStore.ts      # Persisted filter state (localStorage)
├── types/                  # Shared TypeScript types (mirrors API schemas)
├── utils/
│   ├── format.ts           # Number formatting, date formatting, truncate
│   └── constants.ts        # API base URL, item types, rarities, etc.
└── App.tsx                 # Router + providers
```

---

## Key Implementation Details

### 1. API Client Generation (Orval)
```bash
# package.json script
"generate:api": "orval --input https://pick-api.onrender.com/openapi.json --output src/api --client tanstack-query"
```
- Generates TanStack Query hooks + TypeScript types from live OpenAPI spec
- Run once initially, then whenever API changes

### 2. TanStack Query Configuration
```typescript
// queryClient.ts
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,           // 30s cache
      refetchInterval: 30_000,     // 30s polling for live data
      retry: 1,
      refetchOnWindowFocus: true,
    },
  },
});
```

### 3. Polling Strategy
| Data Type | Refetch Interval | Stale Time |
|-----------|------------------|------------|
| Items list | 30s | 30s |
| Calculator results | On submit only | N/A |
| News feed | 60s | 30s |
| Meta/Status | 30s | 15s |
| Search | Manual (debounced) | N/A |

### 4. Responsive Breakpoints (Tailwind)
- Mobile: `< 640px`
- Tablet: `640px - 1024px`
- Desktop: `> 1024px`

### 5. Error Handling
- Global error boundary + toast notifications (react-hot-toast)
- API errors → user-friendly messages + retry button
- Network offline detection → banner

---

## Vercel Configuration

```json
// vercel.json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "rewrites": [
    { "source": "/api/(.*)", "destination": "https://pick-api.onrender.com/api/$1" }
  ],
  "headers": [
    {
      "source": "/assets/(.*)",
      "headers": [{ "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }]
    }
  ]
}
```
- API proxy in development (`vite.config.ts` proxy)
- Production uses Vercel rewrites to avoid CORS

---

## Dependencies

### Production
```json
{
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "react-router-dom": "^6.20.0",
  "@tanstack/react-query": "^5.0.0",
  "zustand": "^4.4.0",
  "axios": "^1.6.0",
  "react-hot-toast": "^2.4.0",
  "date-fns": "^3.0.0",
  "clsx": "^2.0.0"
}
```

### Dev
```json
{
  "vite": "^5.0.0",
  "typescript": "^5.3.0",
  "tailwindcss": "^3.4.0",
  "postcss": "^8.4.0",
  "autoprefixer": "^10.4.0",
  "orval": "^6.0.0",
  "@types/react": "^18.2.0",
  "@types/react-dom": "^18.2.0",
  "eslint": "^8.50.0",
  "@typescript-eslint/eslint-plugin": "^6.0.0",
  "@typescript-eslint/parser": "^6.0.0",
  "prettier": "^3.1.0",
  "prettier-plugin-tailwindcss": "^0.5.0"
}
```

---

## Tasks (Ordered)

### T1 — Project Setup
- [ ] `npm create vite@latest frontend -- --template react-ts`
- [ ] Install dependencies (prod + dev)
- [ ] Configure Tailwind, ESLint, Prettier
- [ ] Configure Orval in `package.json` + `orval.config.js`
- [ ] Run initial `npm run generate:api`
- [ ] Set up Vercel project + GitHub integration

### T2 — Core Infrastructure
- [ ] QueryClient provider + TanStack Query config
- [ ] React Router + routes + layout wrapper
- [ ] Global UI store (Zustand) + filter store
- [ ] UI component library (Button, Input, Select, Table, Modal, Tabs, Card, Badge, Spinner, Tooltip)
- [ ] Error boundary + toast provider
- [ ] API proxy in Vite config + Vercel rewrites

### T3 — Item Browser Page (`/`)
- [ ] ItemTable with pagination, sorting
- [ ] ItemFilters (type dropdown, search input with debounce)
- [ ] ItemDetailModal (fetch `/items/{slug}`)
- [ ] Type filter pills (from `/items/types`)
- [ ] Search integration (link to `/search?q=...`)

### T4 — Calculator Dashboard (`/calculators`)
- [ ] Tab navigation (5 tabs)
- [ ] **EV Tab**: Form (drop table builder, panel stats, quality, boosts) → ResultDisplay
- [ ] **TTG Tab**: Form (goal value, location EV, panel stats) → ResultDisplay
- [ ] **Modifier Odds Tab**: Form (panel MB, boosts) → Distribution chart + odds
- [ ] **Best Pan Tab**: Form (available pans selector, build params, filters) → Ranked table
- [ ] **Museum Tab**: Form (ores grid, unlocked displays, targets, mode select) → Recommendations + unlock costs

### T5 — Formula Reference (`/formulas`)
- [ ] FormulaList (table with name, confidence, variables)
- [ ] FormulaDetail (markdown-rendered formula, variables, confidence, source)

### T6 — News Feed (`/news`)
- [ ] NewsList (paginated, tag filter chips)
- [ ] NewsItem card (title, author, score, tags, posted_at)
- [ ] LatestSidebar (from `/news/latest`)
- [ ] TagFilter multi-select (from `/news/tags`)

### T7 — Meta/Status Dashboard (`/meta`)
- [ ] ScrapeStats cards (total items, types, last run, status)
- [ ] GameVersionCard (version, detected_at, triggered_full_scrape)
- [ ] HealthStatus (live/ready checks with latency)
- [ ] Auto-refresh (30s)

### T7 — Search Page (`/search`)
- [ ] SearchBar (debounced 300ms, min 2 chars)
- [ ] SearchResults (paginated, highlights matches)
- [ ] Filters (type dropdown, location input)
- [ ] Empty/loading/error states

### T8 — Polish & Deploy
- [ ] Responsive testing (mobile/tablet/desktop)
- [ ] Accessibility audit (axe-core, keyboard nav, ARIA labels)
- [ ] Performance (lighthouse > 90)
- [ ] Vercel deploy + custom domain (optional)
- [ ] Analytics (Vercel Analytics or Plausible)

---

## Validation Checklist

| Criterion | How Verified |
|-----------|--------------|
| All 6 routes load without console errors | Manual + Cypress smoke tests |
| Calculator results match API exactly | Compare with known test cases |
| Polling works (data refreshes without reload) | Network tab + manual wait |
| Responsive on mobile/tablet/desktop | Chrome DevTools device toolbar |
| Build passes on Vercel | Vercel deploy logs |
| API proxy works in dev | `npm run dev` → network tab |
| TypeScript compiles with no errors | `npm run typecheck` |
| ESLint + Prettier pass | `npm run lint` |

---

## Risks / Notes

- **API on Render free tier** — cold starts (15-30s). Frontend should show skeleton loaders + retry.
- **CORS** — Vercel rewrites handle production; Vite proxy handles dev.
- **OpenAPI drift** — Orval must be re-run when API changes. Add CI check.
- **Calculator forms** — Complex nested objects (drop tables, ore grids). Use react-hook-form + Zod for validation.
- **Large lists** — Use `react-window` for virtualized ItemTable if >100 items.

---

## Out of Scope (Future Phases)

- User accounts / saved builds / favorites
- Dark mode toggle
- Real-time WebSocket (scrape progress, live updates)
- PWA / offline support
- Internationalization
- Advanced charts (Recharts/Chart.js for calculator visualizations)