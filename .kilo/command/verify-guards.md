---
description: Prove the publishing pipeline cannot erase the catalogue
---

The pipeline is fail-closed, and that property is worth checking after any change
to the scraper, the exporter, or the refresh script. Two things must hold:

1. A scrape that reaches nothing must fail and leave the published file untouched.
2. An export that would empty the catalogue must be refused.

```bash
cd /home/nola/Desktop/PICK

SNAPSHOT=frontend/public/snapshot.json
BEFORE=$(md5sum "$SNAPSHOT" | cut -d' ' -f1)

# 1. a blocked scrape must fail, and the file must be byte-identical
MEDIAWIKI_API_URL="http://invalid.invalid/api.php" \
  .venv/bin/python -m scripts.scraper; echo "exit: $?"

AFTER=$(md5sum "$SNAPSHOT" | cut -d' ' -f1)
[ "$BEFORE" = "$AFTER" ] && echo "PASS: the snapshot was not touched" || echo "FAIL: the snapshot changed"
git status --porcelain -- "$SNAPSHOT"
```

The unit tests pin the same rules and are faster to run. They need the test
database, so pass the URLs:

```bash
TEST_DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick_test" \
DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick" \
  .venv/bin/python -m pytest tests/test_export_guard.py tests/test_scrape_resilience.py -q
```

`tests/test_export_guard.py` covers the refusals (an empty snapshot over a full
one, and a drop of more than 20%). `tests/test_scrape_resilience.py` runs the
scrape against the fixtures in `tests/fixtures/`, so it never touches the
network.

The exporter has a dry-run mode that reports what it would do and writes
nothing:

```bash
.venv/bin/python -m scripts.export_snapshot --output frontend/public/snapshot.json --check
```

It must print `"written": false` and leave the file's checksum unchanged.
