# Stabilise PICK: local pipeline, fail-closed publishing, less weight

## Goal

Make the site's data pipeline trustworthy before any new feature work: the
published `snapshot.json` must never be replaced by a degraded one, the scrape
must run somewhere that can actually reach the wiki, and the project must stop
carrying components that do not work.

## What is actually broken (evidence)

1. **GitHub runners are blocked by Miraheze.** In CI run `40643138260`
   (commit `d81b6e4`), *every* wiki request returns
   `403 Forbidden`, e.g.
   `https://prospecting.miraheze.org/w/api.php/?action=parse&page=Pans`.
   All 28 tracked pages, `get_category_members`, and the Changelog fetch. The
   same User-Agent from the developer machine returns 200, so Miraheze is
   blocking the runner IP, not a header problem. **Scraping from GitHub Actions
   can never succeed.**

2. **The resilience fix turned a hard failure into a silent wipe.**
   `442489d` made a failing change-listing fall back to scraping every page and
   stopped errors from raising. On a runner whose requests are all `403`, the
   scrape now completes *successfully* with `status: "partial"`, `pages_scraped:
   0`, exit code 0. `.github/workflows/daily-scrape.yml:60-78` then exports a
   snapshot of the fresh CI database (**0 items**), sees `changed: true`, and
   commits and pushes it over the live data. `static.yml` rebuilds Pages from
   `master`. Result: an empty catalogue on the published site.

3. **Nothing guards the publish.** `scripts/coverage_report.py` only exits
   non-zero under `--strict`, and `daily-scrape.yml:69` calls it bare. There is
   no item-count, status, or freshness check between scraping and committing.
   `weekly-full-scrape.yml:55-69` has the identical unguarded commit.

4. **The CI `test` job is red**, so no commit on `master` is verified.
   `deploy-api.yml` is gated on CI, so it has effectively never deployed. The
   current failure is a bug in a test added to fix the *previous* failure (see
   Phase 1).

5. **The live site reads the committed snapshot, not the API.**
   `frontend/src/lib/snapshot.ts:214-242` uses `/api/v1/export/snapshot` only
   when `VITE_API_BASE_URL` is set, and `static.yml:45` deliberately leaves it
   unset. So the committed `frontend/public/snapshot.json` is the source of
   truth, and the Render API serves an endpoint no visitor calls.

6. **Staleness is invisible.** Six Prometheus metrics are declared in
   `app/monitoring.py:33-66` and never written anywhere else in the repo.
   `/health/ready` only probes the database. A run that scrapes nothing reports
   success.

## Decisions (already agreed — do not re-open)

- The scrape runs **on this machine**, which can reach the wiki.
- The **site stays on GitHub Pages**, served from the committed snapshot; this
  machine scrapes, exports and commits it.
- Scheduling: **systemd user timer**, `Persistent=true`, plus a passphrase-less
  **deploy key** scoped to this repo.
- Failure/staleness surfaces as **journald logs, a freshness warning on the
  site, and a phone push via ntfy.sh**.
- Remove: **Render entirely**, the **wiki webhook endpoint**, the **R
  statistical bridge**, and the **six unused metrics**.

## Phase 0 — stop the bleeding (manual, do first)

Disable the two workflows in the GitHub UI (*Actions → workflow → ••• → Disable
workflow*) or:

```bash
gh workflow disable "Daily Wiki Scrape"
gh workflow disable "Weekly Full Wiki Scrape"
```

The daily schedule is `0 */6 * * *` and recent runs landed 30 min–2.5 h late, so
the next run is due imminently and would commit the empty snapshot. Do not
proceed until both show as disabled.

## Phase 1 — get CI green

`tests/test_scrape_resilience.py` (rewritten in `d1757b5` to use fixtures
instead of the live wiki) fails on the runner with:

```
duplicate key value violates unique constraint "ix_wiki_pages_page_id"
[parameters: ('Blueprint', 1263, 1, ...)]
```

Cause: `_OfflineClient.get_page_info` returns `abs(hash(title)) % 10000` as
`page_id`. Python salts `hash()` per process, so two titles collided. It passed
locally by luck.

1. Replace the `hash()` page id with a **stable, collision-free** value, e.g.
   index the titles: `{t: i for i, t in enumerate(sorted(TRACKED_PAGES), 1)}`.
