---
name: db-entity
description: Checklist for adding or changing a persisted entity (Postgres table + domain model + repository). Use when adding a table, column, SQL migration, or repository under backend/shared/storage/sql/.
---

# Persisted entity

Adding an entity touches six places. Miss one and it fails at runtime, not import time — walk the whole list.

1. **Domain model** — Pydantic model in `backend/shared/models/<entity>.py`; export it from `backend/shared/models/__init__.py`. Actors, server, and repos speak this type, never the ORM.
2. **ORM model** — `backend/shared/storage/sql/models/<entity>.py`, class `<Entity>ORM(Base)`, typed `Mapped[...]` / `mapped_column`. Follow the house columns: UUID pk `default=uuid.uuid4`, `created_at` as `DateTime(timezone=True)` with `server_default=sql_text("now()")`.
3. **Migration** — next-numbered plain SQL file in `backend/shared/storage/sql/migrations/` (`NNN_verb_what.sql`). Migrations are applied in filename order by the Compose `migrate` service or `python -m backend.shared.storage.sql.migrate`. There is no autogenerate: the SQL must match the ORM exactly (types, nullability, defaults, indexes). Never edit an already-applied migration — add a new one.
4. **DTO mapper** — `_to_<entity>(orm)` in `backend/shared/storage/sql/model_to_dto.py`.
5. **Repository** — `backend/shared/storage/sql/repositories/<entity>_repo.py`. Engine injected in `__init__`, short-lived `Session(self.engine)` per method, `select()` statements, return domain models (via the mapper) — never leak ORM objects.
6. **Store wiring** — instantiate the repo as an attribute in `SqlStore.__init__` (`backend/shared/storage/sql/sql_store.py`).

Schema changes to an existing entity follow the same list minus the repo scaffold: new migration + ORM + domain model + mapper stay in sync.

## Checks before done
- Fresh-volume `docker compose up` applies the new migration cleanly (or run the migrate module against a clean DB).
- Round-trip through the repo works: create → get returns an equal domain model.
- A test under `backend/tests/` covers the new repo behavior.
