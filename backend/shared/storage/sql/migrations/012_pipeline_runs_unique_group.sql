-- Historically this migration created a UNIQUE index on pipeline_runs("group")
-- so the "record at the start of the pipeline" write could be idempotent
-- (one row per ingestion group via INSERT ... ON CONFLICT DO NOTHING).
--
-- That design is gone: 015_reshape_pipeline_runs.sql drops the "group" column
-- entirely (runs are now keyed by dataset/provider snapshots, not group).
--
-- The index can therefore no longer be created here. The migration runner
-- re-applies every file on every boot (no applied-migration tracking), so on
-- any DB already reshaped by 015 the "group" column does not exist and
-- CREATE INDEX ... ON ("group") is a hard error (CREATE TABLE IF NOT EXISTS in
-- 011 is a harmless no-op, but an index on a missing column is not). This is
-- the same hazard 011 documents and avoids.
--
-- This file is kept (rather than deleted) to preserve the migration sequence
-- numbering. It now only drops any leftover group indexes, which is safe on
-- both fresh and reshaped databases; 015 also drops them.
DROP INDEX IF EXISTS pipeline_runs_group_idx;
DROP INDEX IF EXISTS pipeline_runs_group_key;
