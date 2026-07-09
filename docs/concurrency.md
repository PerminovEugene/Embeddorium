# Concurrency, threads & processes

This page documents how much work each pipeline stage runs in parallel today,
where those limits come from, and what actually bounds load on an embedding
backend like Ollama. It reflects the shipped `docker-compose.yml` and actor
code — no hidden rate limiter, no autoscaling.

## TL;DR

- **Every stage runs single-threaded, single-process, one container each.**
  Each worker is launched with `--processes 1 --threads 1`, and no stage has
  `replicas`/`scale` in Compose.
- So the whole pipeline processes **one message per stage at a time**, including
  embedding — **effective embedding concurrency is `X = 1`**.
- That `X = 1` for embedding is **incidental, not enforced.** There is no
  rate-limiter, semaphore, or connection cap in the code. It falls out of the
  worker knobs above. Raise `--threads`/`--processes` or add replicas and Ollama
  will receive `processes × threads × containers` concurrent calls, bounded by
  nothing in this repo.

## Per-stage settings

Each pipeline stage is its own Dramatiq worker container, each consuming a
single queue, each pinned explicitly (Dramatiq otherwise defaults threads to the
host CPU count):

| Container | Command | Processes × Threads |
| --------- | ------- | ------------------- |
| `worker-validate-source` | `dramatiq …validate_source_actor` | 1 × 1 |
| `worker-fetch-source` | `dramatiq …fetch_source_actor` | 1 × 1 |
| `worker-parse-source` | `dramatiq …parse_source_actor` | 1 × 1 |
| `worker-chunk-document` | `dramatiq …chunk_document_actor` | 1 × 1 |
| `worker-schedule-embeddings` | `dramatiq …schedule_embeddings_actor` | 1 × 1 |
| `worker-schedule-links` | `dramatiq …schedule_discovered_links_actor` | 1 × 1 |
| `worker-filter-documents` | `dramatiq …filter_documents_actor` | 1 × 1 |
| `worker-embed-chunks` | `dramatiq …embed_chunks_actor` | 1 × 1 |
| `worker-track-pipeline-status` | `dramatiq …track_pipeline_status_actor` | 1 × 1 |
| `worker-outbox-dispatcher` | `python -m backend.outbox.dispatcher` | single poll loop (not Dramatiq) |

The values live in the `command:` line of each service in `docker-compose.yml`.

### Why the embed stage is pinned to 1×1

`worker-embed-chunks` keeps a comment explaining its `--threads 1`
(`docker-compose.yml`):

> the embedding model is a lazily-initialized module singleton; a single thread
> avoids racing on first init and concurrent `model.encode`.

So the pin is deliberate for the in-process (`huggingface`) provider. The same
constraint is repeated for the bare-metal path in
[docs/embeddings.md](embeddings.md): `dramatiq …embed_chunks_actor --processes 1
--threads 1`.

### Dramatiq prefetch

Dramatiq derives its RabbitMQ prefetch from thread count:
`queue_prefetch = min(threads * 2, 65535)`. With `--threads 1` that is **2** —
RabbitMQ hands each consumer at most 2 unacked messages, and the single worker
thread still runs them strictly one at a time.

## The outbox dispatcher fans out immediately

Concurrency at the *worker* is bounded; concurrency at the *queue* is not.

`schedule_embeddings_actor` splits every chunk of a document into batches
(`batch_size`, default `32` in the model, `64` from the UI) and writes **one
outbox row per batch in a single DB transaction** — all at once, no throttling.

`backend/outbox/dispatcher.py` then turns those rows into RabbitMQ messages with
a single-threaded poll loop that fetches up to `DEFAULT_BATCH_LIMIT = 100`
pending rows per iteration and **drains fast — it only sleeps when there is
nothing to publish** (`run_forever`).

So for a document producing `ceil(N / batch_size)` batches (the "1000 batches of
64" case), all of those messages land in the `ingest.embed.chunk.generate.v1`
queue within seconds. **This is harmless on its own** — RabbitMQ just queues
them, and the 1×1 embed worker drains them one at a time. But it means the
*entire backlog is instantly available* to any consumer concurrency you add.

## What bounds Ollama load

Nothing in the code, beyond the worker pin. The Ollama client
(`backend/shared/clients/ollama_embed_client.py`) is fully sequential:

- `encode()` loops over sub-batches synchronously — no threads, no async, no
  `Semaphore`.
- Retries are synchronous (`_EMBED_RETRIES = 2`, `_RETRY_BACKOFF = 1.0s`).
- **No HTTP timeout** is set — the underlying `ollama` client defaults to
  `timeout=None`, so a hung call blocks the single worker thread indefinitely.

There is **no** `dramatiq.rate_limits` / `ConcurrentRateLimiter` middleware, **no**
application-level semaphore, and **no** connection-pool cap anywhere in the repo
(`backend/shared/clients/queue/queue_client.py` adds only logging middleware).

**Effective bound: `X = processes × threads × replicas` for `worker-embed-chunks`,
which ships as `1 × 1 × 1 = 1`.** The only other limiter is Ollama's own
server-side `OLLAMA_NUM_PARALLEL`, which is external to this project.

## Scaling safely

If you want to speed up embedding, do **not** naively bump `--threads` on
`worker-embed-chunks`:

- For the `huggingface` provider, extra threads race the lazily-initialized
  model singleton (see above) — keep it at `1 × 1`.
- For the `ollama` provider, each added thread / process / replica is a new
  concurrent HTTP caller with no code-side ceiling and no request timeout. Scale
  Ollama-facing concurrency deliberately and cap it on the Ollama side with
  `OLLAMA_NUM_PARALLEL`, or add an explicit concurrency limit in the client
  first.

Other stages (fetch, parse, chunk) are I/O-bound and can generally take more
threads without correctness issues, but that is untested territory — the shipped
config keeps everything at `1 × 1` for predictable, inspectable runs.