2. Fix the test's real intent. `get_page_info("Changelog")` returns the
   Changelog fixture, which contains a version heading, so
   `check_for_game_update` returns True and `_run_scrape` takes the **full**
   branch — the increment-fallback path the test is named for is never
   exercised. Make the fake client return a Changelog with no version, or
   stub `check_for_game_update` to return `False`, so the fallback is really
   under test.
3. Assert the fallback explicitly: the set of scraped titles equals
   `set(TRACKED_PAGES)` (minus `skip_titles`), not merely `pages_scraped > 20`.

Verified locally before the collision fix: the full suite passes with the wiki
unreachable (433 passed, 5 skipped) on CPython 3.11 — keep that property; no
test may depend on network access.

## Phase 2 — make publishing fail closed

The publish path must refuse to replace good data with bad data. Two layers:

1. `scripts/scraper.py`: exit non-zero when the run scraped **no** pages
   (`pages_scraped == 0`), so a blocked or empty scrape fails the job. Keep
   `partial` (some pages failed) as a warning, not a failure — that is
   legitimate.
2. `scripts/export_snapshot.py`: before writing, compare against the snapshot
   already on disk and refuse when the new one is degenerate — item count is
   `0` while the existing count is `> 0`, or the count drops by more than a set
   threshold (start at 20%). On refusal: exit non-zero with a clear message and
   leave the existing file untouched.
3. The refresh script (Phase 3) must abort the commit when either of the above
   exits non-zero.

## Phase 3 — the local refresh job

Add `scripts/refresh_site.sh` (POSIX-ish bash, `set -euo pipefail`):

1. `docker compose up -d postgres`, then wait for `pg_isready` (do not rely on
   a fixed sleep).
2. `alembic upgrade head`.
3. `python -m scripts.scraper` — or `--full` when invoked with `--full`.
4. `python -m scripts.seed_formulas`.
5. `python -m scripts.export_snapshot --output frontend/public/snapshot.json`;
   capture `changed`.
6. If `changed`: `git add frontend/public/snapshot.json`, commit with a fixed
   bot identity, `git push`.
7. Run `scripts/coverage_report.py` (non-strict) and record its output; include
   a gap summary in the notification.
8. On any failure: `curl` an ntfy.sh topic and exit non-zero.

Requirements and notes:

- **Environment**: systemd does not read `.env`. Have the script source the
  repo `.env` (gitignored, already present) or use a dedicated
  `EnvironmentFile=`.
- **Credentials**: create a passphrase-less deploy key for this repo only
  (Settings → Deploy keys) and configure the SSH host alias; confirm
  `git push` works with no prompt from a bare `systemd` environment.
- **Interpreter**: `.venv` currently has stale absolute-path shebangs from the
  earlier folder rename. Rebuild the venv before wiring the timer, and invoke
  through the venv's interpreter (`.venv/bin/python -m ...`) rather than the
  `.venv/bin/*` console scripts, whose shebangs are the broken part.
- **Units**: `~/.config/systemd/user/pick-refresh.service` plus
  `pick-refresh.timer` (daily, `Persistent=true`, `OnCalendar` at a fixed local
  time) and `pick-refresh-full.timer` (weekly). Run
  `loginctl enable-linger $USER` so it fires when you are not logged in.
- The weekly full sweep stays as a safety net against a missed incremental.

## Phase 4 — remove the dead weight

All four cuts were agreed. Do them as **separate commits** so any one can be
reverted alone.

1. **GitHub scrapes**: delete `.github/workflows/daily-scrape.yml` and
   `.github/workflows/weekly-full-scrape.yml`. Keep `ci.yml` and `static.yml`.
2. **Render**: delete `render.yaml`, `RENDER_SETUP.md` and
   `.github/workflows/deploy-api.yml`; drop the Render references from
   `README.md` and `SETUP.md`. The API remains as a local Docker service.
3. **Webhook**: delete `app/api/webhooks.py`, its registration in
   `app/api/__init__.py:27,37`, the `webhooks` entry in `app/main.py:32`, the
   `webhook_secret` setting in `app/config.py:24`, and
   `TestWebhookIntegration` in `tests/test_integration.py:95+`. It cannot fire
   against a local-only API.
