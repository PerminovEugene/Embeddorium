# Search Lab

Search Lab compares searches that were already executed and persisted by
`POST /search`. It does not run retrieval itself.

## Comparison rules

- Selected searches must report the same dataset name.
- By default they must also use the same query text.
- **Allow different inputs** relaxes the query-text rule while retaining the
  dataset-name rule.

## Views

- **By chunk** merges identical `chunkId` values and shows where each selected
  search ranked that chunk.
- **By document** groups the combined chunk rows by source URL or document ID.
- **By rank** places the result at each zero-based stored result position from
  every selected search together.

Search results are persisted in their returned order, so the array index is the
rank used by the UI. Scores are displayed but are not normalized across search
methods; a BM25 raw score, Qdrant similarity score, RRF score, and reranker
score do not share one scale.

Search Lab currently has no judgments, golden query sets, or retrieval metrics.
See [Evaluation flow](../architecture/evaluation-flow.md).
