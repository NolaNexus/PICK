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

Never hand-edit `frontend/src/api/pick.ts` or `pick.schemas.ts`. They are
orval output and are overwritten on the next run.
