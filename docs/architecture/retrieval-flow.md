# Retrieval flow

The search API orchestrates retrieval synchronously for each query in the
request.

```mermaid
flowchart LR
    Q["Query + run ID"] --> Load["Load run snapshot"]
    Load --> Method{"Search method"}
    Method -->|semantic| Embed["Embed query"] --> Dense["Qdrant + run filter"]
    Method -->|keyword| BM25["Postgres BM25 + run join"]
    Method -->|hybrid| Both["Dense and BM25"] --> RRF["RRF k=60"]
    RRF --> Maybe{"Rerank?"}
    Maybe -->|yes| Rerank["HTTP cross-encoder"]
    Maybe -->|no| Results["Hydrated hits"]
    Dense --> Results
    BM25 --> Results
    Rerank --> Results
    Results --> History["Best-effort search history"]
```

## Run scoping

Dense points carry `pipeline_run_id`; Qdrant filters on it. BM25 joins
`document_chunks` to `crawl_targets` and filters `crawl_targets.pipeline_id`.
Both paths hydrate chunk text and document source URLs from PostgreSQL.

## Result shape

All methods normalize hits to the same keys: source/query identity, score,
chunk ID, document ID, chunk index/text, dataset name, source URL, and custom
metadata.

## Failure behavior

Missing/invalid run IDs, methods, Top K values, or reranker configuration are
HTTP errors. Embedding, Qdrant, and BM25 runtime failures propagate from the
request. Reranker runtime failures alone degrade to the original hybrid result
order. Search-history persistence failures are logged and swallowed.
