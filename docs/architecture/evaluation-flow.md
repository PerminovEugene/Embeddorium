# Evaluation flow

Embeddorium currently provides result inspection and comparison, not a full
retrieval evaluation system.

## Implemented flow

1. `POST /search` executes one strategy for each query input.
2. The server best-effort persists the query, strategy settings, and ordered
   results.
3. Search Lab loads saved searches through `GET /searches` and
   `GET /searches/{id}`.
4. The UI aligns results by chunk, document, or rank for visual comparison.

This supports qualitative checks such as whether semantic and BM25 find the
same chunk and how reranking changes order.

## Not implemented

- Ground-truth/golden query sets
- Relevant/irrelevant judgments
- Recall@k, Precision@k, MRR, nDCG, or hit-rate calculation
- Latency or cost capture per retrieval stage
- Versioned evaluation runs and regression gates
- Answer generation and groundedness evaluation in the supported UI/API flow

The schema, ownership, and acceptance criteria for those features are not
defined by the current implementation: {MISSED_INFO}
