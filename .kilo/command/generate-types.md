---
description: Regenerate the frontend's committed types from the snapshot contract
---

The published file has a contract of its own, in `snapshot.schema.json` at the
root of the repository. The frontend's types are generated from it:

```bash
cd /home/nola/Desktop/PICK/frontend && npm run generate:snapshot-types
```

This writes `frontend/src/lib/snapshot.types.ts`. Never hand-edit that file — it
is overwritten on the next run.

Regenerating with unchanged input must produce no diff:

```bash
cd /home/nola/Desktop/PICK
git status --short snapshot.schema.json frontend/src/lib/snapshot.types.ts
```

When you change what the snapshot holds, change the schema **first**, then
regenerate the types, then export the snapshot. The order matters: the schema is
the contract, and everything else follows it.

```bash
cd /home/nola/Desktop/PICK
.venv/bin/python -m scripts.export_snapshot
```

`scripts/export_snapshot.py` validates the payload against the schema before
writing it, so a mismatch fails the export rather than shipping.

## There is no API client

There used to be a second generated artefact: the OpenAPI spec and the orval
client under `frontend/src/api/`. Both were removed along with the API layer —
nothing deployed the API, no frontend code called it, and the exporter writes the
snapshot directly rather than through a route. `npm run generate:api` no longer
exists.

If a programmatic interface is needed, the dataset is `snapshot.json` and its
contract is `snapshot.schema.json`.
