# The actors

Each actor lives under `backend/actors/<name>_actor/` and is split in two:

- **`handler.py`** — pure logic. Takes an injected `SqlStore` (and, where
  relevant, a vector store / fetcher / chunker), does the work, and writes any
  next-stage message to the outbox. No Dramatiq or broker imports.
- **`launcher.py`** — the thin Dramatiq binding. Declares the `@dramatiq.actor`
  (queue name, actor name, `max_retries=3`), sets up the broker and a
  right-sized `SqlStore` pool, wraps the call in `log_to(...)` so logs land in
  the target's per-run folder, then delegates to the handler.

This split is why the handlers are directly unit-testable (see
`backend/tests/actors/`) — a test calls the handler with a fake store, no broker
required.

## Common contract

Every crawl-stage message carries the **crawl target id** and the run's
**`pipeline_id`**, and nothing else (`ScheduleEmbeddingsPayload` &co. in
`backend/shared/clients/queue/pipeline_payloads.py`). The stage looks up
everything else — source fetch, document, chunks, per-actor config — from the
store by id. Keeping the wire payload minimal avoids carrying large or stale
data through RabbitMQ, and lets each actor read its configuration from the run's
immutable `actor_configs` snapshot rather than global env.

Every stage that owns a status transition claims its target with a
**compare-and-set lock** (`store.crawl_targets.acquire(from_statuses=[...],
to_status=...)`). If the target is not in an expected `from` status the acquire
returns `None`, the actor logs a `message_skipped` and returns — so a redelivered
or out-of-order message is a safe no-op. The `to_status` is included in
`from_statuses` too, so a retry of the *same* stage re-acquires cleanly.

The `crawl_targets` status walk (see
`backend/shared/models/crawl_target.py`):

```
queued → fetching → fetched → [filtering → filtered →] parsing → parsed
       → chunking → chunked → scheduling → (embedding →) processed
```

plus the terminal `skipped`, `skipped_unsupported`, `failed_transient`,
`failed_permanent`. `filtering`/`filtered` only occur on the local-file chain;
`embedding` is the intermediate "chunks scheduled, not yet all embedded" state.

---

## validate_source — stage 0

`backend/actors/validate_source_actor/handler.py`

Shared entry point of both chains, and where discovered links re-enter.

- **Consumes** `ingest.crawl.source.validate.v1` — payload `{url,
  parent_document_id?, parent_chunk_id?, pipeline_id?}`
  (`ValidateSourcePayload`).
- **Does** — picks a validation strategy by the run's dataset `source_type`
  (web: URL normalize + same-origin gate; local: path resolve + exists/readable).
  Dedups against an already-active target with the same normalized identity
  (when `validate_source.dedup` is on). On success creates a `CrawlTarget`
  (`QUEUED`) with a nested `log_dir`.
- **Emits** — a `fetch_source` message via **`broker.enqueue`** (a direct
  enqueue, not the outbox — there is no prior committed row to tie it to), at
  `handler.py:167`.
- **Skips** (no-op, logged) — when dedup finds an active target, or the strategy
  raises `SourceValidationError` (e.g. off-origin link, missing file).

## fetch_source — stage 1

`backend/actors/fetch_source_actor/handler.py`

Merged fetch stage; one strategy plugin per source type.

- **Consumes** `ingest.crawl.source.fetch.v1` — `{crawl_target_id, pipeline_id?}`
  (`FetchSourcePayload`).
- **Acquire** `QUEUED | FAILED_TRANSIENT | FETCHING → FETCHING`.
- **Does** — web targets are fetched over HTTP(S) (TLS verification, read
  timeout and content-type allowlist come from `fetch_source` config); local
  targets are read from disk. Writes the raw bytes to disk and, in one
  transaction, a `SourceFetch` provenance row + advances to `FETCHED` + the
  next-stage outbox event.
- **Emits** — `strategy.next_outbox_event(...)`: `parse_source` for web,
  `filter_documents` for local files.
