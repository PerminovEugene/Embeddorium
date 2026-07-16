# Use cases

## Validate an ingestion pipeline

Use the mock provider to exercise source validation, fetching, filtering,
parsing, chunking, queue handoffs, Postgres persistence, and Qdrant upserts
without operating a model server.

## Compare chunking choices

Create separate runs over the same dataset with different discovered chunker
plugins and settings. Each run stores the selected chunker and settings in its
actor configuration snapshot.

## Compare retrieval strategies

Run semantic, keyword, and hybrid searches against a completed run. Searches
are persisted. Search Lab can place saved results side by side by chunk,
document, or rank.

## Inspect failures and provenance

Use Indexing Runs to inspect target status, errors, skip reasons, chunk counts,
and processing timestamps. Open raw and parsed artifacts under the run folder
to see what the fetch and parse stages produced.

## Ingest Estonian legal XML

The local XML path includes a Juurakt-aware parser and a `legal_xml` chunker
that emits section-oriented chunks and falls back to markdown chunking when the
input is not a recognized act.

## Test remote embedding backends

Configure Ollama or an OpenAI-compatible endpoint as a provider, then select it
for a run or for manual text-to-text embedding comparison.
