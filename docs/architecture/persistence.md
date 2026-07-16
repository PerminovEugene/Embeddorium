# Persistence

## PostgreSQL

| Table | Stored data |
| --- | --- |
| `datasets` | Web URL or local path list |
| `providers` | Provider/capability and validated JSON config |
| `pipeline_runs` | Dataset/actor snapshots, lifecycle, batch counters |
| `crawl_targets` | Per-run source identity, lineage, status, errors |
| `source_fetches` | Fetch provenance and raw path |
| `documents` | Parse provenance, structured output, parsed path |
| `document_chunks` | Text, order, type, metadata, offsets, embed status |
| `discovered_links` | Source lineage and scheduling state |
| `outbox_events` | Durable downstream messages and publish state |
| `search_inputs` | Query text |
| `searches` | Run-scoped search config and ordered JSON hits |

Migrations are ordered SQL files. The migration runner executes every file on
every invocation, so migrations are expected to be idempotent. The Compose
Postgres image is based on version 17 and builds `pg_textsearch` tag `v1.3.1`
for the BM25 index.

## Filesystem

Raw and parsed content is stored relative to `PIPELINE_RUNS_DIR`, defaulting to
`/tmp/pipeline_runs` inside services and bind-mounted to
`tmp/pipeline_run` on the host. Layout:

```text
<run-id>[__<run-name>]/
  logs/
  sources/<crawl-target-id>/
    raw/content.<ext>
    parsed/content.txt
```

The DB stores relative paths, which allows all containers sharing the mount to
resolve the same artifact.

## Qdrant

Collections are named `BASE_<dataset-name>_qwen_embed_8b`. A point ID is the
chunk UUID. Payload fields include chunk/document IDs, chunk index/type,
pipeline run ID, and namespaced system/custom metadata. Re-upserting a chunk
overwrites the same point.

Collections are created only when absent. Their vector size and distance cannot
be changed by a later run that reuses the same collection name.

## Delete behavior

Deleting a run cascades SQL crawl targets, their source fetches, and searches,
and removes matching run directories. `documents.crawl_target_id` is not a
foreign key, so documents and their chunks are not automatically removed by
run deletion. Search-input rows and Qdrant points are also not removed by that
operation.
