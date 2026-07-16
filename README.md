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

## Documentation

### Root

1. [Home](#embeddorium)
2. [Glossary](docs/glossary.md)
3. [FAQ](docs/faq.md)
4. [Changelog](docs/changelog.md)
5. [Contributing](docs/contributing.md)

### Product

1. [Overview](docs/product/overview.md)
2. [Goals and non-goals](docs/product/goals-and-non-goals.md)
3. [Use cases](docs/product/use-cases.md)
4. [Product model](docs/product/product-model.md)
5. [Limitations](docs/product/limitations.md)

### Getting started

1. [Installation](docs/getting-started/installation.md)
2. [Quick start](docs/getting-started/quick-start.md)
3. [First dataset](docs/getting-started/first-dataset.md)
4. [First ingestion](docs/getting-started/first-ingestion.md)
5. [First search](docs/getting-started/first-search.md)

### Concepts

1. [Datasets](docs/concepts/datasets.md)
2. [Providers](docs/concepts/providers.md)
3. [Ingestion pipelines](docs/concepts/ingestion-pipelines.md)
4. [Search](docs/concepts/search.md)
5. [Search Lab](docs/concepts/search-lab.md)
6. [Plugins](docs/concepts/plugins.md)

### Guides

#### Retrieval

1. [Run vector search](docs/guides/retrieval/run-vector-search.md)
2. [Run BM25 search](docs/guides/retrieval/run-bm25-search.md)
3. [Configure hybrid search](docs/guides/retrieval/configure-hybrid-search.md)
4. [Configure reranking](docs/guides/retrieval/configure-reranking.md)
5. [Compare searches](docs/guides/retrieval/compare-searches.md)

#### Plugins

1. [Add custom actor configuration](docs/guides/plugins/how-to-add-custom-actor-configuration.md)
2. [Add custom provider configuration](docs/guides/plugins/how-to-add-custom-provider-configuration.md)

### Architecture

1. [Overview](docs/architecture/overview.md)
2. [System context](docs/architecture/system-context.md)
3. [Runtime topology](docs/architecture/runtime-topology.md)
4. [Domain model](docs/architecture/domain-model.md)
5. [Data lifecycle](docs/architecture/data-lifecycle.md)
6. [Ingestion flow](docs/architecture/ingestion-flow.md)
7. [Retrieval flow](docs/architecture/retrieval-flow.md)
8. [Evaluation flow](docs/architecture/evaluation-flow.md)
9. [Persistence](docs/architecture/persistence.md)
10. [Plugin system](docs/architecture/plugin-system.md)
11. [Frontend](docs/architecture/frontend.md)
12. [Error handling](docs/architecture/error-handling.md)
13. [Security](docs/architecture/security.md)

### Development

1. [Setup](docs/development/setup.md)
2. [Repository structure](docs/development/repository-structure.md)
3. [Coding conventions](docs/development/coding-conventions.md)
4. [Testing](docs/development/testing.md)
5. [Release process](docs/development/release-process.md)

## License

Apache License 2.0. See [LICENSE.md](LICENSE.md).
