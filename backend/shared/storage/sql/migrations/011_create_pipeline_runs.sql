-- Persists the launch configuration of one ingestion/RAG pipeline run, so
-- runs are reproducible and comparable. Per-actor settings (chunking,
-- embedding, vector store, agent/LLM) live in `settings`, grouped by the
-- pipeline actor that consumes them (see README "Pipeline flow"). Dataset
-- identifiers are kept as top-level columns too, so runs can be queried
-- without digging into JSONB.
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "group"         TEXT NOT NULL,
    source_type     TEXT NOT NULL DEFAULT 'web',
    collection_name TEXT NOT NULL,
    settings        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- NOTE: indexes on "group" and settings are intentionally NOT created here.
-- Migration 015_reshape_pipeline_runs.sql drops both columns ("group" and
-- settings) and drops those indexes. Because the migration runner re-applies
-- every file on every boot (no applied-migration tracking), creating those
-- indexes here would crash on any DB that has already been reshaped by 015:
-- CREATE TABLE IF NOT EXISTS is a no-op (table exists, columns already gone),
-- but an index on a nonexistent column is a hard error.
-- The indexes are therefore useless in any case — 015 removes them immediately
-- on a fresh DB and they never exist on a reshaped one.
CREATE INDEX IF NOT EXISTS pipeline_runs_created_at_idx
    ON pipeline_runs (created_at);
