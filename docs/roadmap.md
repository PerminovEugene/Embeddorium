# Roadmap

Where Embeddorium is heading, in rough order. The guiding idea: don't just
run retrieval — make retrieval strategies **comparable and explainable**. Every
answer should show which chunks were selected, with what ranks and scores, and
which pipeline settings produced them.

This is a living document, not a commitment. Issues and PRs against any of it
are welcome.

## Shipped

- End-to-end ingestion pipeline: crawl / local XML → parse → chunk → embed →
  Qdrant, with reproducible per-run snapshots.
- Pluggable chunking strategies with auto-discovery
  ([plugins.md](plugins.md)).
- Dense (vector) search over a run's collection, from the UI and the API
  ([search.md](search.md)).
- Embeddings tester for manual text-vs-text similarity comparison.
- BM25 groundwork: Postgres `pg_textsearch` extension and a BM25 index over
  chunk text.
- MCP server exposing the knowledge base, plus an optional LangGraph chat
  agent.

## Next: lexical and hybrid retrieval

- **BM25-only search mode** through the search API, so dense and lexical can
  be compared on the same query.
- **Hybrid search** — dense + BM25 candidates fused with Reciprocal Rank
  Fusion (RRF), with per-hit badges showing whether a chunk came from dense,
  lexical, or both.
- **Retrieval trace** — persist per-candidate dense rank, lexical rank, and
  fused rank for every search, so results are debuggable after the fact.

## Then: better context

- **Heading-path enrichment** — prefix chunks with their document/section
  breadcrumbs before embedding.
- **Neighbor expansion** — return ±N adjacent chunks around a hit.
- **Parent-child retrieval** — search small chunks, return the parent
  section.

## Later: reranking and evaluation

- **Rerankers** — cross-encoder (local or provider API) reordering of
  candidates, plus MMR diversity and near-duplicate removal.
- **Compare UI** — one query, several retrieval strategies side by side.
- **Evaluation** — golden query sets, manual relevance labels, and metrics
  (Recall@k, MRR, nDCG) to compare configurations regressively.

## Lab (exploratory)

Multi-query retrieval, LLM chunk contextualization, summary indexes, HyDE,
SPLADE, ColBERT-style late interaction, late chunking. These wait until the
compare/eval layer exists — without it, their impact can't be measured.

## Anti-goals (for now)

- No Elasticsearch/OpenSearch before the Postgres BM25 baseline proves
  insufficient.
- No agentic RAG before simple, reproducible retrieval works end to end.
- No "quality by eyeball" — retrieval changes should be judged on visible
  chunks, ranks, and metrics.
