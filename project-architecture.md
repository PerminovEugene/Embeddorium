# Project Architecture

A distributed crawler and indexer for legal web sources. Seed URLs come from a config file; the system crawls them, chunks the text, generates vector embeddings, and stores everything for later retrieval.

---

## Entry point

`laws_agent/runners/add_web_source_job.py <config.json>`

Reads the config, iterates over groups (e.g. "Estonia") and their source URLs, and pushes each `(group, url)` pair into the first queue. Nothing else — it just seeds the pipeline.

**config.json shape:**
```json
{
  "groups": [
    {
      "name": "Estonia",
      "sources": [{ "link": "emta.ee", "description": "..." }]
    }
  ]
}
```

---

## Pipeline (stage-per-actor, outbox-backed)

The ingestion of one source is split into five single-responsibility stages,
each its own actor / queue / worker. The `crawl_targets` status machine is the
orchestration backbone: every stage acquires its work with a **compare-and-set
status lock** (e.g. `FETCHED → PARSING`), so a stage runs at most once and
concurrent/retried deliveries are no-ops.

```
add_web_source_job
       │
       ▼
laws.crawl.frontier.manage.v1
       │
       ▼
crawl_frontier_manager_actor          ← dedup gate; creates crawl_target (queued)
       │ (new URLs only)
       ▼
laws.crawl.source.fetch.v1      → fetch_source            (QUEUED→FETCHING→FETCHED)
       ▼
laws.crawl.source.parse.v1      → parse_source            (FETCHED→PARSING→PARSED)
       ▼
laws.crawl.document.chunk.v1    → chunk_document          (PARSED→CHUNKING→CHUNKED)
       ▼
laws.crawl.embeddings.schedule.v1 → schedule_embeddings   (CHUNKED→SCHEDULING)
       ▼
laws.crawl.links.schedule.v1    → schedule_discovered_links (SCHEDULING→PROCESSED)
       │                                  │
       │ embed events                     └──► laws.crawl.frontier.manage.v1
       ▼                                        (persisted discovered links, looped back)
laws.embed.chunk.generate.v1    → embed_chunks            ← embed → save to Qdrant
```

**No actor enqueues RabbitMQ directly.** Each stage writes its domain rows **and**
the next stage's message into an `outbox_events` row in a single DB transaction
(via `store.unit_of_work()`). The standalone **outbox dispatcher**
(`python -m laws_agent.outbox.dispatcher`) polls pending outbox rows and
publishes them, marking each `sent`. This removes the DB-save + enqueue
dual-write: a message exists iff its data was committed. Delivery is
at-least-once and every consumer is idempotent (status locks + `dedup_key` on
outbox + natural-key upserts), so re-delivery never duplicates work.

### crawl_frontier_manager_actor
Dedup gate. Normalises the URL, skips it if an active `crawl_target` exists (transient failures stay re-queueable), else creates a `crawl_target` (status `queued`) and enqueues `fetch_source`. Enforces same-origin policy for discovered links (seeds bypass).

### fetch_source
Fetches over TLS (insecure only for allowlisted domains) via `HttpFetcher`, classifies failures as transient (retry) vs permanent (give up), rejects unsupported content types, hashes the body, and stores a `source_fetches` provenance row.

### parse_source
Selects a parser by content type (registry: html→trafilatura, plain→passthrough; PDF/DOCX is a one-line extension), produces normalized text, and saves the `Document` with provenance (final URL, status, content/text hashes, parser/chunker versions, `retrieved_at`, real `language` default `unknown`, crawl `group`).

### chunk_document
Splits the document text into ~1200-token chunks (`langchain MarkdownTextSplitter`), upserts `document_chunks` (unique on `document_id + chunk_index`) and persists `discovered_links` (unique on `source_chunk_id + normalized_url`).

### schedule_embeddings
Writes one embed outbox event per batch of chunks (deduped per batch), then triggers link scheduling.

### schedule_discovered_links (terminal)
Writes one frontier outbox event per pending discovered link, marks them scheduled, and only then sets the target `PROCESSED` — so downstream work is durable before completion.

### embed_chunks
Loads chunks, runs `Qwen/Qwen3-Embedding-8B` via `sentence-transformers`, upserts vectors into `LAWS_{group}_qwen_embed_8b` using the **chunk id as the point id** (re-embedding overwrites instead of duplicating).

---

## Storage

| Store    | What lives there                                      |
|----------|-------------------------------------------------------|
| Postgres | `documents`, `document_chunks`, `crawl_targets`, `source_fetches`, `discovered_links`, `outbox_events` |
| Qdrant   | Vector embeddings with `chunk_id` / `document_id` / `group` payload (point id = chunk id) |

`crawl_targets` is the crawl frontier: every URL the system has seen gets a row with a status that walks the pipeline (`queued → fetching → fetched → parsing → parsed → chunking → chunked → scheduling → processed`), plus terminal `skipped_unsupported` / `failed_transient` / `failed_permanent`. This both prevents re-crawling and drives stage orchestration.

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
| `worker-outbox-dispatcher` | Publishes outbox_events to RabbitMQ |
| `worker-embed-chunks`      | Runs embed_chunks_actor (local)   |

Workers are built from `Dockerfile.dev`, mount the source tree as a volume, and use `dramatiq --watch laws_agent` so they reload on any code change.
