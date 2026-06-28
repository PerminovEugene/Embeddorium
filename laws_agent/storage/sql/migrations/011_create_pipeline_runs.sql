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

CREATE INDEX IF NOT EXISTS pipeline_runs_group_idx
    ON pipeline_runs ("group");

CREATE INDEX IF NOT EXISTS pipeline_runs_created_at_idx
    ON pipeline_runs (created_at);

CREATE INDEX IF NOT EXISTS pipeline_runs_settings_idx
    ON pipeline_runs USING GIN (settings);