- **Failure modes** — `UnsupportedSourceError` → `SKIPPED_UNSUPPORTED` (e.g.
  disallowed content type); transient `SourceFetchError` → `FAILED_TRANSIENT`
  and **re-raises** so Dramatiq retries; permanent `SourceFetchError` →
  `FAILED_PERMANENT` (no retry).

## filter_documents — local chain only

`backend/actors/filter_documents_actor/handler.py`

Keyword relevance gate between `fetch_source` (local strategy) and
`parse_source`. Web targets never enter it.

- **Consumes** `ingest.crawl.file.filter.v1` — `{crawl_target_id, pipeline_id?}`
  (`FilterDocumentsPayload`).
- **Acquire** `FETCHED | FILTERING → FILTERING`.
- **Does** — extracts the document title from the XML and classifies it with
  the keyword strategy (include + exclude lists from `filter_documents` config).
  Empty title (non-XML content) falls back to body matching. When the gate is
  disabled or both lists are empty, everything passes.
- **Emits / transitions** — relevant → `FILTERED` + `parse_source` outbox event;
  not relevant → `SKIPPED` with `skip_reason="not_relevant"`, and the chain
  stops there.

## parse_source — stage 2

`backend/actors/parse_source_actor/handler.py`

- **Consumes** `ingest.crawl.source.parse.v1` — `{crawl_target_id, pipeline_id?}`
  (`ParseSourcePayload`).
- **Acquire** `FETCHED | PARSING | FILTERED → PARSING` (the `FILTERED` entry is
  how the local-file chain rejoins here after `filter_documents`).
- **Does** — the parse strategy picks a parser (explicit override from
  `parse_source.parser`, else by content type), extracts normalized text,
  validates metadata/intermediate JSON sizes, and writes the parsed text to
  disk. In one transaction: upserts a `Document` (with `content_hash`,
  `text_hash`, parser/chunker versions, provenance) → `PARSED` → outbox
  `chunk_document`.
- **Failure modes** — unresolvable parser (`parse` returns `None`) →
  `SKIPPED_UNSUPPORTED`; missing `SourceFetch` row → `FAILED_TRANSIENT` +
  raise (treated as a not-yet-visible commit, so Dramatiq retries).

## chunk_document — stage 3

`backend/actors/chunk_document_actor/handler.py`

- **Consumes** `ingest.crawl.document.chunk.v1` — `{crawl_target_id,
  pipeline_id?}` (`ChunkDocumentPayload`).
- **Acquire** `PARSED | CHUNKING → CHUNKING`.
- **Does** — builds a `ChunkInput` from the parsed text (plus the raw fetched
  bytes, re-read from disk, for structure-aware chunkers), runs the run's
  selected chunker plugin, and extracts links from each chunk's text. In one
  transaction: upserts `DocumentChunk` rows (unique on `document_id +
  chunk_index`), upserts `DiscoveredLink` rows (unique on `source_chunk_id +
  normalized_url`) → `CHUNKED` → outbox `schedule_embeddings`.
- **Failure modes** — missing `Document` → `FAILED_TRANSIENT` + raise.
  Reserved-metadata collisions raise `ValueError` (a hard bug in a chunker
  plugin, not retried into success).

## schedule_embeddings — stage 4

`backend/actors/schedule_embeddings_actor/handler.py`

Fan-out point: turns one document's chunks into N embed jobs.

- **Consumes** `ingest.crawl.embeddings.schedule.v1` — `{crawl_target_id,
  pipeline_id?}` (`ScheduleEmbeddingsPayload`).
- **Acquire** `CHUNKED | SCHEDULING → SCHEDULING`.
- **Does** — splits the document's chunks into batches of `batch_size`
  (`schedule_embeddings.batch_size`, default `32`) and, in one transaction,
  writes **one `embed_chunks` outbox event per batch**
  (`dedup_key = embed:<document_id>:<start>`), then one `schedule_discovered_links`
  outbox event.
- **Emits** — `embed_chunks` (×N batches) + `schedule_discovered_links`.
- **Counters** — each *newly inserted* embed event bumps the run's
  `embeddings_scheduled` by one (redeliveries are deduped and don't
  double-count). This is half of the run-completion condition.

