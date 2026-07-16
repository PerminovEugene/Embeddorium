# Pipeline actors

Ingestion in Embeddorium is a chain of small, single-purpose
[Dramatiq](https://dramatiq.io/) actors. Each actor is one stage: it claims a
unit of work, does exactly one thing, records the result in Postgres, and hands
off to the next stage. No actor talks to RabbitMQ directly — every handoff is
written to a transactional outbox and published by a standalone dispatcher,
which is what keeps the pipeline restartable and idempotent.

This folder is the **implementation reference** for those actors. For the
higher-level narrative (why the outbox, where data lives, the status machine)
read [../architecture.md](../architecture.md) first; for how much runs in
parallel read [../concurrency.md](../concurrency.md). The pages here go one level
deeper: exact queue names, message payloads, per-actor status transitions, and
the operational details that back them.

| Page | What it covers |
| ---- | -------------- |
| [actors.md](actors.md) | Every actor: responsibility, consumed/emitted payloads, status transitions, failure modes |
| [queues.md](queues.md) | RabbitMQ broker, Dramatiq wiring, queue names, retries, prefetch, how workers are launched |
| [operations.md](operations.md) | The outbox, `pipeline_runs` state machine, idempotency, error handling, backpressure, observability |

## The two chains

There are two ways in — crawling web pages, or reading a folder of local XML
files. Both run through the **same** actors; only the first two stages
(`validate_source`, `fetch_source`) select a per-source-type strategy plugin
(web vs local file), and the local chain inserts one extra `filter_documents`
gate before rejoining the shared tail.

```
                POST /pipeline-runs/{id}/launch → seed_pipeline (direct enqueue)
                                    │
                                    ▼
                            validate_source
                                    │  (direct enqueue)
                                    ▼
                             fetch_source
                          web │            │ local
                              ▼            ▼
                        parse_source   filter_documents
                              ▲            │
                              └────────────┘  (relevant → parse_source)
                                    │
                                    ▼
                            chunk_document
                                    │
                                    ▼
                          schedule_embeddings
                          │                  │
                          ▼                  ▼
                   embed_chunks       schedule_discovered_links
                          │            │              │
                          │            │              ▼
                          │            │        validate_source
                          │            │        (discovered links,
                          │            │         loops back to top)
                          ▼            ▼
                        track_pipeline_status
                     (completes the run when
                      no work remains)
```

Every stage after `fetch_source` hands off through the **outbox**. The two
exceptions are the pipeline entry points, which enqueue directly on the broker:

- `seed_pipeline` → `validate_source` (see `backend/server/pipeline/launch.py`).
- `validate_source` → `fetch_source` (see
  `backend/actors/validate_source_actor/handler.py:167`).

Everything downstream is written to `outbox_events` inside the same transaction
as the stage's domain rows, and `backend/outbox/dispatcher.py` turns those rows
into RabbitMQ messages. See [operations.md](operations.md#the-outbox) for why.

## The stage order

| # | Actor | Queue | Reads | Emits |
| - | ----- | ----- | ----- | ----- |
| 0 | `validate_source` | `ingest.crawl.source.validate.v1` | seed / discovered link | `fetch_source` (direct) |
| 1 | `fetch_source` | `ingest.crawl.source.fetch.v1` | crawl target | `parse_source` (web) or `filter_documents` (local) |
| — | `filter_documents` | `ingest.crawl.file.filter.v1` | fetched local file | `parse_source` (if relevant) |
| 2 | `parse_source` | `ingest.crawl.source.parse.v1` | source fetch | `chunk_document` |
| 3 | `chunk_document` | `ingest.crawl.document.chunk.v1` | document | `schedule_embeddings` |
| 4 | `schedule_embeddings` | `ingest.crawl.embeddings.schedule.v1` | chunks | `embed_chunks` (per batch), `schedule_discovered_links` |
| 5 | `schedule_discovered_links` | `ingest.crawl.links.schedule.v1` | discovered links | `validate_source` (frontier), `track_pipeline_status` |
| 7 | `embed_chunks` | `ingest.embed.chunk.generate.v1` | chunk batch | `track_pipeline_status` |
| — | `track_pipeline_status` | `ingest.pipeline.status.track.v1` | run counters + crawl targets | — (completes the run) |

The stage numbers mirror the docstrings in each `handler.py`. `filter_documents`
and `track_pipeline_status` are cross-cutting rather than numbered stages of
their own — the first is a local-chain-only gate, the second a listener poked
from the tail of the chain. See [actors.md](actors.md) for each one in detail.
</content>
</invoke>