4. **Metrics**: delete the six unused counters/gauges in
   `app/monitoring.py:33-66`. Keep the middleware and the health routers.
5. **R bridge** — *this one is a refactor, not a deletion; read the warning
   below.* `r_stats` is imported by the calculators
   (`app/api/calculators.py:53-65` uses ten names; `app/services/calculators.py:6`
   uses `fit_modifier_distribution`), and the pure-Python fallbacks live
   *inside* `r_stats.py`.
   - Move the Python implementations into a new `app/services/stats.py`,
     keeping the same function names, and strip the `R_AVAILABLE` branches and
     all rpy2/R code.
   - Update the two import sites to the new module.
   - `is_available()` no longer has a meaning; either drop it or return a
     constant, and update anything that reports an R status.
   - Retarget the fallback tests in `tests/test_r_stats.py` to the new module
     and delete the R-only tests. Delete `R/*.R` and `requirements-r.txt`.
   - **Warning**: this touches the calculators, the most valuable feature. Land
     it last, on its own, with the fallback tests as the safety net. If it
     causes trouble, revert just this commit.

## Phase 5 — make staleness visible

1. `frontend/src/pages/HomePage.tsx` already renders "Data updated …" from the
   snapshot's `generated_at`. Extend it: past a threshold (start at 3 days)
   show a clear warning instead of a quiet line. `SnapshotCache.isStale()` in
   `frontend/src/lib/snapshot.ts:209` already implements the age test; reuse it
   rather than adding a second rule.
2. The ntfy.sh notification in Phase 3 should fire on scrape failure, on a
   refused export, and when the snapshot on disk is already older than the
   threshold at the start of a run (i.e. the previous runs silently did
   nothing).

## Phase 6 — local environment hygiene

- Delete the stray untracked `uv.lock` and the generated `pick.egg-info/`
  directory; confirm `.gitignore` covers both.
- Rebuild `.venv` so no shebang points at the old folder name (this is also a
  Phase 3 prerequisite).
- Note in `README.md` that the repository must not be renamed or moved without
  recreating `.venv` and updating the systemd unit paths — this has already
  broken the environment once.

## Validation

Run every one of these before considering the work done:

1. `pytest` with the wiki **unreachable** (`MEDIAWIKI_API_URL` pointed at an
   invalid host): all pass, live-wiki tests skip. This is the property the CI
   job depends on.
2. `ruff check`, `ruff format --check`, `mypy app scrapers scripts`, and the
   frontend `typecheck` / `lint` / `build` — all clean.
3. Manual end-to-end run of `scripts/refresh_site.sh` against the local Docker
   database: confirm it scrapes, exports, and produces a commit; confirm the
   Pages build follows.
4. **Guard tests**, the important ones:
   - Point `MEDIAWIKI_API_URL` at an invalid host and run the script: it must
     fail, notify, and leave `frontend/public/snapshot.json` **byte-identical**
     to the committed version. Then `git status` must be clean.
   - Seed a snapshot with a healthy item count, then force an export that
     produces zero items: the export must refuse and exit non-zero.
5. Confirm the timer actually fires: shorten `OnCalendar` temporarily
   (e.g. `*:0/5`), watch `systemctl --user list-timers` and
   `journalctl --user -u pick-refresh`, then restore.
6. Push and confirm the `CI` workflow is green on `master`, and that
   `Deploy frontend to GitHub Pages` succeeds with a non-empty snapshot
   (`counts.items` unchanged or greater).

## Risks

- **The wipe is live until Phase 0 is done.** Nothing else matters first.
- The R extraction (Phase 4.5) changes calculator behaviour paths by removing
  the branch that was already dead in every environment, but it is the only
  cut with real blast radius. Keep it isolated.
- A home machine is not a datacentre: the site stays up on Pages, but the data
  only refreshes when the machine runs. `Persistent=true` plus the freshness
  warning plus ntfy is the mitigation; do not pretend availability is equal.
- The ntfy.sh topic is a shared secret in practice: anyone who knows it can
  read the messages. Treat the topic name as a secret.

## Out of scope

- Any new feature or calculator work.
- Re-exposing the API publicly (and therefore the webhook) — revisit only if a
  concrete need appears.
- Rewriting the scraper to bypass Postgres and emit the snapshot directly.
