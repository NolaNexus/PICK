# PICK — Type the models, delete the unreachable calculators, close the duplication

**Status:** implemented and pushed. (The status line previously said "not pushed";
that was stale. Verified at `5f9ca0d`: all four commits below are ancestors of both
`HEAD` and `origin/master`.)

## Outcome

Four commits. The gates are green: 412 passed, ruff check/format and mypy clean with
**all seven error codes enabled**, frontend typecheck/lint/build clean, and the offline
suite passes with the wiki unreachable (408 passed, 4 skipped).

| Commit | What it did |
| --- | --- |
| `5af31c5` | removed the backend calculator API and the dead formulas maths |
| `ecb87c9` | dropped the duplicate foreign key the DDL comparison found |
| `85b4553` | typed the models and the parsers; turned the typecheck back on |
| `53fdbb9` | the docs |

**The typecheck catches things again.** All seven codes are enabled. Before, mypy found
import errors and nothing else; now it catches a wrong type, a wrong attribute and a
wrong call. Each code was removed from the suppression list only once its run was
clean.

**Zero published data changed.** The export reports `"changed": false` — the same 853
slugs, and not one field of content altered.

**The DDL did not change.** The models and the migrations now describe the same
schema, and `tests/test_schema_parity.py` keeps them that way.

## What the work found

**The models and the migrations had drifted.** The comparison the plan called for
turned up a duplicate foreign key: the initial migration declared
`items.source_page_id` twice, once inline on the column and once as a table constraint
with `ON DELETE SET NULL`. The database has therefore had two foreign keys on one
column, one of which nulls the reference and one of which does not. They behave the
same until a wiki page row is deleted, at which point the stricter one refuses the
delete. Migration `007` drops the duplicate.

The models also lacked the `server_default`s the migrations declare — `created_at`,
`detected_at`, `started_at` and `last_scraped` all get `DEFAULT now()` in the database
but not in the model. The models now match, so the two agree.

**Two incidental bugs.** `filter_tags("tabber")` was passing the tag name where
mwparserfromhell wants the `recursive` flag — it worked by accident, because a
non-empty string is truthy. And the database session factory was a module global that
was `None` until the engine was created, so every caller had to guard against it; it is
now an object with a definite type.

**The plan's `description` field was right about the shape but wrong about one
detail.** It said `description` is `NotRequired` because some parsers put it inside
`data` — that is correct, and it is `NotRequired` for the same reason. The plan also
said `slug` was optional; checking all 24 parsers showed every one of them emits it,
so it is required.

## Deviations from the plan

**The plan said the fragment types would be a separate enum.** They are not: they are
a strict subset of the types a row can hold, so one enum over all 33 is simpler and
the `is_fragment` flag in the taxonomy table carries the distinction. This was the
plan's own reasoning, applied to the enum rather than the fold table.

**`app/services/formulas.py` was renamed** to `app/services/seed_formulas.py`, which
the plan offered as an option. The module now holds only the seed data, and its name
should say so.

**The `Confidence` literal lives in `app/models/formula.py`** rather than the
schema module, so the model and the seed data share it and cannot disagree.

## Verification notes

- Every suppression was removed only after its run was clean. The order was
  `attr-defined`, `assignment`, `arg-type`, `call-arg`, `index`, then `var-annotated`
  and `misc`.
- The schema parity test was proven to catch a duplicate foreign key by adding one to
  the model and watching it fail.
- The DDL was compared statement by statement against the live database: the only
  remaining differences are alembic's own bookkeeping table and the same `nextval`
  default written two ways.
- The migration round-trips: upgrade, downgrade and upgrade again on a copy of the
  live database, with all 1,146 rows intact.
- The published snapshot is byte-identical: `"changed": false` after the models
  moved, the parsers were typed and the API lost its calculator endpoints.

## Out of scope

- **Narrowing `data` to a per-type shape.** 97 distinct keys with no fixed shape per
  type is a modelling problem that would mean reshaping the parsers, the reconciler
  and the frontend together. The TypedDict describes the *item envelope*, not the
  payload inside it.
- **A frontend test suite.** The frontend has no tests at all, and the calculators
  that ship to users are untested. That is the largest remaining gap and it is worth
  its own block of work, but it is a different toolchain (vitest) and a different
  kind of change.
- The scrape coverage gaps, the dark-mode toggle, the custom domain, the News page,
  and deploying the API. All previously deferred.

Three things, in this order:

1. **Delete the backend calculator API.** Its math is unreachable from the product
   and exists in three copies.
2. **Migrate the models to SQLAlchemy 2.0's typed style.** This is the root cause of
   five of the seven globally suppressed mypy error codes.
3. **Type the parser boundary** so the 24 parsers are checked rather than trusted.

