<div align="center">

<img src="docs/assets/embeddorium-logo.png" alt="Embeddorium" width="170">

# Embeddorium

**A local-first retrieval pipeline workbench.** Ingest, inspect, search, and
compare RAG data without treating the pipeline as a black box.

![Python](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)
![Dramatiq](https://img.shields.io/badge/pipeline-Dramatiq-orange)
![Qdrant](https://img.shields.io/badge/vectors-Qdrant-DC244C)
![License](https://img.shields.io/badge/license-Apache%202.0-blue)

</div>

## What Embeddorium does

Embeddorium runs a visible, durable pipeline:

```text
source -> fetch -> filter -> parse -> chunk -> embed -> store -> search -> compare
```

It can:

- Ingest a web seed and discovered same-origin links, or local XML files.
- Preserve raw and parsed artifacts alongside per-source logs.
- Select auto-discovered chunker and provider plugins per run.
- Use mock, Ollama, or OpenAI-compatible embedding providers.
- Search a completed run with semantic vectors, PostgreSQL BM25, or hybrid RRF.
- Optionally rerank hybrid results through an HTTP cross-encoder endpoint.
- Persist searches and compare their chunks, documents, and ranks in Search Lab.

The pipeline uses PostgreSQL for state and chunk text, Qdrant for dense vectors,
RabbitMQ/Dramatiq for actor messages, FastAPI for the API, and React/Vite for the
UI.

## Quick start

You need Git and Docker with Compose v2. The first run can use random mock
vectors, so no model server is required.

```sh
git clone https://github.com/PerminovEugene/web-knoweladge-indexer.git embeddorium
cd embeddorium
cp .env.example .env
docker compose up -d --build
```

Open <http://localhost:5173>, then:

1. **LLM Providers**: create a Mock / Embedding provider.
2. **Datasets**: create a Web dataset.
3. **Pipelines**: create a pipeline using that dataset/provider. Disable child
   links for a bounded single-page run.
4. Select the pending pipeline and launch it.
5. **Indexing Runs**: wait for `completed` and inspect its targets.
6. **Search**: select the completed run. Use BM25 for deterministic first
   results; mock semantic vectors are random.

Detailed instructions: [Installation](docs/getting-started/installation.md) and
[Quick start](docs/getting-started/quick-start.md).

## Local interfaces

| Interface | Address |
| --- | --- |
| UI | <http://localhost:5173> |
| API and OpenAPI | <http://localhost:8000/docs> |
| Qdrant dashboard | <http://localhost:6333/dashboard> |
| RabbitMQ management | <http://localhost:15672> |

The API has no authentication and is intended for a trusted local environment.

## Documentation

- [Documentation home](docs/index.md)
- [Complete navigation](docs/navigation.md)
- [Product overview](docs/product/overview.md)
- [Concepts](docs/concepts/ingestion-pipelines.md)
- [Retrieval guides](docs/guides/retrieval/run-vector-search.md)
- [Architecture](docs/architecture/overview.md)
- [Development](docs/development/setup.md)
- [Known limitations](docs/product/limitations.md)

## Project status

The package version is `0.1.0`, with no tagged releases in the repository.
Important current constraints include XML-only local ingestion, unenforced crawl
depth/cross-domain settings, no API authentication, one-thread workers, and an
incomplete MCP/agent prototype. See the limitations page for the full verified
list.

## Repository layout

```text
backend/       actors, plugins, API, storage, tests
ui/            React/Vite application
infra/         PostgreSQL, RabbitMQ, and Qdrant support
scripts/       local reset and worker rebuild helpers
docs/          product, guides, architecture, and development docs
sources/       gitignored local XML source root
```

## Contributing

See [Contributing](docs/contributing.md). The core checks are:

```sh
.venv/bin/python -m pytest backend/tests -q
ruff check .
ruff format --check .
cd ui && npm run lint && npm run build
```

## License

Apache License 2.0. See [LICENSE.md](LICENSE.md).
