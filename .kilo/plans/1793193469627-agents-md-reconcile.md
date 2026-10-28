# File the known gaps as GitHub issues

**Status:** implemented.

## Context

The previous plan (also `1793193469627-agents-md-reconcile.md`, before it was
repurposed) closed four documentation gaps and is implemented and pushed.
Separately, five known gaps were identified and listed for the user, who asked for
issues to be opened for all of them.

While researching them to write accurate issue bodies, a **sixth and more severe
defect** turned up: the Museum calculator is broken end-to-end, not merely missing
a feature. It replaces the "mode select does nothing" gap with a larger one. The
user confirmed the Museum issues should be **one issue**, not three.

No code changes to the application. This plan files **four issues** covering the
five gaps, and adds the issue templates as a commit.

## What to file, and the evidence for each

Every claim below was verified against the code, not inferred.

### Issue 1 — the Museum calculator returns empty results (bug)

Three independent defects, each fatal on its own. All must be fixed for the tab to
work, which is why they are one issue.

**(a) Rarity casing mismatch.** `frontend/src/lib/museum.ts:22` defines
`RARITY_ORDER = ["Common", "Uncommon", "Rare", ...]` in title case, and
`calculateMuseumComparison` iterates exactly those strings, looking up
`oreDatabase[`${oreName}|${rarity}`]` (`:282`, `:296`). But
`frontend/src/pages/CalculatorsPage.tsx:132` and `:246` seed the user's ore rows
with `rarity: 'common'` — lowercase — and `:594` accepts free text. `availableOres`
is bucketed by the ore's own typed rarity (`:236-242`), then only the `RARITY_ORDER`
buckets are read (`:262`). A lowercase `common` ore lands in a bucket nobody reads.
The default ore row contributes nothing.

**(b) The ore data is nested where the code reads it flat.** The snapshot stores
museum ore data at `data.museum = { rarity, max_boost, bonus_stat, min_weight_kg }`
— see `mineral-amber`, `frontend/public/snapshot.json:11784-11789`.
`CalculatorsPage.tsx:257` stores the whole `data` object as the ore record, but
`museum.ts:137-139` reads `oreData.min_kg`, `oreData.bonus_stat`,
`oreData.max_boost` at the **top level**. So `bonus_stat` and `max_boost` are
undefined, and the weight field is not merely nested but *differently named*:
the data has `min_weight_kg`, the code wants `min_kg`. Every boost computes to 0.

**(c) The page's ore database is discarded.** `CalculatorsPage.tsx:250-265` builds
`oreDb` from the snapshot. `calculateMuseumOptimizer` never accepts it — it builds
its own at `museum.ts:588-591` with `oreDatabase[key] = {} as OreData`, i.e. empty
objects for every ore. The page's `oreDb` work is thrown away.

**Observed effect.** The Museum tab shows empty slot recommendations and zero
stats. The render block (`CalculatorsPage.tsx:627-656`) shows only
`slot_recommendations` and `total_stats`; `by_rarity`, `weight_gate_info` and
`unlock_costs` are computed by `calculateMuseumOptimizer` (`museum.ts:562-568`) and
**never rendered**.

**(d) The `mode` select is dead.** `museumSchema.mode`
(`CalculatorsPage.tsx:75`) offers `optimize | project | weight_gate |
unlock_cost`. `values.mode` is never read — `handleMuseumSubmit` (`:247-278`)
passes only `availableOres`, `unlockedDisplays`, `targetStats` and `sizeBoost`.
The three modes map exactly onto the three unrendered outputs, so the select
promises views that do not exist.

**Also note:** `unlockedDisplays` is hard-coded to `[]` (`:269`), so the calculator
never sees the player's current museum.

### Issue 2 — `calculateEV` uses price as a drop chance (bug)

`frontend/src/lib/calculators.ts:247-252`:

```ts
const dropChance = new Decimal(item.base_price ?? 0) // placeholder: actual drop chance field varies
const price = new Decimal(item.base_price ?? 0)
totalEv = totalEv.plus(dropChance.times(price).times(weightMultiplier(0)))
```

`evPerPan` is therefore `Σ(base_price² × 1)`. The real formula is
`Σ(drop_chance × price × weight_multiplier)`; the code's own comment says so.

The good news, verified: **the real drop chances are already in the snapshot.**
Minerals carry `data.chances[]` with `chance_percent` and `one_in` — see
`mineral-amber`, `snapshot.json:11791-11812` (`chance_percent: 0.05837`,
`one_in: 1713`). No new scraper field is needed.

