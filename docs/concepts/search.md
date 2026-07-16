# Search

`POST /search` accepts one or more query texts and one retrieval strategy. Every
strategy is scoped to a pipeline run.

## Semantic

The server builds an embedding client from the run's provider snapshot, embeds
the query with L2 normalization, and asks the run's Qdrant collection for the
nearest points filtered by `pipeline_run_id`. Qdrant's collection distance
controls ranking.

## Keyword

PostgreSQL ranks `document_chunks.text` with the `pg_textsearch` `<@>` operator.
The query joins chunks to crawl targets for the selected pipeline. The raw
operator score is negated: lower/more negative is a better match. The API
returns that raw score.

Keyword search does not call the embedding provider or Qdrant.

## Hybrid

Hybrid requests `topK` dense results and `topK` BM25 results, converts each
result set to a best-first chunk-ID list, and applies RRF:

```text
score(chunk) = sum(1 / (60 + one_based_rank))
```

The fused list is sorted by descending RRF score, with chunk ID as a
deterministic tie-break, and cut to `topK`.

## Reranking

Reranking is available only for hybrid search. A saved `cross-encoder` provider
scores each `(query, chunk text)` pair from the fused pool, overwrites the score,
sorts descending, and keeps `rerankerTopK`. Invalid provider configuration is a
request error. A runtime endpoint failure is logged and degrades to the original
hybrid order, capped to `rerankerTopK`.

## History

One `search_inputs` and one `searches` row are written per query input. Saving
history is best-effort and does not fail an otherwise successful search.