## schedule_discovered_links — stage 5

`backend/actors/schedule_discovered_links_actor/handler.py`

- **Consumes** `ingest.crawl.links.schedule.v1` — `{crawl_target_id,
  pipeline_id?}` (`ScheduleDiscoveredLinksPayload`).
- **Acquire** `SCHEDULING → SCHEDULING` (locks without advancing yet).
- **Does** — writes one **frontier** outbox event per pending discovered link
  (`dedup_key = frontier:<link_id>`, targeting `validate_source`, so links loop
  back to the top of the chain) when `schedule_discovered_links.follow_child_links`
  is on, and marks those links scheduled — all in one transaction with the
  status change, so downstream work is durable before the target is "done".
- **Transitions** — if the document has zero chunks, no document, or every chunk
  is already embedded (embed raced ahead) → `PROCESSED` directly; otherwise →
  `EMBEDDING` (an intermediate "waiting on embeds" state that `embed_chunks`
  later finalizes to `PROCESSED`).
- **Also emits** — a `track_pipeline_status` poke.
- **Crawl scope lives here** — `follow_child_links` / `follow_cross_domain` /
  `max_depth` are `schedule_discovered_links` actor config, the single source of
  truth the crawl reads. They are **not** dataset fields (a `WebDataset` is only
  a name + seed URL). Today only `follow_child_links` is enforced (same-origin is
  enforced separately at `validate_source`); the other two are recorded but not
  yet wired in.

## embed_chunks — stage 7 (terminal)

`backend/actors/embed_chunks_actor/handler.py`

- **Consumes** `ingest.embed.chunk.generate.v1` — `{document_id, chunk_ids[],
  pipeline_id?}` (`EmbedChunksPayload`; note this one carries the document +
  chunk ids, not a crawl-target id).
- **Does** — reads the run's provider snapshot from
  `actor_configs.embed_chunks.provider` (cached per `pipeline_id`), builds the
  provider-agnostic embed client, ensures the Qdrant collection exists, encodes
  each chunk (internal `BATCH_SIZE = 4` sub-batching), and upserts vectors into
  Qdrant **keyed by chunk id** (so re-embedding overwrites instead of
  duplicating), with `document_id` / `chunk_type` / `pipeline_run_id` payload.
- **Then, once the whole batch is upserted, in one transaction** — marks those
  chunks `embedded`; **finalizes the owning target to `PROCESSED` iff every
  chunk of its document is now embedded**
  (`finalize_target_if_all_chunks_embedded`); and, for a tracked run, writes a
  `track_pipeline_status` poke and bumps `embeddings_completed` by one (deduped,
  so redeliveries don't double-count).
- **Config source** — collection, similarity/distance and provider all come from
  the run's `pipeline_run` snapshot, never global env, so the index side and the
  query (search) side agree on exactly one configuration.

## track_pipeline_status — cross-cutting listener

`backend/actors/track_pipeline_status_actor/handler.py`

Not a numbered stage. Poked from the tail of both chains — by `embed_chunks`
(every finished batch) and by `schedule_discovered_links` (every processed
target). Both triggers are required because the last embed for a run can finish
either before or after its owning target reaches `processed`; relying on one
leaves a race where the run never completes.

- **Consumes** `ingest.pipeline.status.track.v1` — `{pipeline_id}`
  (`TrackPipelineStatusPayload`; the only payload with no crawl-target id — the
  tracker re-derives everything from the DB).
- **Completes the run iff both hold**:
  1. `crawl_targets.count_active_for_pipeline(pipeline_id) == 0` — every target
     reached a terminal-or-`processed` state (a target in `embedding` still
     counts as active).
  2. `embeddings_completed >= embeddings_scheduled` — every scheduled embed batch
     finished.
- **On success** — sets the run `completed` and stamps `finished_at`. Every other
  invocation is a deliberate no-op ("not done yet"); the actor is poked far more
  often than a run actually completes.
</content>