The theme is one thing: **the typechecker currently catches almost nothing**, and the
code that would be caught is the code that touches the database and the wiki.

## Why this, and why in this order

The mypy configuration disables seven error codes globally:

```toml
disable_error_code = [
    "arg-type", "assignment", "attr-defined", "call-arg", "index", "misc", "var-annotated",
]
```

`arg-type`, `assignment`, `attr-defined` and `call-arg` are the codes that catch a
wrong type, a wrong attribute and a wrong call. With them off, the typecheck finds
import errors and nothing else.

### The root cause is one style choice

The models use the legacy `Column()` form:

```python
id = Column(BigInteger, primary_key=True)
type = Column(ItemType, nullable=False)
```

With that form, `Item.type` is typed as `Column`, not `str`. So every query in the
codebase loses its type at the first step:

```python
result = await db.execute(select(Item).where(Item.is_active.is_(True)))
items = result.scalars().all()      # list[Any], not list[Item]
```

`list[Any]` disables checking for everything downstream of it — `item.name` is `Any`,
`item.data` is `Any`, and passing either to a typed function checks nothing. That is
what `arg-type` and `attr-defined` were being suppressed for.

SQLAlchemy 2.0's `Mapped[]` / `mapped_column()` fixes this at the source: the
declaration states the Python type, and the ORM propagates it into the query results.
There are 49 column declarations across 6 model files.

### The parser boundary is the other half

All 24 page parsers return `list[dict[str, Any]]`, and their output is fed straight
into the model:

```python
item = Item(
    type=item_data["type"],       # Any -> str
    name=item_data["name"],       # Any -> str
    data=item_data.get("data", {}),
    ...
)
```

`item_data["type"]` is `Any`, so the `arg-type` check that would catch a parser
emitting a type the database does not accept cannot run. The shape is consistent
across all 24 parsers — `id`, `type`, `name`, `slug`, `data`, `image_url` — so one
`TypedDict` describes the whole boundary.

### The calculator duplication

The calculator math exists in three places:

| | Lines | Reachable from the product? |
| --- | ---: | --- |
| `frontend/src/lib/calculators.ts` + `museum.ts` | 1,057 | **Yes** — this is what users get |
| `app/services/calculators.py` | 1,037 | No — the API is local-only and `VITE_API_BASE_URL` is unset |
| `app/services/formulas.py` (8 functions) | ~70 | No — nothing imports them |

`app/services/formulas.py` holds `items_per_pan`, `digs_per_pan`, `modifier_luck`,
`golden_rule` and four more. Nothing imports them; `seed_formulas` is the only thing
imported from that module. They are dead.

`app/services/stats.py` exists for the same reason the R bridge did — it is the
Python half of a calculator feature that only the API exposed. Once the API goes it
goes too.

And the modifier distribution table — thirteen numbers — is written out three times:
`app/services/calculators.py:147`, `app/services/stats.py:11` and
`frontend/src/lib/calculators.ts:116`. The two backend copies are not even the same
function: `stats.py` normalises to 100, `calculators.py` normalises to the
modified-ore percentage.

**The frontend keeps its implementation.** It is the one users actually get, it uses
`decimal.js` for the tiny-probability arithmetic that `float` cannot hold, and it is
the only one that is exercised.

## Tasks

### 1. Delete the backend calculator API

Delete these files outright:

- `app/api/calculators.py` (181 lines)
- `app/services/calculators.py` (1,037 lines)
- `app/services/stats.py` (55 lines)
- `app/schemas/calculator.py` (535 lines)
- `tests/test_calculators.py` (698 lines)
- `tests/test_calculator_stats.py` (81 lines)

Then:

- `app/api/__init__.py` — drop the `calculators_router` import and its
  `include_router` call.
- `app/schemas/__init__.py` — drop every calculator schema from the imports and
  `__all__`. `app/schemas/calculator.py` is gone, so the whole module disappears.
- `app/services/__init__.py` — drop the four `calculate_*` re-exports and the
  `from app.services.calculators import (...)` block.
- `app/services/formulas.py` — delete the eight dead functions (`items_per_pan`,
  `size_weight_multiplier`, `digs_per_pan`, `seconds_per_dig`, `time_per_pan`,
  `modifier_luck`, `modifier_fraction`, `event_luck_multiplier`, `golden_rule`) and
  the `import math` they need. What remains is `seed_formulas`, which is the module's
  only real job. **Consider renaming the module** to `app/services/seed_formulas.py`
  so its name says what it does — it no longer has anything to do with formulas as
  maths, only with seeding the formulas table.
- `scripts/seed_formulas.py` — update the import if the module is renamed.

Check for other references: `grep -rn "services.calculators\|services.stats\|schemas.calculator"`
over `app/`, `scripts/`, `tests/`.

