-- Add per-run embedding batch counters to pipeline_runs.
--
-- track_pipeline_status needs a cheap way to know whether every embed batch
-- that was ever scheduled for a run has also finished, without scanning the
-- outbox or the chunk tables. embeddings_scheduled counts batches emitted by
-- schedule_embeddings; embeddings_completed counts batches finished by
-- embed_chunks. Both are incremented exactly once per batch (see
-- UnitOfWork.add_outbox's insert-or-noop return value), so a run is safe to
-- complete once crawl_targets has no more active work AND
-- embeddings_completed >= embeddings_scheduled.
--
-- Idempotent (the runner re-applies every file on every boot): IF NOT EXISTS
-- guards on both columns. Old rows default to 0, matching a run that has not
-- scheduled or completed any embeds yet.

ALTER TABLE pipeline_runs
    ADD COLUMN IF NOT EXISTS embeddings_scheduled INTEGER NOT NULL DEFAULT 0;

ALTER TABLE pipeline_runs
    ADD COLUMN IF NOT EXISTS embeddings_completed INTEGER NOT NULL DEFAULT 0;
