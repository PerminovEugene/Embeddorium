-- Drop the top-level provider JSONB column from pipeline_runs.
--
-- Idempotent: DROP COLUMN IF EXISTS is a no-op when the column is already
-- absent (e.g. fresh DBs where migration 015 never added it, or this migration
-- has already run). Safe to execute multiple times.
--
-- Background
-- ----------
-- The provider snapshot was previously stored as a separate top-level column
-- alongside dataset + actor_configs. It has been moved into
-- actor_configs.embed_chunks.provider so that the provider config lives next
-- to the actor that uses it (embed_chunks), leaving room for other actors to
-- carry their own provider snapshots independently in the future.
--
-- The GIN index on actor_configs already covers provider queries made via
-- actor_configs.embed_chunks.provider, so no new index is needed.

ALTER TABLE pipeline_runs DROP COLUMN IF EXISTS provider;

-- Remove the GIN index that targeted the old provider column, if it exists
-- (it was never created in 015, but guard defensively for any ad-hoc indexes).
DROP INDEX IF EXISTS pipeline_runs_provider_idx;