The API keeps `items`, `formulas`, `meta`, `search` and `export`. Those are a coherent
read API over the data, and `export/snapshot` is what the frontend would call if
`VITE_API_BASE_URL` were ever set.

### 2. Regenerate the spec and the client

```bash
.venv/bin/python -c "import json; from app.main import app; json.dump(app.openapi(), open('openapi.json','w'), indent=2)"
cd frontend && npm run generate:api
```

The spec loses six paths and the generated client loses their hooks. The
`generated-files` CI job (added in the last block of work) will catch it if this is
missed.

### 3. Migrate the models to `Mapped[]`

Rewrite the six model files in `app/models/` using SQLAlchemy 2.0's typed style:

```python
from sqlalchemy.orm import Mapped, mapped_column

class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    type: Mapped[str] = mapped_column(ItemType, nullable=False)
    source_page_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("wiki_pages.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    data: Mapped[dict[str, Any]] = mapped_column(ItemData, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(UTC), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(UTC), server_default=func.now(),
        onupdate=datetime.now(UTC), nullable=False
    )
```

The rules for each column:

- **Nullable columns** get `| None`. `image_url`, `description`, `source_page_id`,
  `group_name`, `raw_header`, `last_scraped`, `finished_at`, `status`, `error_log`.
- **`created_at` / `updated_at`** are `datetime`, not `datetime | None` — they are
  `nullable=False` with a server default, so they are always set.
- **`data`** is `dict[str, Any]`. `params` on `Formula` is `dict[str, Any]`.
- **`type`** on `Item` and `Taxonomy` is `str`. The enum is a database type, not a
  Python one — SQLAlchemy stores it as the string value, and the models already treat
  it as a string everywhere (`item.type == "relic"`).
- **`confidence`** on `Formula` is `str`, but the value is one of two. Make it a
  `Literal["approximate", "confirmed"]` — the schema already constrains it, and the
  enum exists in the file contract.

  The literal must be declared **once**. `app/models/formula.py` should own it:

  ```python
  Confidence = Literal["approximate", "confirmed"]
  ```

  and `app/services/formulas.py` should import it rather than write the strings
  again, so the seed data and the column cannot disagree. The same applies to the
  JSON Schema's `confidence` enum, which `tests/test_snapshot_contract.py` already
  compares against the file.

The `after_create` event listener in `app/models/item.py` that adds the JSON object
check stays as it is — it is a dialect detail, not a typing one.

**`app/models/taxonomy.py`** has the same treatment. Its `type` column is the same
enum.

**Watch for**: `Mapped[]` requires the annotation to be the *Python* type, and
SQLAlchemy will not infer it. Every column needs an explicit annotation.

### 4. Type the parser boundary

Add a `ParsedItem` TypedDict. It belongs in `scrapers/types.py` or `scrapers/__init__.py`:

```python
class ParsedItem(TypedDict):
    """What a page parser returns.

    Every parser produces the same shape, so the scraper can rely on it.
    """
    id: str
    type: str
    name: str
    slug: str
    data: dict[str, Any]
    image_url: str | None
    description: NotRequired[str | None]
```

The optionality was checked against all 24 parsers rather than assumed:

- **`slug` is always present.** Every parser emits it, so it is a required key. The
  scraper's fallback to `item_data.get("id")` (`app/services/scraper.py:293-296`) is
  defensive code for a case that does not happen, and it can stay as it is.
- **`image_url` is always present**, and always `None` — the scraper fills it in
  later from the wiki's image name.
- **`description` is genuinely inconsistent**, and must be `NotRequired`. Some parsers
  set it at the top level (`equipment.py:109`, `potions.py:119`, `events.py:138`,
  `minerals.py:83`, `quests.py:197`, `relics.py:66`, `runes.py:94`, `mastery.py:142`,
  `locations.py:62`, `blueprints.py:131`, `mutations.py:192`, `museum.py:29`,
  `excavations.py:286`, `formulas.py` and others); some put it inside `data` instead
  (`pans.py:43`, `shovels.py:43`, `sluices.py:46`, `geodes.py:37`); and
  `modifiers.py:39` sets it to `None`. Declaring it as required would be declaring
  something false.

  **Do not "fix" this inconsistency in this block of work.** Moving `description` to
  one place would change the published data, and the plan's acceptance criterion is
  that the snapshot does not change.

Then change each parser's return annotation from `list[dict[str, Any]]` to
`list[ParsedItem]`, and `scrapers/registry.py`'s `PARSERS` from `dict[str, Any]` to
`dict[str, Callable[[str], list[ParsedItem]] | None]`.

One consequence to expect: the parsers build their dicts with literal keys, and mypy
checks TypedDict literals strictly. A parser that returns a dict with an extra key,
or that builds the dict in two steps, will need adjusting. That is the point of the
exercise — it surfaces shape drift — but it means the 24 parsers are the bulk of the
work in this task.

