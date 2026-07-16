# Embeddorium documentation

Embeddorium is a local-first workbench for building, inspecting, and comparing
retrieval pipelines. It ingests web pages or local XML, preserves the
intermediate artifacts, stores chunks in PostgreSQL, writes dense vectors to
Qdrant, and supports semantic, BM25, and hybrid search.

## Start here

- New user: [Installation](getting-started/installation.md) then
  [Quick start](getting-started/quick-start.md).
- Learn the model: [Product overview](product/overview.md) and
  [Product model](product/product-model.md).
- Run retrieval: [Search concepts](concepts/search.md) and the
  [retrieval guides](guides/retrieval/run-vector-search.md).
- Extend the pipeline: [Plugin concepts](concepts/plugins.md) and the
  [plugin guides](guides/plugins/how-to-add-custom-actor-configuration.md).
- Work on the repository: [Development setup](development/setup.md).

## Documentation map

The complete, ordered page list is maintained in [navigation.md](navigation.md).
Architecture details start at [Architecture overview](architecture/overview.md).

## Local interfaces

After `docker compose up -d --build`:

| Interface | Address |
| --- | --- |
| Web UI | <http://localhost:5173> |
| FastAPI/OpenAPI | <http://localhost:8000/docs> |
| Qdrant dashboard | <http://localhost:6333/dashboard> |
| RabbitMQ management | <http://localhost:15672> |

The API and UI do not implement authentication. They are intended for a trusted
local environment; see [Security](architecture/security.md).
