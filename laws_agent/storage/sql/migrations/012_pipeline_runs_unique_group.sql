-- One pipeline-run row per ingestion group: the group maps 1:1 to its Qdrant
-- collection (LAWS_<group>_qwen_embed_8b), which is the unit the UI searches.
-- A unique index makes the "record at the start of the pipeline" write
-- idempotent and race-safe (INSERT ... ON CONFLICT DO NOTHING), so the many
-- entry-actor invocations of one run collapse to a single row.
DROP INDEX IF EXISTS pipeline_runs_group_idx;

CREATE UNIQUE INDEX IF NOT EXISTS pipeline_runs_group_key
    ON pipeline_runs ("group");