`scrapers/item_page.py` returns a *different* shape — `{"name", "type", "fields",
"modifiers"}` — and is used by the enrichment service, not the page parsers. Give it
its own `ParsedItemPage` TypedDict.

### 5. Narrow the mypy suppressions, one code at a time

After tasks 1-4, run mypy with each code re-enabled and see what is left:

```bash
.venv/bin/mypy app/ scrapers/ scripts/ --enable-error-code=arg-type
```

Remove a code from `disable_error_code` only when the run is clean. The likely
outcome, in order of easiest:

- **`assignment`** and **`attr-defined`** — should fall out of task 3 alone.
- **`arg-type`** and **`call-arg`** — should fall out of tasks 3 and 4 together.
- **`index`** — probably needs `data` to be typed more precisely than
  `dict[str, Any]` in a few places.
- **`var-annotated`** — needs `params = {}` and similar to be annotated.
- **`misc`** — the broadest and least predictable; likely the last to go.

**If a code cannot be removed cleanly, do not force it.** Keep it disabled and record
in the plan why. A suppression with a stated reason is honest; a suppression that
hides a hundred errors is not. The aim is that the *core* — the models, the query
layer, the scraper, the reconciler — is checked strictly, and the parsers are checked
at their boundary.

### 6. Update the docs

- `AGENTS.md` — the calculator section says "the calculator API has six working
  endpoints". That is now wrong: the endpoint is gone. Replace it with what remains
  and why the calculators live in the frontend.
- `README.md` — "Powers calculators for modifier odds, expected value, best pan,
  museum optimization, and time-to-goal" is still true, but the calculator is now
  purely a frontend feature. The "Exposes a REST API (FastAPI) for items, formulas,
  calculators, and metadata" line must drop "calculators".
- `SETUP.md` — it lists the six calculator endpoints. Update it.
- `frontend/src/lib/calculators.ts:2` — "Calculator math ported from
  app/services/calculators.py". That file is going. Change it to say the math comes
  from the Stat Systems Guide and is the only implementation.

## Risks

- **`Mapped[]` can change runtime behaviour.** SQLAlchemy 2.0's typed style is
  mostly a typing change, but it interacts with `declarative_base()`'s attribute
  handling. The models are created by `Base.metadata.create_all` in the test
  fixture and by the alembic migrations in production, and the migrations use raw
  SQL, so the DDL should not change. **Verify** by comparing the generated DDL
  before and after: `Base.metadata.create_all` against a scratch database, then
  `pg_dump --schema-only`. Any difference in the DDL is a bug, not a formatting
  change.
- **The `type` column's Python type.** `Mapped[str]` for a column that is a database
  enum is correct — SQLAlchemy returns the string. This was checked against the code:
  the reconciler compares `item.type` to plain strings (`item.type == "relic"`,
  `item.type == "excavation_site"`) and *assigns* one (`item.type = "relic"`,
  `app/services/reconcile.py:652`). A `Mapped[ItemType]` annotation would be a lie
  about the runtime value and would break those comparisons.
- **`NotRequired` needs Python 3.11+.** The project pins `python_version = "3.11"`,
  so `typing.NotRequired` is available. `typing_extensions` is not a dependency and
  should not be added.
- **The `data` column's Python type.** `dict[str, Any]` is right for the model. The
  *parser* payload is a different thing: it is a nested structure whose shape
  depends on the item type. That stays `dict[str, Any]` — narrowing it is the
  `data` reshaping work that is out of scope.
- **Deleting the calculator API changes the public API surface.** The site does not
  use it, but anyone who pointed `VITE_API_BASE_URL` at a live deployment would lose
  those endpoints. The secret is unset and the Render deployment is gone, so there
  is no live consumer. This should be said in the commit body.

## Validation

- Backend gates in CI's exact scopes: `ruff check app scrapers scripts tests`,
  `ruff format --check app scrapers scripts tests`, `mypy app/ scrapers/ scripts/`.
- Full suite with `TEST_DATABASE_URL` set to a database ending in `_test`; and the
  offline run with `MEDIAWIKI_API_URL="http://invalid.invalid/api.php"` (the live
  wiki tests must skip, not fail).
- Frontend: `npm run typecheck && npm run lint && npm run build`.
- **The DDL must not change.** Compare `pg_dump --schema-only` of the test database
  before and after the model migration.
- **The published data must not change.** Run
  `python -m scripts.export_snapshot --output frontend/public/snapshot.json --check`
  and confirm `"changed": false`. The models' typing change must not alter a single
  published row.
- **The generated files must be current.** Regenerate and confirm no diff; the
  `generated-files` CI job does this.
- **Every suppression that is removed is removed deliberately.** Record in the
  commit body which code was enabled and what it caught.
