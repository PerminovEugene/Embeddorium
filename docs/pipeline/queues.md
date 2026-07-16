# Queues & workers

The pipeline runs on **RabbitMQ** as the broker and **Dramatiq** as the actor
framework. This page documents the broker wiring, the queue names, retry
behaviour, and how the worker processes are launched. For *how much* each stage
runs in parallel (threads, prefetch, fan-out, embedding load) see
[../concurrency.md](../concurrency.md) — that page is the source of truth for
concurrency and is not repeated here.

## Broker

`backend/shared/clients/queue/queue_client.py` builds a single
`dramatiq.brokers.rabbitmq.RabbitmqBroker` from `backend.shared.config`:

- Connection params (`RABBITMQ_HOST/PORT/VHOST/USER/PASSWORD`) come from env —
  `.env` for host interpolation, `.env.docker` inside containers. They must match
  the credentials in `infra/rabbitmq/definitions.json`.
- `heartbeat=600` (10 min). The negotiated heartbeat is the smaller of this and
  the server's `heartbeat` in `infra/rabbitmq/rabbitmq.conf`, which is also 600 —
  deliberately generous so brief Docker Desktop VM stalls don't trip "missed
  heartbeats" and churn every worker connection.
- One middleware is added: `MessageLoggingMiddleware` (structured
  publish/consume logging). There is **no** rate-limiter, concurrency, or
  connection-cap middleware anywhere in the repo.

Each launcher/dispatcher creates its own broker with a distinct
`connection_name` (e.g. `parse_source`, `embed_chunks`, `outbox_dispatcher`) so
connections are identifiable in the RabbitMQ management UI.

Queues, exchanges and bindings are **not** pre-declared in
`definitions.json` — Dramatiq declares each actor's queue on startup. The
definitions file only seeds the vhost, user and permissions.

## Queue names

One queue per actor, versioned with a `.v1` suffix. Defined once in
`backend/shared/clients/queue/queue_names.py` and imported everywhere (never
hard-coded), so a rename can't drift between publisher and consumer.

| Actor | Queue |
| ----- | ----- |
| `validate_source` | `ingest.crawl.source.validate.v1` |
| `fetch_source` | `ingest.crawl.source.fetch.v1` |
| `filter_documents` | `ingest.crawl.file.filter.v1` |
| `parse_source` | `ingest.crawl.source.parse.v1` |
| `chunk_document` | `ingest.crawl.document.chunk.v1` |
| `schedule_embeddings` | `ingest.crawl.embeddings.schedule.v1` |
| `schedule_discovered_links` | `ingest.crawl.links.schedule.v1` |
| `embed_chunks` | `ingest.embed.chunk.generate.v1` |
| `track_pipeline_status` | `ingest.pipeline.status.track.v1` |

## Retries

Every actor is declared with `max_retries=3` (in each
`backend/actors/<name>_actor/launcher.py`). No `min_backoff`/`max_backoff` is
set, so Dramatiq's default `Retries` middleware backoff applies (exponential
with jitter). A stage retries when its handler **raises** — which the handlers
do deliberately for transient conditions (e.g. a not-yet-visible `SourceFetch`
or `Document`, or a transient `SourceFetchError`). Conditions that should not
retry return quietly instead: permanent fetch failures set `FAILED_PERMANENT`
and return, and unprocessable-state / dedup / skip cases log a `message_skipped`
and return.

After `max_retries` is exhausted Dramatiq moves the message to its dead-letter
queue (`dramatiq`'s default DLQ). There is no custom DLQ handling in this repo;
a permanently failing target is diagnosed from its `crawl_target` status and the
worker logs.

## Prefetch

Dramatiq derives RabbitMQ prefetch from thread count
(`queue_prefetch = min(threads * 2, 65535)`). Workers ship pinned at
`--threads 1`, so each consumer holds at most **2** unacked messages. Details
and the reasoning are in [../concurrency.md](../concurrency.md#dramatiq-prefetch).

## How workers are launched

Each stage is its own container in `docker-compose.yml`, running one Dramatiq
worker bound to one queue, pinned to a single process and thread:

```
dramatiq backend.actors.<name>_actor --queues <queue> --processes 1 --threads 1
```

The `--processes`/`--threads` pins are explicit because Dramatiq otherwise
defaults to one process per CPU core × 8 threads; pinning them keeps each
worker's `SqlStore` connection pool sized against a known, bounded concurrency
(the launchers use `SqlPoolConfig(pool_size=2, max_overflow=3)`). `--watch` /
`--reload` under `Dockerfile.dev` reloads workers on source changes.

Workers `depends_on` a healthy `rabbitmq` and a successfully completed `migrate`
service, and run `restart: on-failure`, so first-boot ordering settles itself.

The **outbox dispatcher** is not a Dramatiq worker — it is a plain single-thread
poll loop (`python -m backend.outbox.dispatcher`) that publishes committed
outbox rows onto these queues. See
[operations.md](operations.md#the-outbox).

| Container | Command tail |
| --------- | ------------ |
| `worker-validate-source` | `…validate_source_actor --queues ingest.crawl.source.validate.v1` |
| `worker-fetch-source` | `…fetch_source_actor --queues ingest.crawl.source.fetch.v1` |
| `worker-parse-source` | `…parse_source_actor --queues ingest.crawl.source.parse.v1` |
| `worker-chunk-document` | `…chunk_document_actor --queues ingest.crawl.document.chunk.v1` |
| `worker-schedule-embeddings` | `…schedule_embeddings_actor --queues ingest.crawl.embeddings.schedule.v1` |
| `worker-schedule-links` | `…schedule_discovered_links_actor --queues ingest.crawl.links.schedule.v1` |
| `worker-filter-documents` | `…filter_documents_actor --queues ingest.crawl.file.filter.v1` |
| `worker-embed-chunks` | `…embed_chunks_actor --queues ingest.embed.chunk.generate.v1` |
| `worker-track-pipeline-status` | `…track_pipeline_status_actor --queues ingest.pipeline.status.track.v1` |
| `worker-outbox-dispatcher` | `python -m backend.outbox.dispatcher` |

Inspect live queues in the RabbitMQ management UI at `http://localhost:15672`,
or purge them between runs with `scripts/purge-queues.sh`.
</content>
