---
name: verify
description: Verify a change in this repo end-to-end. Use before committing nontrivial backend, UI, or infra changes to confirm the affected flow actually works, not just that tests pass.
---

# Verify a change

Pick the layers the diff touches; always finish with the end-to-end run if the pipeline path changed.

## Backend (anything under backend/)
```sh
.venv/bin/python -m pytest backend/tests -q
ruff check . && ruff format --check .
```

## UI (anything under ui/)
```sh
cd ui && npm run lint && npm run build
```

## Infra / compose (docker-compose.yml, infra/, Dockerfiles, migrations)
```sh
docker compose config -q          # compose file validates
docker compose up -d --build      # migrate service must apply migrations cleanly
docker compose ps                 # everything healthy/running
```

## End-to-end (pipeline stages, storage, providers, search)
The mock provider makes this take seconds — no model server needed.

1. `docker compose up -d --build`, then open the UI at http://localhost:5173.
2. Providers → create a **Mock** provider (model type `embedding`).
3. Datasets → create a Web dataset with one URL, depth `0`.
4. Pipeline runs → start a run with that dataset + provider.
5. **Success:** run reaches `completed`, and the collection appears at http://localhost:6333/dashboard with sane chunk/vector counts.

If the run wedges, inspect `docs/architecture/error-handling.md` and `docs/architecture/runtime-topology.md` (or use the `pipeline-debugger` agent); reset state between attempts with `scripts/full-clean.sh`.

## Report
State plainly what was run and what was observed — actual statuses and counts, not "should work". If a check was skipped, say so.
