# Product overview

Embeddorium is a local retrieval-engineering workbench. Its primary loop is:

```text
source -> fetch -> filter -> parse -> chunk -> embed -> store -> search -> compare
```

The system exposes that loop instead of hiding it in one script. A pipeline run
saves its dataset and actor settings, Postgres records work and provenance,
raw/parsed artifacts remain inspectable on disk, and vectors are written to
Qdrant. The UI provides management pages for datasets, providers, pipelines,
and runs, plus search and saved-result comparison.

## Supported sources

- A web dataset with one seed URL. Discovered same-origin links can be followed.
- A local dataset containing files or folders under `sources/`; the current
  seeder selects XML files recursively.

## Supported retrieval

- Semantic dense-vector search in Qdrant.
- Keyword BM25 search in PostgreSQL through `pg_textsearch`.
- Hybrid search using Reciprocal Rank Fusion.
- Optional cross-encoder reranking of hybrid results through an HTTP endpoint.

Embeddorium is not a hosted service. The shipped runtime is Docker Compose and
the API has no authentication.
