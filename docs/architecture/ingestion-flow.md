# Ingestion flow

Web and local XML inputs use the same actor sequence. `validate_source` and
`fetch_source` select `web` or `local` strategies from the run's dataset type.
Both source types then pass through the keyword filter.

```text
launch
  -> validate_source
  -> fetch_source
  -> filter_documents
  -> parse_source
  -> chunk_document
  -> schedule_embeddings
       -> embed_chunks -------------------> track_pipeline_status
       -> schedule_discovered_links ------> track_pipeline_status
              -> validate_source (discovered web links)
```

## Stages

| Actor | Queue | Main result |
| --- | --- | --- |
| `validate_source` | `ingest.crawl.source.validate.v1` | Normalize/validate/dedup, create queued target |
| `fetch_source` | `ingest.crawl.source.fetch.v1` | Raw artifact and fetch provenance |
| `filter_documents` | `ingest.crawl.file.filter.v1` | Pass to `filtered` or skip as not relevant |
| `parse_source` | `ingest.crawl.source.parse.v1` | Parsed artifact and document |
| `chunk_document` | `ingest.crawl.document.chunk.v1` | Chunks and discovered links |
| `schedule_embeddings` | `ingest.crawl.embeddings.schedule.v1` | Batched embed events and link-scheduling event |
| `schedule_discovered_links` | `ingest.crawl.links.schedule.v1` | Frontier events and target finalization/wait state |
| `embed_chunks` | `ingest.embed.chunk.generate.v1` | Qdrant points and embedded chunk states |
| `track_pipeline_status` | `ingest.pipeline.status.track.v1` | Complete a finished run |

Every actor declares `max_retries=3`. Stage handlers use compact ID payloads
and reload data/config from storage.

## Transaction boundaries

Launch enqueues `validate_source` directly. After saving a target,
`validate_source` also enqueues `fetch_source` directly. These two handoffs do
not use the SQL outbox; a process failure between persisting the target and
publishing fetch can leave a queued target without a message.

From `fetch_source` onward, a stage normally commits its data/status and next
event in one SQL transaction. The dispatcher later publishes the event.

## Target statuses

```text
queued -> fetching -> fetched -> filtering -> filtered -> parsing -> parsed
       -> chunking -> chunked -> scheduling -> embedding -> processed
```

Zero-chunk documents can move directly from `scheduling` to `processed`.
Terminal alternatives include `skipped`, `skipped_unsupported`,
`failed_transient`, and `failed_permanent`.
