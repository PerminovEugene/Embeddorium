# Architecture

Embeddorium ingests a source once through a chain of small, single-purpose
[Dramatiq](https://dramatiq.io/) actors. Each actor does one thing, records its
result in Postgres, and hands off to the next stage through a transactional
outbox. No actor talks to RabbitMQ directly, which is what keeps the whole thing
restartable and idempotent.

There are two ways in — crawling web pages, or reading a folder of local XML
files. Both run through the _same_ chain of actors: the first two stages
(`validate_source`, `fetch_source`) select a per-source-type strategy plugin
(web vs local file) and the rest is fully shared.

> For the implementation-level reference — each actor's message payload, queue
> name, status transitions and failure modes, plus the broker/retry setup — see
> [pipeline/](pipeline/README.md).

## The crawl chain (web)

<img src="docs/assets/Architecture.png" alt="Embeddorium architecture" >

1. **validate_source** — the validation/dedup gate (strategy plugins live in
   `backend/plugins/validate_source`). The web strategy normalizes the URL and
   enforces same-origin policy for discovered links (seeds are exempt); the
   actor then skips the source if an active `crawl_target` already exists,
   otherwise creates one (`queued`) and enqueues the fetch. Discovered links
   loop back here carrying the same `pipeline_id`.
2. **fetch_source** — the merged fetch stage (strategy plugins live in
   `backend/plugins/fetch_source`). The web strategy fetches over TLS
   (insecure only for allowlisted domains), sorts failures into transient
   (retry) vs permanent (give up), rejects unsupported content types, and
   writes the raw body to disk plus a `source_fetches` provenance row.
3. **parse_source** — picks a parser by content type, extracts normalized text,
   and saves a `Document` with its hashes and provenance.
4. **chunk_document** — splits the text into chunks and records any links it
   finds along the way.
5. **schedule_embeddings** — emits one embed job per batch of chunks, then hands
   off to link scheduling.
6. **schedule_discovered_links** — schedules the persisted links back to the
   frontier, then marks the target `processed`. This is deliberately last, so
   downstream work is durable before a target is considered done.
7. **embed_chunks** — embeds each chunk with the run's configured provider and
   upserts the vectors into Qdrant, using the chunk id as the point id (so
   re-embedding overwrites instead of duplicating).
8. **track_pipeline_status** — not a numbered stage of its own, but a listener
   triggered from the tail of the chain: `embed_chunks` pokes it after every
   finished batch, and `schedule_discovered_links` pokes it after every target
   reaches `processed`. Both are needed because the last embed can finish
   either before or after its target reaches `processed`; relying on only one
   trigger leaves a race where the run never gets marked complete. It flips
   the run to `completed` (and stamps `finished_at`) once `crawl_targets` has
   no more active targets for the run _and_ every scheduled embed batch has
   finished — see "Runs are self-contained" below for the counters that back
   this check.

## The file chain (local XML)

Instead of crawling links, this chain reads a local dump of `*.xml` files and
optionally filters them by keyword. It runs through the same `validate_source`
and `fetch_source` actors as the web chain — only the strategy plugins differ —
and rejoins the shared chain at `parse_source`.

- **validate_source (local strategy)** normalizes the path to its absolute form
  (`file://<abs_path>` for dedup), validates that the file exists and is
  readable, dedups against an already-queued target, and creates the
  `crawl_target`.
- **fetch_source (local strategy)** reads the file from disk and stores it as a
  `SourceFetch` (`http_status=0`, `content_type=application/xml`), then routes
  to `filter_documents` instead of `parse_source`.
- **filter_documents** pulls the document title out of the XML and checks it
  against a configurable keyword list. With no keywords configured, everything
  passes. Non-matches are marked `skipped` (`skip_reason="not_relevant"`) and
  the chain stops; matches advance to `filtered` and rejoin at `parse_source`.

`schedule_discovered_links` naturally finds zero links in an XML document, which
is expected.

## Why the outbox

Every stage writes its domain rows **and** the next stage's message into an
`outbox_events` row inside a single database transaction. A standalone
dispatcher (`python -m backend.outbox.dispatcher`) polls those rows and publishes
them to RabbitMQ, marking each `sent`.

That removes the classic dual-write problem: a message exists if and only if the
data it depends on was committed. Delivery is at-least-once, and every consumer
is idempotent — stages acquire work with a compare-and-set status lock (e.g.
`FETCHED → PARSING`), outbox rows carry a `dedup_key`, and upserts use natural
keys. Re-delivery never duplicates work.

## The status machine

`crawl_targets` is both the crawl frontier and the orchestration backbone. Every
URL (or file) the system has seen gets a row whose status walks the pipeline:

```
queued → fetching → fetched → parsing → parsed → chunking → chunked → scheduling → processed
```

plus the terminal states `skipped`, `skipped_unsupported`, `failed_transient`,
and `failed_permanent`. Because each stage claims its target with a
compare-and-set, a stage runs at most once and concurrent or retried deliveries
are no-ops.

## Where data lives

| Store          | What lives there                                                                                                                                       |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Postgres**   | `pipeline_runs`, `crawl_targets`, `source_fetches`, `documents`, `document_chunks`, `discovered_links`, `outbox_events` — plus datasets and providers. |
| **Qdrant**     | Chunk vectors, keyed by chunk id, with `document_id` / `group` payload.                                                                                |
| **Filesystem** | Raw fetched bytes and parsed text, under `tmp/pipeline_run/<pipeline_id>/sources/<source_id>/{raw,parsed}/`. The DB stores the paths, not the blobs.   |

Keeping the large text on disk keeps Postgres lean and gives you real files to
open when you want to see exactly what a stage produced. Everything for a run —
logs and source artifacts — lives under `tmp/pipeline_run/<pipeline_id>/` and is
deleted when the run is deleted.

## Runs are self-contained

The `pipeline_runs` row is created before any message is published, and it holds
full snapshots of the dataset and the embedding provider. Every actor receives
`pipeline_id` in its payload and reads its configuration — chunk size and
overlap, embedding provider and model, the Qdrant collection — from that row,
never from global env config. That means two runs with different settings can
coexist, and the UI can point a search at exactly the collection and model a
given run produced.

Completion is also tracked on the row itself: `embeddings_scheduled` and
`embeddings_completed` count embed batches emitted / finished, each
incremented exactly once per batch via the outbox's dedup-on-insert (see
`UnitOfWork.add_outbox`), so redelivered messages never double-count. Once
`schedule_discovered_links` or `embed_chunks` pokes `track_pipeline_status`
and it finds no active crawl targets left for the run and
`embeddings_completed >= embeddings_scheduled`, it sets `status="completed"`
and `finished_at` — no external poller needed.

