# Coding conventions

## Backend boundaries

- Keep actor business logic in `handler.py`; keep Dramatiq, broker creation,
  logging context, and dependency construction in `launcher.py`.
- Read run-specific provider and actor settings from the pipeline snapshot.
- Keep strategies close to pure transformations. Persistence and queue
  handoffs belong to actors.
- Use the provider registry to build embedding clients; shared search/actor code
  should not branch on individual provider names.
- Use a `UnitOfWork` when domain writes and a downstream event must commit
  together. Give every event a stable deduplication key.
- Preserve stable chunk UUIDs as Qdrant point IDs and validate vector dimensions
  through the embed client before collection creation.

## Persistence

- Add ordered SQL migrations under
  `backend/shared/storage/sql/migrations/` for schema changes.
- Update the domain model, SQLAlchemy model, repository mapping, and tests
  together.
- Migration files are rerun on every startup and therefore must remain
  idempotent.
- Bind user input in SQL; do not format retrieval queries into raw SQL strings.

## API and UI

- Public API models use camelCase aliases. Plugin `FieldSpec.key` values and
  nested raw configuration blobs intentionally remain snake_case.
- Keep routers thin and put workflow logic in service modules.
- Prefer backend-published actor/provider field metadata over duplicate
  frontend definitions where the existing UI supports it.

## Style

Ruff is the configured formatter/linter dependency. `[tool.ruff]` in
`pyproject.toml` sets a 120-character line length. Follow the surrounding typed
Python and TypeScript patterns and add focused tests with behavior changes.
