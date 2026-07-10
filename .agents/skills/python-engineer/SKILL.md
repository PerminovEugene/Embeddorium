---
name: python-engineer
description: Conventions for writing backend Python in this repo. Use when adding or editing code under backend/ — actors, plugins, SQLAlchemy models, Pydantic schemas, or Dramatiq workers.
---

# Python engineer

Target: Python 3.11+, Pydantic v2, SQLAlchemy 2, Dramatiq. Match the style of `backend/`.

- Type-hint everything. Prefer `X | None` over `Optional[X]`; use `list`/`dict` generics, not `typing.List`.
- Pydantic v2: `model_config`, `model_validate`, `model_dump`. No v1 `.dict()`/`Config` class.
- SQLAlchemy 2: typed `Mapped[...]` / `mapped_column`, `select()` queries, explicit sessions. No legacy Query API.
- Dramatiq actors stay small and idempotent — one stage of the pipeline each. Side effects go through the outbox, not inline.
- Plugins (chunkers, embedders) are auto-discovered — follow the existing base class and register by dropping the file in the right `backend/plugins/` dir; touch no core code.
- Fail loud: raise typed exceptions, never swallow. Log with the module logger, not `print`.
- Keep functions pure where possible; push I/O to the edges.
- Server code is one directory per feature under `backend/server/` (datasets, providers, pipeline, search, …) — new endpoints go in their feature dir, not `main.py`.
- New table/column/repository? Follow the `db-entity` skill checklist — migrations are hand-written numbered SQL files, no autogenerate.
- Layers stay separated: actors and server code use domain models from `backend/shared/models` and repos on the store; ORM types never cross out of `storage/sql/`.

## Checks before done
- `ruff check` and `ruff format` clean (config in `setup.cfg`/`pyproject.toml`).
- `.venv/bin/python -m pytest backend/tests -q` passes; add a test under `backend/tests/` for new behavior.
- New dependency added to the correct extra in `pyproject.toml` (extras are per-worker: `web`, `embed`, `embedding`, `server`, `mcp`, `agent`, `dev`) and `requirements.txt` regenerated (`pip freeze > requirements.txt`).
