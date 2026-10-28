# AGENTS.md: reconcile with the current codebase

**Status:** implemented.

## Context

`AGENTS.md` was rewritten earlier in this session and its claims were verified against
the code at that point. It is **accurate** — this plan does not rewrite it. What it
does is close four gaps found on a second verification pass, after the
`pick.schemas.ts` retirement and the vitest suite landed.

The plan was written while the working tree carried uncommitted work from that
earlier task: the `AGENTS.md` rewrite, the stale-file retirement, and the 126-test
frontend suite. This plan added to that rather than replacing it.

## What was verified as already correct

Re-checked against the code; all still true, so **keep them**:

- 24 parsers, 33 item types, 8 fragment types (only 4 in `FOLDS`), 853 snapshot items.
- `pages_ok` vs `pages_scraped`; the exclusion-list change detection; the
  `ORDER BY` requirement; the three `items` check constraints; the taxonomy living
  in the database; `SNAPSHOT_SCHEMA_VERSION` = 6 in both places; `Mapped[]` and the
  strict mypy config; `ruff format` drift on `alembic/` (4 files, outside CI scope);
  dotenv-not-shell; migrations `001`–`007`; 110 files ruff-formatted; the virtualenv
  path hazard; `.env.example` tracked with `.env` ignored.
- The vitest section, the item-type section, and the calculator-types section are all
  correct as written.

## The four gaps

### 1. Mixed indentation in the frontend

`frontend/src/lib/calculators.ts` (322 tab-indented lines) and
`frontend/src/lib/museum.ts` (469) are **tab**-indented. Every other file under
`frontend/src/` uses **2 spaces**. `.prettierrc` sets `tabWidth: 2` and no
`useTabs`, so those two files disagree with the config as well as with their
neighbours.

The danger is that CI never runs `prettier --check` — the `build-frontend` job runs
`typecheck`, `test`, `lint` and `build` only, and the only `format` step in the
workflow is `ruff format --check` on the Python side. So `npm run format` on the
frontend would rewrite ~790 lines of those two files, burying a real change in
whitespace, and nothing would fail to warn you.

### 2. The health routes have a doubled path segment

`app/main.py` mounts the health router at prefix `/api/v1/health`, and
`app/monitoring.py` declares `health_router = APIRouter(prefix="/health")` with
routes at `""`, `/ready` and `/live`. The real URLs therefore carry **two**
`health` segments:

- `/api/v1/health/health`
- `/api/v1/health/health/ready`
- `/api/v1/health/health/live`

Confirmed in `openapi.json` (lines 41, 65, 89) and in the generated
`frontend/src/api/pick.ts`. An agent that guesses `/api/v1/health` or
`/api/v1/health/ready` gets a 404, and the more natural guess looks plausible
enough to waste time on.

Related: `/metrics` is a plain route declared on `app` in `app/main.py`, **not** the
`router` object in `app/monitoring.py`. That router is mounted nowhere, so the
`@router.get("")` metrics handler in `app/monitoring.py` is dead code — the live
handler is `metrics_endpoint` in `app/main.py`. Worth one sentence so nobody
"fixes" the wrong function.

### 3. Two backend modules are missing from the layout table

`app/monitoring.py` (Prometheus metrics, health checks, the metrics middleware) and
`app/logging_config.py` (`setup_logging`, JSON logs unless `debug`) are real
entrypoints wired into `app/main.py` but absent from the layout table.

### 4. The API route surface is never named

`AGENTS.md` says what the API serves but not where it lives. The actual surface:

| Route | Source |
| --- | --- |
| `/api/v1/items`, `/api/v1/formulas`, `/api/v1/meta`, `/api/v1/search`, `/api/v1/export` | the five routers in `app/api/__init__.py` |
| `/` | `app/main.py` |
| `/metrics` | `app/main.py` |
| `/api/v1/health/health{,/ready,/live}` | `app/monitoring.py` via `app/main.py` |

## Decisions made

- **Indentation:** document the split, and fix the two test files that do not match
  their own modules. Do **not** re-indent the two source modules — that is a
  ~790-line whitespace change that belongs in its own commit, and the user chose
  against it here.
- The plan is documentation plus a two-file whitespace fix. No behaviour changes.

## Tasks

### Task 1 — Re-indent `snapshot.test.ts` and `taxonomy.test.ts` to 2 spaces

`frontend/src/lib/snapshot.test.ts` (147 tab-indented lines) and
`frontend/src/lib/taxonomy.test.ts` (135) are tab-indented, but their modules
`snapshot.ts` and `taxonomy.ts` use 2 spaces. Each test file should match the
module it tests.

