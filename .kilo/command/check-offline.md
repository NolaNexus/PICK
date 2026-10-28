---
description: Run the test suite with the wiki unreachable, the way a CI runner sees it
---

Miraheze answers GitHub-hosted runners with `403 Forbidden` for every request, so
the suite has to pass with the wiki down. This is the check that proves no test
depends on the network.

```bash
cd /home/nola/Desktop/PICK

TEST_DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick_test" \
DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick" \
MEDIAWIKI_API_URL="http://invalid.invalid/api.php" \
  .venv/bin/python -m pytest -q
```

Expect the live-wiki tests to **skip** (they are marked `requires_wiki`), not
fail. A failure here means a test reached for the network and would break CI.

Compare with the online run, which should pass everything:

```bash
TEST_DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick_test" \
DATABASE_URL="postgresql+asyncpg://pick:pick@localhost:5432/pick" \
  .venv/bin/python -m pytest -q
```
