# Repository structure

```text
backend/
  actors/              Dramatiq stage handlers and launchers
  plugins/             Actor strategies, chunkers, provider adapters
  server/              FastAPI routers, schemas, and services
  shared/
    clients/           HTTP, embedding, rerank, and queue clients
    models/            Pydantic domain models
    pipeline/          Run config, URL, hashing, and artifact helpers
    storage/
      sql/             SQLAlchemy models/repositories/migrations
      vector/          Qdrant wrapper and collection naming
  outbox/              SQL outbox dispatcher
  mcp/                 Incomplete MCP prototype
  agent/               Incomplete MCP-dependent LangGraph prototype
  tests/               Pytest suite
ui/
  src/api/             Backend HTTP clients
  src/components/      Forms, tables, controls, layout
  src/pages/           Route-level React pages
infra/
  postgres/            PostgreSQL 17 + pg_textsearch build
  qdrant/              Qdrant notes/configuration
  rabbitmq/            Broker definitions and configuration
scripts/               Local reset and worker rebuild helpers
docs/                  Public documentation
sources/               Gitignored local XML source root
tmp/pipeline_run/      Gitignored run logs and source artifacts
```

`docker-compose.yml` is the runtime inventory. `pyproject.toml` is the single
source of truth for package metadata, dependency extras, and Ruff config.
