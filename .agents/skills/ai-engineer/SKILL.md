---
name: ai-engineer
description: Conventions for the RAG/embedding pipeline. Use when working on chunking, embedding providers, Qdrant vector storage, retrieval, or the MCP/agent layer.
---

# AI engineer

Domain: the ingest → chunk → embed → store → query loop. Providers are pluggable; keep them swappable.

- Embedding providers are interchangeable: `mock` (instant, offline), Ollama over HTTP. Never hardcode a model — read it from run config. Providers are HTTP clients (httpx/ollama); keep torch/sentence-transformers out of the container path.
- Vector dimension, distance metric, and collection name come from the embedder — never assume. Validate dim before upserting to Qdrant.
- Chunkers are plugins in `backend/plugins/chunkers/`, selectable per run. A new strategy is a new plugin (subclass `base.py`, drop the file in, registry auto-discovers), not a core edit — see `docs/concepts/plugins.md`.
- Retrieval is hybrid: dense vectors in Qdrant + BM25 in Postgres (`025_add_chunk_bm25_search.sql`). Search logic lives in `backend/server/search/`; keep both paths working when touching chunk storage.
- Each run snapshots its dataset + provider config; never resolve a provider or chunker setting at query time from mutable global state.
- Every pipeline stage leaves a durable, inspectable trace — preserve that. Don't collapse stages or drop intermediate artifacts.
- Determinism: given the same input + config, a run reproduces. No hidden global state, seed anything random.
- Prefer the `mock` provider for tests and end-to-end runs so CI needs no model server.
- MCP/agent code: expose tools with clear schemas; keep tool handlers thin over the pipeline primitives.

## Checks before done
- Ran the loop end-to-end with the `mock` embedder.
- Chunk/embed counts and dimensions logged and sane.
- No provider-specific assumption leaked into shared code.
