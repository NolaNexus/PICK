# PICK — Commit the work, then close the gaps

**Status:** ready to implement

## Why this is next

The audit found the core in good shape and four concrete holes around it.

**The core is sound.** The pipeline is fail-closed (a scrape that reaches nothing aborts
before publishing; an export that would empty the catalogue is refused), the database
enforces its own invariants, the published file has a contract, and 462 tests pass with
the wiki unreachable. The incremental scrape is efficient — it hashes the wikitext and
skips unchanged pages, so a quiet wiki costs nothing.

**The four holes**, in order of how much they cost:

1. **36 modified and 8 new files are uncommitted.** Two large, green, verified pieces of
   work exist only in the working tree. The daily refresh job runs `git pull --ff-only`
   on this checkout, which fails outright on a dirty tree — so the job is currently
   broken, and nothing has been published since.
2. **CI does not check that the generated files are current.** `openapi.json`, the orval
   client and the new snapshot types are all committed and all generated. Nothing
   regenerates them in CI and compares, so any of the three can drift silently and the
   site ships a client that does not match the spec.
3. **The refresh job will not notice it is publishing from a dirty tree.** It does
   `git add "$SNAPSHOT"` and commits. Anything else that changed would be left behind,
   and the next run would fail at `git pull`.
4. **Two references point at files that no longer exist.** `pyproject.toml` declares
   `pick-news = "scripts.news_scraper:main"` for a module deleted in `7706207`, and
   `requirements.txt` tells the reader to `pip install -r requirements-r.txt`, a file
   that is not in the repository.

**One thing worth naming but not doing now:** `mypy` disables seven error codes
globally (`arg-type`, `assignment`, `attr-defined`, `call-arg`, `index`, `misc`,
`var-annotated`), so the typecheck catches import and name errors but little about the
shape of the code. Narrowing that is the biggest single quality lever in the codebase
and also a slow grind across 26 parser modules. It is deliberately **out of scope** for
this block of work — it is a separate piece of work, not a follow-up task here.

## Decisions

- Commit first, then close the gaps. The uncommitted work is green and verified; it
  should land before anything else changes.
- Scope is the four gaps. No new features, no type-checking work, no data work.

## Tasks

### 1. Commit the two pieces of work

The working tree holds two independently reviewable pieces. Commit them separately so
each can be read on its own.

**Commit A — the core simplification.** The dead calculator surface is gone (9 endpoints
that could only return an empty result, their stubs, schemas and tests, and the always-
`False` `r_used` field); change detection is an exclusion list rather than an inclusion
list, so a taxonomy-only change is published instead of silently dropped; the reconcile
folds are one declarative table; the fragment types are named in the taxonomy.

**Commit B — the database and the file contract.** `items.type` is a PostgreSQL enum;
three check constraints hold the slug, name and payload rules; the taxonomy lives in the
`taxonomy` table; `wiki_id` is gone; the inconsistent column types are fixed; the
partial indexes are in; `snapshot.schema.json` describes the published file and the
frontend's types are generated from it.

The snapshot file and `openapi.json` belong with commit B, because they changed as a
result of it. The `.kilo/plans/` files go in whichever commit is closest in time, or in
their own — they are history, not code.

Before committing, re-run the gates and check the tree is what is expected:

```bash
cd /home/nola/Desktop/PICK
.venv/bin/ruff check app scrapers scripts tests
.venv/bin/ruff format --check app scrapers scripts tests
.venv/bin/mypy app/ scrapers/ scripts/
TEST_DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick_test" \
DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick" \
  .venv/bin/python -m pytest -q
cd frontend && npm run typecheck && npm run lint && npm run build
```

**Do not push yet.** The pages deploy runs on every push to `master`, and the working
tree has not been through that path yet. Push once both commits are in and CI is green.

### 2. Make CI check that the generated files are current

Three artefacts are generated and committed. None of them is checked.

Add a job to `.github/workflows/ci.yml`, after `lint` and `typecheck`, that regenerates
all three and fails if anything differs:

```bash
# The OpenAPI spec.
.venv/bin/python -c "import json; from app.main import app; json.dump(app.openapi(), open('openapi.json','w'), indent=2)"

cd frontend
npm run generate:api
npm run generate:snapshot-types
```

then `git diff --exit-code openapi.json frontend/src/api/ frontend/src/lib/snapshot.types.ts`.

The job needs both the Python and the Node toolchains, so it cannot borrow the setup
steps from the existing jobs — it needs its own `setup-python` and `setup-node`. The
Python side needs `requirements.txt` installed; the Node side needs
`npm ci --legacy-peer-deps`.

**The spec has no trailing newline** (it is written with `indent=2` and no newline), so
the regeneration must be byte-identical for the check to be meaningful. It already is —
verified: regenerating all three produces no diff.

Note that `frontend/src/api/client.ts` is hand-written, not generated, so the diff must
name the two generated files rather than the whole directory. `orval` writes
`pick.ts` and `pick.schemas.ts`; confirm the config writes nothing else
(`frontend/orval.config.mjs`).

### 3. Make the refresh job refuse to publish from a dirty tree

`scripts/refresh_site.sh` currently:

- runs `git pull --ff-only` at line 104, which fails on a dirty tree — but only with a
  message that says "resolve it by hand", so a stray edit looks like a network problem;
- runs `git add "$SNAPSHOT"` at line 168, which stages one file and leaves everything
  else behind.

Both should be explicit, and the failure should say what is actually wrong.

Add a check before the pull, so the reason is clear:

```bash
# The job publishes the snapshot from this checkout, so the checkout has to be
# clean. A stray edit would otherwise fail the pull below with a message about
# the network, or be left behind by the commit at the end.
if [ -n "$(git status --porcelain)" ]; then
  fail "the checkout has uncommitted changes; commit or stash them first"
fi
```

`git status --porcelain` is empty for a clean tree and prints one line per change, so
the test is exact.

Then, before the commit, make sure the only thing staged is the snapshot. If anything
else is staged, refuse rather than committing a half-finished state:

```bash
if [ "$(git diff --cached --name-only)" != "$SNAPSHOT" ]; then
  fail "something other than the snapshot is staged; refusing to publish"
fi
```

Place this after `git add "$SNAPSHOT"` and before `git commit`.

### 4. Remove the two dead references

- **`pyproject.toml` line 39**: delete `pick-news = "scripts.news_scraper:main"`. The
  module was deleted in `7706207` ("take the news feature out for now"), so the entry
  point raises `ModuleNotFoundError` when it is resolved. Check whether `pick-scraper`
  on line 38 still resolves; it does, and it stays.

  While there: `pyproject.toml` also lists the runtime dependencies unpinned, while
  `requirements.txt` pins them. Two lists that can disagree is the same class of problem
  this whole block of work is about. **Recommended:** make `requirements.txt` the only
  list of runtime dependencies and have `pyproject.toml` read it, or delete the
  `dependencies` block and say in a comment that `requirements.txt` is the source of
  truth. Do not leave two lists.

- **`requirements.txt` lines 20-28**: the comment tells the reader that rpy2 is not
  installed and points at `app/services/r_stats.py` and `requirements-r.txt`. All three
  were deleted. Replace the comment with a short note that the R bridge was removed and
  the calculators are pure Python.

  `requirements.txt` also lists `pytest`, `pytest-asyncio`, `pytest-cov` and `ruff` —
  test and lint tools in the runtime requirements file. CI installs `requirements.txt`
  for the lint and typecheck jobs, which is why they are there. **Recommended:** split
  them into `requirements-dev.txt` and have CI install both where needed. This is a
  small change and it makes the runtime file honest.

### 5. Update `AGENTS.md` and `SETUP.md`

- `AGENTS.md`: it now describes the schema and the file contract, but it does not
  mention that CI checks the generated files, or that the refresh job refuses to run on
  a dirty tree. Both are the kind of thing an agent gets wrong. Add one line for each.
- `SETUP.md`: the "Step 2" section was fixed in the last block of work. Check the
  remaining sections against what the code now does — in particular whether it still
  describes the R bridge as installable.

## Risks

- **Commit A and commit B both change the snapshot.** The snapshot in the tree already
  has `wiki_id` removed and the taxonomy updated, so it belongs with commit B. Splitting
  the commits means commit A alone would not pass its own snapshot validation — which
  is fine, because the validation runs in the working tree, not per commit. **Say so in
  the commit body** if a reviewer tries to check out commit A on its own.
- **The CI drift job installs two toolchains.** It is the slowest job in the workflow.
  If it becomes a nuisance, it can be moved to a `workflow_dispatch` trigger plus a
  pre-push hook, but then it stops catching drift automatically. Keep it automatic.
- **The dirty-tree check will fail the job on the day someone edits a file and forgets.**
  That is the point — but the failure message has to say what to do, which is why it
  names uncommitted changes rather than reporting a failed pull.

## Validation

- Backend gates, in CI's exact scopes: `ruff check app scrapers scripts tests`,
  `ruff format --check app scrapers scripts tests`, `mypy app/ scrapers/ scripts/`.
- Full suite with `TEST_DATABASE_URL` set to a database ending in `_test`; and the
  offline run with `MEDIAWIKI_API_URL="http://invalid.invalid/api.php"`.
- Frontend: `npm run typecheck && npm run lint && npm run build`.
- The new CI job: it must fail on an unmodified checkout if a generated file is
  deliberately changed, and pass on an unmodified one. Prove it both ways.
- The refresh job's new checks: run `scripts/refresh_site.sh --dry-run` with a clean
  tree (it must get past the dirty check) and then with a deliberately dirty tree (it
  must stop with the new message, before the pull).
- The pipeline still produces an identical snapshot: run
  `python -m scripts.export_snapshot --output frontend/public/snapshot.json --check`
  and confirm `"changed": false`.

## Out of scope

- Narrowing the `mypy` suppressions. This is the biggest quality lever in the codebase
  and it is a project of its own, not a task in this one.
- Widening the scrape coverage. The coverage report shows the `Stat_Systems_Guide` page
  yielding 27 of 67 rows and two tracked pages with no parser. That is feature work.
- The `data` payload's shape. 97 distinct keys with no fixed shape per type is a
  modelling problem that would mean reshaping the parsers, the reconciler and the
  frontend together.
- Custom domain, dark mode, the News page, and deploying the API. All previously
  deferred.