Two smaller defects in the same function:

- `inputs.luck` and `inputs.quality` are accepted (`:217-218`) and then ignored.
- `weightMultiplier(0)` is hard-coded, so the weight multiplier never applies.
- `base_weight` is collected in the UI (`CalculatorsPage.tsx:363`) and passed in
  (`:150`) but is never used by the maths.

The existing test `frontend/src/lib/calculators.test.ts` pins the current behaviour
with a `TODO` comment, so it will need updating with the fix.

### Issue 3 — the frontend has mixed indentation (enhancement)

`frontend/src/lib/calculators.ts` (322 tab-indented lines) and
`frontend/src/lib/museum.ts` (469) use **tabs**. Everything else under
`frontend/src/` uses **two spaces**. `frontend/.prettierrc` says `tabWidth: 2` with
no `useTabs`, so those two files disagree with the config as well as with their
neighbours.

Why it matters: CI never runs `prettier --check`. The `build-frontend` job runs
`typecheck`, `test`, `lint` and `build` only (`.github/workflows/ci.yml:135-161`),
and the only `format` step in the workflow is `ruff format --check` on the Python
side (`:28-29`). So running `npm run format` across `src/` would rewrite ~790
lines of those two files, bury a real change in whitespace, and **nothing would
warn you**.

Note the two test files `calculators.test.ts` and `museum.test.ts` match their
(tab-indented) modules; `snapshot.test.ts` and `taxonomy.test.ts` match their
(2-space) modules. The convention is "match the file you are editing".

The fix is a whitespace-only commit re-indenting those two source files to 2 spaces,
after which `npm run format` becomes safe across `src/`.

### Issue 4 — `ruff format` fails on `alembic/` (chore)

`ruff format --check alembic/` reports 4 files needing reformatting, while
`ruff format --check app scrapers scripts tests` passes with 110 files already
formatted.

CI never sees it: `.github/workflows/ci.yml:29` runs
`ruff format --check app scrapers scripts tests` — `alembic/` is simply not in the
scope. `pyproject.toml` has no `extend-exclude`, so the directory is not excluded
either; it is just unchecked.

Two acceptable resolutions, and the issue should say so rather than dictate:
re-format the 4 files, **or** add `alembic/` to the CI scope (which would require
re-formatting them anyway). What is not acceptable is leaving it unchecked,
because a migration edited by hand will not match the formatter.

### Issue 5 — the repo has no issue tracker in use (chore)

`NolaNexus/PICK` has issue tracking enabled and ten labels, but **zero issues had
ever been created** — verified four ways: `list_issues` (open and all),
`search_issues` (scoped and global), `gh issue list --state all`, and
`gh repo view` → `.issues.totalCount == 0`. There were also no pull requests and
no issue templates.

Worth a small housekeeping job: add issue templates so future work has
somewhere to be recorded, and so the Copilot Coding Agent has issues to pick up.

**This one was done as committed work rather than filed as an issue** — see
"How they were filed" below. The templates landed in commit `19be56e`, and
`AGENTS.md` gained an "Issues" section in commit `9ceb1f2` recording both the
templates and the fact that issue types cannot be set on this repository.

### Not an issue — already handled

The `calculateEV` placeholder and the dead `mode` select are the only two of the
five original gaps that are real defects; the other three are cosmetic or already
documented in `AGENTS.md`. Issue #1 supersedes the "mode select does nothing" item
because the select is not merely inert — the whole tab is inert.

## How they were filed

All went to `NolaNexus/PICK`. The repo's labels are `accessibility`, `bug`,
`documentation`, `duplicate`, `enhancement`, `help wanted`, `good first issue`,
`invalid`, `question`, `wontfix`. There is **no `chore` label** — verified against
`gh label list`.

**Issue types do not work on this repository, so the labels carry the split.**
GitHub's issue types are an *organisation* feature, and `NolaNexus/PICK` is
user-owned: `GET /repos/NolaNexus/PICK` returns `owner.type == "User"`. The
`GET /repos/{owner}/{repo}/issue-types` endpoint lists the three defaults
(`Task`, `Bug`, `Feature`, all `is_enabled: true`) because it lists types
"inherited from the repository owner" — but for a user-owned repo there is no
owner to inherit from, so assigning one is a **silent no-op**. Every attempt
returns `200` with `issueType: null` and records no event on the issue timeline:
REST `-f type=Bug`, REST `-F issue_type_id=431597676`, GraphQL `issueTypeId`,
GraphQL `issueType: {issueTypeId, suggest}`, and creation-time `issueTypeId`.
This is not a permission problem — the token has `repo` and the account has
`admin` on the repo. The `orgs/NolaNexus/issue-types` endpoint 404s because
there is no organisation.

