#!/usr/bin/env bash
#
# Scrape the wiki, refresh the published snapshot, and commit it.
#
# Miraheze answers GitHub-hosted runners with 403 Forbidden, so the scrape runs
# on the machine that holds this checkout. It is driven by the systemd timer in
# deploy/systemd/.
#
# Fail-closed by design: a scrape that reaches no page, or an export that would
# erase the catalogue, aborts before anything is committed.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="$ROOT/.venv/bin/python"
SNAPSHOT="$ROOT/frontend/public/snapshot.json"
STALE_DAYS=3
FULL=0
DRY_RUN=0

for arg in "$@"; do
  case "$arg" in
    --full) FULL=1 ;;
    --dry-run) DRY_RUN=1 ;;
    *)
      echo "unknown argument: $arg" >&2
      exit 2
      ;;
  esac
done

# systemd does not read the repository .env, so load it here. The file is
# dotenv, not shell, so parse it instead of sourcing it: values such as the
# User-Agent contain spaces and parentheses that a shell would choke on.
load_env() {
  local file="$1"
  [ -f "$file" ] || return 0
  while IFS='=' read -r key value || [ -n "$key" ]; do
    case "$key" in
      '' | \#*) continue ;;
    esac
    # A variable already set in the environment wins over the file.
    if [ -n "${!key:-}" ]; then
      continue
    fi
    value="${value%$'\r'}"
    value="${value#\"}"
    value="${value%\"}"
    value="${value#\'}"
    value="${value%\'}"
    export "$key=$value"
  done <"$file"
}

load_env "$ROOT/.env"

notify() {
  local title="$1"
  local body="$2"
  if [ -n "${NTFY_TOPIC:-}" ]; then
    curl -fsS -m 10 \
      -H "Title: $title" \
      -H "Priority: high" \
      -H "Tags: warning" \
      -d "$body" \
      "https://ntfy.sh/${NTFY_TOPIC}" >/dev/null || true
  fi
}

fail() {
  echo "FAILED: $1" >&2
  notify "PICK refresh failed" "$1"
  exit 1
}

snapshot_age_days() {
  "$PY" - "$SNAPSHOT" <<'PYTHON' 2>/dev/null || echo ""
import json
import sys
from datetime import datetime, timezone

try:
    with open(sys.argv[1], encoding="utf-8") as handle:
        generated = json.load(handle)["generated_at"]
    moment = datetime.fromisoformat(generated.replace("Z", "+00:00"))
    print(int((datetime.now(timezone.utc) - moment).total_seconds() // 86400))
except Exception:
    print("")
PYTHON
}

[ -x "$PY" ] || fail "no virtualenv at $PY; create one and install requirements.txt"

# Warn before the run if the data is already stale: that means earlier runs
# silently did nothing, which is exactly what this job exists to catch.
AGE="$(snapshot_age_days)"
if [ -n "$AGE" ] && [ "$AGE" -ge "$STALE_DAYS" ]; then
  notify "PICK data is stale" "The published snapshot is ${AGE} days old."
fi

echo "==> Checking the checkout"
# The job publishes the snapshot from this checkout, so the checkout has to be
# clean. A stray edit would otherwise fail the pull below with a message that
# reads like a network problem, or be left behind by the commit at the end.
if [ -n "$(git status --porcelain)" ]; then
  fail "the checkout has uncommitted changes; commit or stash them first"
fi

echo "==> Updating the checkout"
git pull --ff-only --quiet || fail "the checkout could not be updated; resolve it by hand"

echo "==> Starting the database"
# The database container may have been created by an older compose project
# (the checkout has been renamed once), so start it by name when it exists and
# let compose create it otherwise.
if docker inspect pick-db >/dev/null 2>&1; then
  docker start pick-db >/dev/null
else
  docker compose up -d db >/dev/null
fi

for _ in $(seq 1 30); do
  if docker exec pick-db pg_isready -U pick -d pick >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
docker exec pick-db pg_isready -U pick -d pick >/dev/null 2>&1 ||
  fail "the database did not become ready"

echo "==> Migrating"
"$PY" -m alembic upgrade head || fail "the database migration failed"

echo "==> Scraping"
if [ "$FULL" -eq 1 ]; then
  "$PY" -m scripts.scraper --full || fail "the scrape reached no page; nothing was published"
else
  "$PY" -m scripts.scraper || fail "the scrape reached no page; nothing was published"
fi

echo "==> Seeding formulas"
"$PY" -m scripts.seed_formulas || fail "seeding formulas failed"

echo "==> Exporting the snapshot"
EXPORT_ARGS=(--output "$SNAPSHOT")
if [ "$DRY_RUN" -eq 1 ]; then
  EXPORT_ARGS+=(--check)
fi
if ! RESULT="$("$PY" -m scripts.export_snapshot "${EXPORT_ARGS[@]}")"; then
  echo "$RESULT"
  fail "the snapshot export was refused; nothing was published"
fi
echo "$RESULT"

echo "==> Reporting coverage"
"$PY" -m scripts.coverage_report 2>&1 | sed -n '1,40p' || true

case "$RESULT" in
  *'"changed": true'*) CHANGED=1 ;;
  *) CHANGED=0 ;;
esac

if [ "$CHANGED" -eq 0 ]; then
  echo "==> Snapshot unchanged; nothing to publish"
  exit 0
fi

if [ "$DRY_RUN" -eq 1 ]; then
  echo "==> Dry run: the snapshot would be published, but nothing was written"
  exit 0
fi

echo "==> Publishing"
git add "$SNAPSHOT"
# Only the snapshot may be committed. Anything else that got staged would be
# published as part of a scrape commit, which is not what the job is for. Git
# prints paths relative to the repository root, so the snapshot is compared
# that way too.
STAGED="$(git diff --cached --name-only)"
SNAPSHOT_RELATIVE="frontend/public/snapshot.json"
if [ "$STAGED" != "$SNAPSHOT_RELATIVE" ]; then
  fail "something other than the snapshot is staged; refusing to publish"
fi
git commit -m "chore: refresh the wiki snapshot" >/dev/null
git push origin HEAD:master || fail "the snapshot commit could not be pushed"

echo "==> Published"
