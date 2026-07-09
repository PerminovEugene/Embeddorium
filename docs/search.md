# Searching the knowledge base

Once a pipeline run has completed, you can query the vectors it produced —
from the UI or over the API. Search is **run-scoped**: you pick a pipeline
run, not a raw collection, and the run's saved snapshot supplies both the
Qdrant collection and the embedding model. That guarantees your query is
embedded with the same model (and dimensions) the collection was indexed
with — there is no way to mismatch them.

## From the UI

Open the home page (http://localhost:5173) and switch the source mode to
**Select pipeline results**:

1. Pick a **completed pipeline run** — this fixes the collection and the
   embedding model.
2. If the run used the Ollama provider, set the **Ollama port** so the server
   can embed your query (the same networking rules as ingestion apply — see
   [embeddings.md](embeddings.md)).
3. Enter one or more **query texts** and submit.

Each query returns the top 10 nearest chunks with their similarity score,
chunk text, and source URL — so you can judge retrieval quality directly
against what the pipeline actually stored.

The other mode, **Manual input**, is the [embeddings tester](usage.md#embeddings-tester):
it compares your own texts against each other instead of querying a collection.

## Over the API

```sh
curl -s -X POST http://localhost:8000/search \
  -H 'Content-Type: application/json' \
  -d '{
    "configuration": {"runId": "<pipeline-run-uuid>", "ollamaPort": 11434},
    "source": {"inputs": [{"id": "q1", "text": "What is the VAT rate?"}]}
  }'
```

- `configuration.runId` — the pipeline run to search. Collection, provider,
  and model are read from the run's snapshot.
- `configuration.ollamaPort` — where to reach Ollama for embedding the query
  (only needed for Ollama-backed runs; mock runs need nothing).
- `source.inputs` — one or more queries; each gets its own result set.

Every hit carries `score`, `chunkId`, `documentId`, `chunkText`, and
`sourceUrl`, joined back from Postgres.

## How a query is answered

1. The server loads the run and reads the collection name and the embedding
   provider snapshot from its saved `actor_configs`.
2. The query text is embedded with that provider/model.
3. Qdrant returns the nearest vectors, filtered by the run's `pipeline_id` —
   a collection can hold vectors from several runs, and the filter keeps
   results scoped to the one you selected.
4. Hit payloads carry chunk and document ids, which are joined back to
   Postgres for the chunk text and source metadata.

Searches are also persisted (query text, configuration, and results) so past
queries can be inspected later.

## Mock runs return random results

The `mock` provider produces random vectors, so searching a mock run returns
arbitrary chunks. That is expected — use it to verify the flow. For meaningful
results, ingest with a real provider
([Ollama tutorial](tutorials/ollama_embeddings.md)).

## BM25 (lexical) search

The Postgres image ships the `pg_textsearch` extension with a BM25 index on
chunk text (`ChunkRepository.search_bm25`), the lexical building block for
hybrid dense + BM25 retrieval. It is not yet exposed through the search API —
see the [roadmap](roadmap.md) and
[infra/postgres/README.md](../infra/postgres/README.md) for how the index is
wired.
