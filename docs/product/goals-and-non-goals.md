# Goals and non-goals

## Goals demonstrated by the code

- Make ingestion stages independently inspectable and testable.
- Save enough run configuration to reproduce which dataset, chunker, provider,
  collection, and similarity metric were used.
- Keep embedding providers replaceable through discovered adapters.
- Make semantic, lexical, and hybrid retrieval comparable on the same data.
- Tolerate at-least-once message delivery through status claims, outbox dedup
  keys, natural-key upserts, and stable Qdrant point IDs.
- Keep model execution outside the backend containers, except for the trivial
  in-process mock provider.

## Current non-goals and deferred work

- Hosted multi-user operation or public internet exposure.
- An authenticated API or role/permission model.
- A general-purpose file ingestion system; local ingestion is XML-only today.
- Elasticsearch/OpenSearch; lexical retrieval uses PostgreSQL BM25.
- In-process Torch, ONNX, or sentence-transformer model serving.
- Automated retrieval evaluation metrics, relevance labels, or answer-quality
  judging.
- A complete chatbot product. The MCP/agent path is present but incomplete.

These are descriptions of the current repository, not commitments about future
versions.
