# AGENTS.md

## Project
MediaWiki (Miraheze "Prospecting!") → PostgreSQL (raw/parsed) → JSON export → Astro static site → GitHub Pages. Python package: `pick-pipeline` v0.1.0.

## Commands
Run backend entry points via the repo venv: `.venv/bin/python -m <module>`.

- `pick` is **not installed** in `.venv` — prefix module runs with `PYTHONPATH=src` or `pip install -e .`.
- Tests: `.venv/bin/python -m pytest` (pytest: `testpaths = ["tests"]`, `addopts = "-q --tb=short"`)
- Single test: `.venv/bin/python -m pytest tests/test_pipeline_e2e.py -q`
- Lint: `.venv/bin/python -m ruff check .` — currently failing: 13 fixable errors (7× `I001` unsorted imports, 6× `F401` unused imports); autofix: `ruff check --fix .`
- Format: `.venv/bin/python -m ruff format --check .` — currently 8 files would be reformatted
- Typecheck: `.venv/bin/python -m mypy src/ tests/` — currently clean
- Migrations: `.venv/bin/python -m alembic upgrade head` (alembic.ini: `script_location = alembic`, `prepend_sys_path = src`; URL hard-coded)

Gate order when it matters: lint → format → typecheck → test — `ruff check . && ruff format --check . && mypy src/ tests/ && pytest`.

## CLI
- `src/pick/cli.py` Click group (`refresh` with `--mode` default `incremental`, `backfill`) has no `__main__` guard and no console script — `python -m pick.cli ...` exits 0 without running.
- Working invocation: `PYTHONPATH=src .venv/bin/python -c "from pick.cli import cli; cli()" refresh --mode=incremental`
- `deploy/pick-refresh.service` + `deploy/pick-refresh.timer` (daily 04:00, `Persistent=true`) wrap this.

## Setup / env
- Python `>=3.11,<3.12` (3.11 locally; no 3.12+ syntax).
- Postgres: `docker compose up -d db` (postgres:17-alpine; user/pass/db `postgres`/`postgres`/`pick`; 127.0.0.1:5432). DB-backed tests need it running.
- Env: copy `.env.example` → `.env`; `Settings` (pydantic-settings) reads it (`env_file = ".env"`).

## Layout
- Pipeline: ingest (`src/pick/ingest`; raw schema in `alembic/versions/001_initial_raw_layer.py`: `raw.wiki_page`, `raw.page_revision`, `raw.ingest_run`, `raw.ingest_checkpoint`) → parse (`src/pick/parse`) → export → publish to `public/`.
- `src/pick/{cli,config,ingest,parse,wiki}`; empty placeholder dirs `src/pick/{analytics,export,quality}`; `views/sql/` empty.
- `public/` = generated data + site + CI (`public/README.md`: meant to become its own repo e.g. `pick-site`; pipeline writes exports into `./data/`, Actions builds `./site/`, deploys Pages). Data: `public/data/{items.json,meta.json,_schema/item.schema.json}`; Astro config `public/site/astro.config.mjs` (static, base `/pick-site`).

## CI / deploy
- No CI at repo root; workflows in `public/.github/workflows/` (`deploy.yml`, `validate-data.yml`).
- Deploy: push to `main` touching `data/**`, `site/**`, or the workflow file → node 22 → `npm ci` + `npm run build` in `public/site` → upload `site/dist` → deploy Pages. `public/site/` currently lacks `package.json`/`package-lock.json`, so the build step is not runnable yet.

## Wiki
- API: `https://prospecting.miraheze.org/w/api.php`; `WIKI_MAXLAG=5`; user agent `PICK-pipeline/0.1`.
- Wiki reachable only from local machine (Miraheze 403s CI runners) — no scrape workflow in CI, no wiki-dependent tests.

## Testing quirks
- Only `tests/test_pipeline_e2e.py` (3 tests); DB-backed test needs local Postgres.
- Parser fixture: tests expect `tests/fixtures/wikitext/Minerals.wiki`, actual fixture is `minerals.wiki` (lowercase) — `test_parser_fixture` silently skips.

## Toolchain quirks
- ruff ≥0.17: top-level `[tool.ruff] select` deprecated → move to `[tool.ruff.lint] select`.
- pydantic v2: class-based `Config` on `BaseSettings` deprecated → use `model_config = SettingsConfigDict(...)`.
- Alembic: `alembic/env.py` sets `target_metadata = None` → autogenerate unsupported.

## Instructions
- No repo-local Kilo config (`kilo.json`) or instruction files in this checkout yet; this file is the agent instruction source.
