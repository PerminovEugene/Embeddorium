# Project Architecture

A distributed crawler and indexer for web and file sources of any domain. Pipeline runs are created via the API; the system crawls the dataset URLs, chunks the text, generates vector embeddings, and stores everything for later retrieval.

---

## Entry point

`POST /pipeline-runs` on the FastAPI server (`backend/server/pipeline_routes.py`)

Receives a `datasetId` and `providerId` (both pre-created via `/datasets` and `/providers`), creates the `pipeline_runs` row with full dataset/provider snapshots, and publishes seed message(s) to RabbitMQ carrying `pipeline_id`. No separate config file or seed script is needed.

---

## Pipeline (stage-per-actor, outbox-backed)

The ingestion of one source is split into five single-responsibility stages,
each its own actor / queue / worker. The `crawl_targets` status machine is the
orchestration backbone: every stage acquires its work with a **compare-and-set
status lock** (e.g. `FETCHED → PARSING`), so a stage runs at most once and
concurrent/retried deliveries are no-ops.

```
POST /pipeline-runs (server)
       │  creates pipeline_run row, publishes seed with pipeline_id
       ▼
ingest.crawl.frontier.manage.v1
       │
       ▼
crawl_frontier_manager_actor          ← dedup gate; creates crawl_target (queued)
       │ (new URLs only)
       ▼
ingest.crawl.source.fetch.v1      → fetch_source            (QUEUED→FETCHING→FETCHED)
       ▼
ingest.crawl.source.parse.v1      → parse_source            (FETCHED→PARSING→PARSED)
       ▼
ingest.crawl.document.chunk.v1    → chunk_document          (PARSED→CHUNKING→CHUNKED)
       ▼
ingest.crawl.embeddings.schedule.v1 → schedule_embeddings   (CHUNKED→SCHEDULING)
       ▼
ingest.crawl.links.schedule.v1    → schedule_discovered_links (SCHEDULING→EMBEDDING,
       │                                  │                  or straight to PROCESSED
       │                                  │                  when the document has no
       │                                  │                  chunks to embed)
       │ embed events                     └──► ingest.crawl.frontier.manage.v1
       ▼                                        (persisted discovered links, looped back)
ingest.embed.chunk.generate.v1    → embed_chunks            ← embed → save to Qdrant,
                                                              flip chunks to `embedded`,
                                                              (EMBEDDING→PROCESSED once
                                                              every chunk is embedded)
```

**No actor enqueues RabbitMQ directly.** Each stage writes its domain rows **and**
the next stage's message into an `outbox_events` row in a single DB transaction
(via `store.unit_of_work()`). The standalone **outbox dispatcher**
(`python -m backend.outbox.dispatcher`) polls pending outbox rows and
publishes them, marking each `sent`. This removes the DB-save + enqueue
dual-write: a message exists iff its data was committed. Delivery is
at-least-once and every consumer is idempotent (status locks + `dedup_key` on
outbox + natural-key upserts), so re-delivery never duplicates work.

### crawl_frontier_manager_actor
Dedup gate. Normalises the URL, skips it if an active `crawl_target` exists (transient failures stay re-queueable), else creates a `crawl_target` (status `queued`) and enqueues `fetch_source`. Enforces same-origin policy for discovered links (seeds bypass).

### fetch_source
Fetches over TLS (insecure only for allowlisted domains) via `HttpFetcher`, classifies failures as transient (retry) vs permanent (give up), rejects unsupported content types, hashes the body, and stores a `source_fetches` provenance row.

### parse_source
Selects a parser by content type (registry: html→trafilatura, plain→passthrough; PDF/DOCX is a one-line extension), produces normalized text, and saves the `Document` with provenance (final URL, status, content/text hashes, parser/chunker versions, `retrieved_at`, real `language` default `unknown`).

### chunk_document
Splits the document text into ~1200-token chunks (`langchain MarkdownTextSplitter`), upserts `document_chunks` (unique on `document_id + chunk_index`) and persists `discovered_links` (unique on `source_chunk_id + normalized_url`).

### schedule_embeddings
Writes one embed outbox event per batch of chunks (deduped per batch), then triggers link scheduling.

### schedule_discovered_links (terminal-for-links)
Writes one frontier outbox event per pending discovered link and marks them scheduled. Sets the target to `EMBEDDING` (waiting on its chunks to be embedded), or straight to `PROCESSED` when its document has zero chunks (or every chunk is already embedded) — no embed batch will ever run for it.

### embed_chunks (terminal)
Loads chunks, runs `Qwen/Qwen3-Embedding-8B` via `sentence-transformers`, upserts vectors into `BASE_{dataset_name}_qwen_embed_8b` using the **chunk id as the point id** (re-embedding overwrites instead of duplicating), flips those chunks' status to `embedded`, and — only once every chunk of the document is embedded — finalizes the target to `PROCESSED`. This is the only place a target with chunks reaches `PROCESSED`, so the status now means the target's chunks are actually embedded, not merely that embed batches were scheduled.

---

## Storage

| Store    | What lives there                                      |
|----------|-------------------------------------------------------|
| Postgres | `documents`, `document_chunks`, `crawl_targets`, `source_fetches`, `discovered_links`, `outbox_events` |
| Qdrant   | Vector embeddings with `chunk_id` / `document_id` / `pipeline_run_id` payload (point id = chunk id) |

`crawl_targets` is the crawl frontier: every URL the system has seen gets a row with a status that walks the pipeline (`queued → fetching → fetched → parsing → parsed → chunking → chunked → scheduling → embedding → processed`, with zero-chunk documents skipping straight from `scheduling` to `processed`), plus terminal `skipped_unsupported` / `failed_transient` / `failed_permanent`. This both prevents re-crawling and drives stage orchestration. Each `document_chunks` row also carries its own `pending → embedded` status, and `processed_at` on `crawl_targets` records when a target reached `processed` (so `processed_at - created_at` gives that target's processing time).

---

## Infrastructure (docker-compose)

| Service                    | Role                              |
|----------------------------|-----------------------------------|
| `postgres`                 | Relational store                  |
| `qdrant`                   | Vector store                      |
| `rabbitmq`                 | Message broker (+ management UI)  |
| `worker-crawl-frontier-manager` | Runs crawl_frontier_manager_actor      |
| `worker-fetch-source`      | Runs fetch_source (stage 1)       |
| `worker-parse-source`      | Runs parse_source (stage 2)       |
| `worker-chunk-document`    | Runs chunk_document (stage 3)     |
| `worker-schedule-embeddings` | Runs schedule_embeddings (stage 4) |
| `worker-schedule-links`    | Runs schedule_discovered_links (stage 5) |
| `worker-embed-chunks`      | Runs embed_chunks (stage 7) — embeds chunks, upserts to Qdrant |
| `worker-outbox-dispatcher` | Publishes outbox_events to RabbitMQ |

Workers are built from `Dockerfile.dev`, mount the source tree as a volume, and use `dramatiq --watch backend` so they reload on any code change.
