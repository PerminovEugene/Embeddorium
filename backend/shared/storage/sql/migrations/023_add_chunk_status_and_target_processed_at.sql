-- Chunk-level embedding status + per-target processing timestamp.
--
-- Today a crawl target is marked PROCESSED as soon as schedule_discovered_links
-- runs, which only means embed batches were *emitted* (schedule_embeddings),
-- not that they were actually embedded (embed_chunks, asynchronous). This
-- migration adds the two columns needed to fix that:
--
-- document_chunks.status tracks each chunk's own embedding lifecycle
-- ("pending" -> "embedded"), written by embed_chunks once a chunk's vector is
-- upserted into Qdrant. A crawl target only reaches PROCESSED once every
-- chunk of its document is "embedded" (see finalize_target_if_all_chunks_embedded
-- in unit_of_work.py) — or immediately, for a target whose document has zero
-- chunks, since "all chunks embedded" is vacuously true and no embed batch
-- will ever be scheduled for it.
--
-- crawl_targets.processed_at records when a target reached PROCESSED, so
-- (processed_at - created_at) gives a per-target processing time without a
-- separate stopwatch/counter.
--
-- Idempotent (the runner re-applies every file on every boot): IF NOT EXISTS
-- guards both columns. Old chunk rows default to 'pending' (safe: nothing
-- re-derives their embedded state from Qdrant, but they were already embedded
-- under the pre-migration flow, so operators should backfill 'embedded' for
-- historical runs if precise old-run progress numbers matter). Old target
-- rows default processed_at to NULL, which just means "processing time
-- unknown" for pre-migration PROCESSED rows.

ALTER TABLE document_chunks
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'pending';

CREATE INDEX IF NOT EXISTS document_chunks_document_id_status_idx
    ON document_chunks (document_id, status);

ALTER TABLE crawl_targets
    ADD COLUMN IF NOT EXISTS processed_at TIMESTAMPTZ;