| # | GitHub | Title | Label |
| --- | --- | --- | --- |
| 1 | #1 | Museum calculator returns empty results: rarity casing, nested ore data, and a discarded ore database | `bug` |
| 2 | #6 | `calculateEV` uses `base_price` as the drop chance, so EV/pan is price squared | `bug` |
| 3 | #7 | Normalise the frontend's mixed tab/space indentation so `npm run format` is safe | `enhancement` |
| 4 | #8 | `ruff format` fails on `alembic/`, a directory CI never checks | `enhancement` |
| 5 | commit `19be56e` | Add issue templates so work has somewhere to be tracked | — |

Issue 5 was done as committed work rather than an issue, because it is the
enabling step: the templates carry the type information that the type field
cannot, and a reporter picks the template that matches their work. The three
templates are `bug_report.yml` (`bug`), `feature_request.yml` (`enhancement`) and
`task.yml` (`enhancement`), plus `config.yml` with
`blank_issues_enabled: false`.

Each issue body follows the repo's commit convention — say **what** is broken and
**why it matters**, then the acceptance criteria — and includes the verified
file:line references so a reader can check the claim without hunting.

**Do not assign the Copilot Coding Agent** for issues #1 and #6 without a decision
first: both need the fix's *shape* agreed (for #1, whether the ore database
becomes an input to `calculateMuseumOptimizer` or the data is flattened in the
page; for #6, whether the EV form takes a drop-chance column or reads the
snapshot's `chances[]` directly). Issues #7 and #8 are mechanical and can be
assigned freely.

## Validation

After filing, confirm:

```bash
gh issue list --repo NolaNexus/PICK --state all --limit 10
gh issue view <n> --repo NolaNexus/PICK
```

Expected: **four** open issues with the titles above, each with its label and a body
citing the files it concerns, plus the four templates in `.github/ISSUE_TEMPLATE/`.

Verified on completion:

- #1 `bug` — 4926-character body, cites `frontend/src/lib/museum.ts:22`,
  `frontend/src/pages/CalculatorsPage.tsx:132`, `frontend/public/snapshot.json:11784`
- #6 `bug` — 4091-character body, cites `frontend/src/lib/calculators.ts:244`,
  `frontend/public/snapshot.json:11791`
- #7 `enhancement` — 3044-character body, cites the four tab-indented files and
  `.github/workflows/ci.yml`
- #8 `enhancement` — 3471-character body, cites `.github/workflows/ci.yml:28` and
  `pyproject.toml`
- Templates: `bug_report.yml`, `feature_request.yml`, `task.yml`, `config.yml`

**No issue types.** They cannot be set on this repository — see "How they were
filed" above. The validation is therefore on labels, not types.

## Risks

| Risk | Mitigation |
| --- | --- |
| Filing a duplicate of an existing issue | The repo had zero issues, verified four ways. Re-checked with `gh issue list --state all` immediately before creating. |
| Issue #1's body being read as a single small bug | The body leads with "The Museum calculator tab always shows empty slot recommendations and zero stats" and then lists the three independent causes, since fixing one alone still leaves it broken. |
| The `chore` label not existing | Verified: the label list has no `chore`. `enhancement` is used instead, and `documentation` was not needed once the templates landed as a commit. |
| Bodies getting stale as the code moves | Each body includes the file:line references and states they were verified against commit `3439db5`, so a future reader knows what was true when. |
| Probe issues left behind during API diagnosis | Four probes were created while working out the issue-type API and all four were deleted. The repo went from zero issues to exactly the four above. Creating real issues as probes was the wrong tool; a placeholder title would have avoided it. |

## Out of scope

- Fixing any of the issues. This plan only files them.
- Choosing the fix shape for issues #1 and #6 — that is a design decision for
  whoever picks them up, and it is why they are not pre-assigned.
- The `alembic/` re-format itself, and the frontend re-indent itself.
- Assigning the Copilot Coding Agent to any issue.
