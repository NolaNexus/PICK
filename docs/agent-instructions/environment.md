# Environment: Virtualenv, Database, `.env`

## Virtualenv

- `.venv` hard-codes its own absolute path. Renaming or moving the checkout breaks every
  script in `.venv/bin`. If paths look wrong, delete `.venv` and recreate it:

  ```bash
  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
  ```

- Invoke tools as `.venv/bin/python -m <tool>`, not `.venv/bin/<tool>`. The shebangs in
  `.venv/bin` are what break.
- `requirements.txt` holds the runtime dependencies and `requirements-dev.txt` the test and
  lint tools. `pyproject.toml` reads its dependency list from `requirements.txt`, so there
  is one list.
- The local `.venv` is Python 3.14. CI runs 3.11 and 3.12. `pyproject.toml` pins
  `target-version = "py311"` and `python_version = "3.11"`.
- `deploy/systemd/*.service` hard-code the checkout path. Update them alongside any move.

## Database

`docker compose up -d db` starts Postgres 16 on `localhost:5432` with user `pick`,
password `pick` and database `pick`. The scraper and the exporter both need `DATABASE_URL`
pointing at it.

Migrations live in `alembic/versions/`. Run them with `.venv/bin/python -m alembic upgrade head`.
`alembic/env.py` sets `transaction_per_migration=True`, so each revision gets its own
transaction. That is what lets one revision add an enum value and a later one use it;
see [data-model.md](data-model.md). For schema changes, see [data-model.md](data-model.md).

## `.env` is dotenv, not shell

- `scripts/refresh_site.sh` parses `.env` line by line rather than sourcing it. Values
  such as `USER_AGENT=PICK/1.0 (Prospecting Information & Community Kit)` contain spaces and
  parentheses.
- Do not `source .env` in a shell.
- `app/config.py` reads the same file through `pydantic-settings` (`env_file=".env"`). A
  value already set in the environment wins over the file.

## Systemd

The scrape runs locally from a systemd timer. The unit files are in `deploy/systemd/`, and
the install steps and deploy-key setup are in `SETUP.md`.