## Services

Everything runs in Docker Compose. Workers are built from `Dockerfile.dev`, mount
the source tree, and run under `dramatiq --watch`, so they reload on any change.

| Service                        | Role                                                  |
| ------------------------------ | ----------------------------------------------------- |
| `postgres`                     | Relational store                                      |
| `qdrant`                       | Vector store (dashboard at `/dashboard`)              |
| `rabbitmq`                     | Message broker (+ management UI)                      |
| `migrate`                      | One-shot: applies SQL migrations before workers start |
| `worker-validate-source`       | Validation/dedup gate (web + local strategies)        |
| `worker-fetch-source`          | Fetch web sources / read local files                  |
| `worker-parse-source`          | Parse into normalized text                            |
| `worker-chunk-document`        | Chunk + link extraction                               |
| `worker-schedule-embeddings`   | Fan out embed jobs                                    |
| `worker-schedule-links`        | Schedule discovered links                             |
| `worker-filter-documents`      | Keyword relevance gate                                |
| `worker-embed-chunks`          | Embed chunks → Qdrant                                 |
| `worker-track-pipeline-status` | Flip runs to `completed` when all work is done        |
| `worker-outbox-dispatcher`     | Publish outbox events → RabbitMQ                      |
| `server`                       | FastAPI API + embeddings tester backend               |
| `ui`                           | React/Vite front end                                  |
