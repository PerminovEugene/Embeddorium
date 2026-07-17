<div align="center">

<img src="docs/assets/embeddorium-logo.png" alt="Embeddorium" width="170">

# Embeddorium

Embeddorium is a local-first platform for turning your data into searchable RAG infrastructure.

<p>
  <img src="https://img.shields.io/badge/RAG-platform-6F42C1" alt="RAG Platform">
  <img src="https://img.shields.io/badge/Version-1.0.0-2EA44F" alt="Version 1.0.0">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Docker%20Compose-supported-2496ED?logo=docker&logoColor=white" alt="Docker Compose">
  <img src="https://img.shields.io/badge/License-Apache%202.0-blue" alt="Apache 2.0 License">
</p>

</div>

* **Declarative:** Define how your data should be ingested, processed, indexed, and searched. Embeddorium executes the pipeline, preserves every intermediate artifact, and makes each processing step available for inspection. Explicit configurations make retrieval workflows easier to reproduce, understand, compare, and debug.

* **Configuration-First:** Datasets, providers, ingestion pipelines, chunking strategies, embedding models, search methods, fusion, and reranking are all configured independently. Run the same data through different configurations without rewriting application code or rebuilding the entire retrieval stack.

* **Plugin-Based:** Extend Embeddorium with custom parsers, filters, chunkers, embedding providers, rerankers, and other pipeline components. When a data format, model provider, or processing strategy is not supported, add a plugin, refresh the UI, and use it as part of the same pipeline. Spend less time on integration boilerplate and more time improving retrieval.

* **Learn Once, RAG Anything:** Turn websites, local files, and structured documents into searchable datasets for applications and AI agents. Use the built-in UI to configure pipelines and inspect retrieval behavior, then expose indexed knowledge through the HTTP API and MCP server.

## High-level component overview

<img src="docs/assets/Architecture_high_level.png" alt="High-level Embeddorium architecture">

## Setup

1. Install Docker Compose v2.

2. Prepare the environment:

```sh
cp .env.example .env
```

3. Start the containers:

```sh
docker compose up -d
```

4. Open the UI at `http://localhost:5173/`.


## Documentation

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

### Root

2. [Glossary](docs/glossary.md)
3. [FAQ](docs/faq.md)
4. [Changelog](docs/changelog.md)
5. [Contributing](docs/contributing.md)

## License

Apache License 2.0. See [LICENSE.md](LICENSE.md).