Both files were verified to contain **no tab characters other than leading
indentation**, and no literal `\t` escapes or template literals that a naive
replacement could damage. The conversion is therefore safe.

Convert leading tabs to 2 spaces each. `expand -t 2` would also convert interior
tabs, so prefer a leading-only substitution — e.g. `sed -i 's/^\t/  /'` applied
repeatedly, or a small Python snippet that expands only the leading run.

Do **not** touch `calculators.test.ts` and `museum.test.ts`: their modules are
tab-indented, so they are already correct.

Verify the result: each of the four test files has the same indentation style as
the module it tests, and the file content is otherwise byte-identical apart from
the leading whitespace.

### Task 2 — Add the indentation note to `AGENTS.md`

Add to the **Frontend** section (alongside the existing `--legacy-peer-deps` and
`/PICK/` base notes):

> **The frontend has mixed indentation.** `src/lib/calculators.ts` and
> `src/lib/museum.ts` use tabs; everything else under `src/` uses two spaces.
> `.prettierrc` says `tabWidth: 2`, but CI never runs `prettier --check`, so the
> drift never fails a build. **Match the file you are editing** — do not run
> `npm run format` across `src/`, because it rewrites those two files wholesale
> and buries a real change in whitespace. Each `*.test.ts` matches the module it
> tests.

### Task 3 — Add the API route surface to `AGENTS.md`

Add a short subsection under "What this is" or a new "The API" heading, listing the
routes in the table above, and stating the two non-obvious facts:

- The health paths carry a **doubled** `health` segment
  (`/api/v1/health/health`, `.../ready`, `.../live`) because the router's own
  `/health` prefix is added to the `/api/v1/health` mount point. Do not "fix" the
  duplication without checking `openapi.json` and the generated client — the paths
  are published in both.
- `/metrics` is served by `metrics_endpoint` in `app/main.py`. The `router` object
  in `app/monitoring.py` is not mounted, so its `@router.get("")` metrics handler
  is dead code.

### Task 4 — Add `app/monitoring.py` and `app/logging_config.py` to the layout table

Two rows in the existing layout table:

- `app/monitoring.py` | Prometheus metrics, the health router, and the request-metrics middleware
- `app/logging_config.py` | `setup_logging`; JSON logs unless `settings.debug`

### Task 5 — Verify the result

The file is documentation, so verification is a read-through plus the gates that
could be affected by Task 1.

```bash
cd /home/nola/Desktop/PICK/frontend
npm run typecheck
npm run test
npm run lint
```

Task 1 changes whitespace in two test files, so the frontend gates must still pass
and the test count must still be **126 passed / 4 files**.

Confirm the indentation invariant holds:

```bash
cd /home/nola/Desktop/PICK
grep -rlP '^\t' frontend/src --include=*.ts --include=*.tsx
```

Expected output after Task 1 — exactly four files, all matching tab-indented
modules:

```
frontend/src/lib/calculators.ts
frontend/src/lib/museum.ts
frontend/src/lib/calculators.test.ts
frontend/src/lib/museum.test.ts
```

Then confirm the backend and generated files are untouched by this work:

```bash
cd /home/nola/Desktop/PICK
git diff --stat app/ scrapers/ scripts/ tests/ alembic/   # expect empty
```

## Risks

| Risk | Mitigation |
| --- | --- |
| The tab→space conversion damages a string literal | Both files were verified to contain tabs only as leading indentation, with no `\t` escapes and no template literals. Re-read the diff after converting. |
| The re-indent changes behaviour | It cannot: only leading whitespace changes. The test count must stay at 126 — that is the check. |
| Documenting the doubled `health` path freezes a wart | State it as a fact to verify against `openapi.json`, not as a recommendation. If someone later fixes the prefix, `openapi.json` and `pick.ts` change and the `generated-files` CI job catches the drift. |
| `AGENTS.md` grows past usefulness | The additions are four short items. The file is 345 lines now and stays under ~370. Do not pad it with anything not listed here. |

## Out of scope

- Re-indenting `calculators.ts` and `museum.ts` to 2 spaces. The user chose to
  document the split instead. If that is ever done, it needs its own commit and a
  note that `npm run format` will then be safe.
- Removing the dead `router` in `app/monitoring.py` or the duplicated health
  prefix. Both are behaviour-affecting and belong in a separate change.
- Making CI run `prettier --check`. Worth considering separately: it would make
  the indentation drift fail the build, but it would fail today, so it needs the
  re-indent first.
- Any further `AGENTS.md` rewrite. The file is accurate; this plan only closes
  gaps.
