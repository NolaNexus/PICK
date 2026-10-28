---
description: Regenerate the committed OpenAPI spec and the frontend API client
---

`openapi.json` and `frontend/src/api/` are generated and committed. Regenerate
both after changing any route or schema.

```bash
cd /home/nola/Desktop/PICK

.venv/bin/python -c "import json; from app.main import app; json.dump(app.openapi(), open('openapi.json','w'), indent=2)"

cd frontend && npm run generate:api
```

The spec is written with `indent=2` and **no trailing newline**. The orval
config (`frontend/orval.config.mjs`) reads `../openapi.json` and writes
`frontend/src/api/`.

Regenerating with unchanged input must produce no diff:

```bash
cd /home/nola/Desktop/PICK && git status --short openapi.json frontend/src/api/
```

If that shows changes you did not expect, the spec and the app disagree — check
whether a route was added without being registered in `app/api/__init__.py`.

Never hand-edit `frontend/src/api/pick.ts` or `frontend/src/api/client.ts`. The
first is orval output and is overwritten on the next run; the second is
hand-written. Note that orval writes only `pick.ts`: its `mode` is `import`, so it
does not emit a separate schemas file, and the `pick.schemas.ts` that the
`tags-split` era left behind has been deleted.

## The snapshot contract

The published file has a contract of its own, in `snapshot.schema.json` at the
root of the repository. The frontend's types are generated from it:

```bash
cd /home/nola/Desktop/PICK/frontend && npm run generate:snapshot-types
```

This writes `frontend/src/lib/snapshot.types.ts`. Never hand-edit that file
either.

When you change what the snapshot holds, change the schema **first**, then
regenerate the types, then regenerate the API spec. The order matters: the
schema is the contract, and everything else follows it.

Regenerating with unchanged input must produce no diff:

```bash
cd /home/nola/Desktop/PICK
git status --short snapshot.schema.json frontend/src/lib/snapshot.types.ts
```
