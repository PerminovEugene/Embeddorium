# Operational details

How the pipeline stays correct under retries, restarts and concurrency, and
where to look when a run misbehaves. This complements
[../architecture.md](../architecture.md) (the conceptual model) and
[../troubleshooting.md](../troubleshooting.md) (diagnosing a stuck stack).

## The outbox

Every stage writes its domain rows **and** the next stage's message into an
`outbox_events` row inside a single database transaction (`store.unit_of_work()`
→ `uow.add_outbox(...)`). A standalone dispatcher
(`backend/outbox/dispatcher.py`, run as `python -m backend.outbox.dispatcher`)
polls those rows, publishes each to RabbitMQ, and marks it `sent`.

This removes the dual-write problem: a message exists **iff** the data it depends
on was committed. A crash between "write data" and "publish message" is
recoverable, because the message is a committed row, not a lost network call.

The dispatcher fetches up to `DEFAULT_BATCH_LIMIT = 100` pending rows per
iteration and **drains fast — it only sleeps (`DEFAULT_POLL_INTERVAL = 1.0s`)
when there is nothing to publish**. A publish failure records an attempt and
leaves the row pending for the next pass (`dispatch_once`).

The two pipeline entry points are the only handoffs that **bypass** the outbox
and enqueue directly on the broker: `seed_pipeline → validate_source` and
`validate_source → fetch_source`. Both are safe because they precede the first
committed pipeline row and are idempotent downstream (dedup + acquire locks).

## Idempotency

Delivery is **at-least-once**, so every consumer is built to tolerate
re-delivery and produce no duplicate work. Three mechanisms combine:

- **Compare-and-set status locks** — a stage acquires its target with
  `acquire(from_statuses=[...], to_status=...)`. A message for a target already
  past that stage finds no match and no-ops. See
  [actors.md](actors.md#common-contract).
- **Outbox dedup keys** — every `add_outbox` carries a `dedup_key` (e.g.
  `chunk:<target>`, `embed:<document>:<start>`, `frontier:<link>`,
  `track:<run>:embed:<doc>:<chunk>`). A duplicate insert is dropped, so a
  redelivered stage never emits duplicate downstream messages, and the
  `embeddings_scheduled` / `embeddings_completed` counters are bumped **exactly
  once per batch** (they increment only when the outbox row is *newly* inserted).
- **Natural-key upserts** — documents, chunks, links and source fetches upsert on
  natural keys; Qdrant points use the chunk id as the point id, so re-embedding
  overwrites instead of duplicating.

## Run state machine

`pipeline_runs` (`backend/shared/models/pipeline_run.py`) tracks the run itself,
separate from per-target `crawl_targets` status:

```
pending → running → completed
                 ↘ failed
```

- **pending** — the row is created by `POST /pipeline-runs` before any message is
  published, holding immutable snapshots of the dataset and per-actor config
  (`actor_configs`, including the embedding provider). Every actor reads its
  configuration from this row by `pipeline_id`, never from global env.
- **running** — set by `POST /pipeline-runs/{id}/launch` (`launch_pipeline_run`),
  which publishes the seed messages, stamps `started_at`, and clears
  `finished_at` so a relaunch starts a clean window. Allowed from `pending`,
  `failed`, or `completed`; a second launch of a `running` run returns 409.
- **completed** — set by `track_pipeline_status` (never an external poller) once
  `count_active_for_pipeline == 0` **and** `embeddings_completed >=
  embeddings_scheduled`, stamping `finished_at`.

The two counters are the backbone of completion detection: `schedule_embeddings`
bumps `embeddings_scheduled` per newly-scheduled batch, `embed_chunks` bumps
`embeddings_completed` per finished batch, and `track_pipeline_status` compares
them. Because embedding is asynchronous relative to crawl-target status, the
tracker is poked from **both** the embed side and the link-scheduling side and
always re-derives completion from the DB rather than trusting message order —
see [actors.md](actors.md#track_pipeline_status--cross-cutting-listener).

## Error handling

- **Transient** — a raise triggers a Dramatiq retry (`max_retries=3`). Handlers
  raise deliberately for not-yet-visible commits (missing `SourceFetch` /
  `Document`, first marked `FAILED_TRANSIENT`) and transient fetch errors.
- **Permanent** — set a terminal status and **return** (no raise, no retry):
  `FAILED_PERMANENT` for permanent fetch errors, `SKIPPED_UNSUPPORTED` for
  unresolvable parsers / disallowed content types, `SKIPPED` for
  filtered-out or dedup'd targets.
- **Exhausted retries** — Dramatiq dead-letters the message; the target's
  `crawl_target` status (a `failed_*` / `skipped_*` state) is the durable record
  of what happened. A run does not auto-fail from a single dead target — it
  completes once no targets remain *active*, with failures left visible on their
  rows.

## Backpressure & fan-out

There is no application-level backpressure. `schedule_embeddings` writes all of
a document's embed-batch outbox rows in one transaction, and the dispatcher
drains them onto the `embed_chunks` queue within seconds. That is harmless —
RabbitMQ buffers them and the single-threaded embed worker drains one at a time —
but it means the *entire backlog is instantly available* to any consumer
concurrency you add. The full analysis (and the warning about naively scaling
the embed worker) is in [../concurrency.md](../concurrency.md).

## Observability

- **Logs** — every launcher wraps its handler in `log_to(target.log_dir,
  pipeline_id=...)`, so a stage's logs land in that target's per-run folder as
  well as the container log. Follow a stage with
  `docker compose logs -f worker-<stage>`.
- **Artifacts** — raw fetched bytes and parsed text live on disk under
  `tmp/pipeline_run/<pipeline_id>/sources/<source_id>/{raw,parsed}/`; the DB
  stores the paths, not the blobs. Open them to see exactly what a stage
  produced.
- **State** — inspect a run via `GET /pipeline-runs/<id>` (status, counters,
  timestamps) and the RabbitMQ management UI (`http://localhost:15672`) for
  queue depths. A run stuck in `running` almost always means the outbox
  dispatcher is down — see
  [../troubleshooting.md](../troubleshooting.md#a-run-is-stuck-in-pending-or-running).
</content>
