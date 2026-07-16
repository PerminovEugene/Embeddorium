# Data lifecycle

## Configuration to run

1. A user creates a dataset and provider.
2. Creating a pipeline run copies the dataset and selected embedding provider
   into JSON snapshots and resolves actor defaults.
3. Launching publishes source seeds and marks the run `running`.

Changes to a dataset or provider after step 2 do not change that run.

## Source to searchable data

1. A source becomes a `crawl_target`.
2. Raw content is written to the run filesystem; fetch provenance goes to
   `source_fetches`.
3. Parsed text is written to the filesystem; hashes, parser output, and its path
   go to `documents`.
4. Chunk text and metadata go to `document_chunks`; links go to
   `discovered_links`.
5. A normalized vector is upserted into Qdrant with the chunk UUID as point ID.
6. The chunk becomes `embedded`; its target becomes `processed` once all sibling
   chunks are embedded.

## Search history

Each query input is saved with one search record containing its selected run,
method, Top K, optional reranker configuration, and returned hit list. This
write is best-effort.

## Deletion and retention

- Deleting a pipeline run cascades its crawl targets and searches in SQL and
  calls filesystem cleanup for folders whose name begins with the run UUID.
- The code does not delete that run's Qdrant points. Points remain but normal
  searches cannot select a deleted run.
- Deleting a dataset or provider does not remove run snapshots.
- `scripts/full-clean.sh` purges queues, deletes all Qdrant collections, resets
  the Postgres schema, clears logs, and rebuilds workers.

Automatic retention, archival, and per-run Qdrant cleanup are not implemented:
{MISSED_INFO}
