-- Reshape pipeline_runs: drop legacy columns and add the new snapshot columns.
--
-- Idempotent: safe to run on an existing dev DB (old columns are dropped, new
-- ones are added) and a no-op on a fresh DB (migration 011 creates the old
-- shape in the same boot transaction; this migration then reshapes it).
--
-- Legacy columns removed
-- ----------------------
-- "group"         TEXT NOT NULL             -- replaced by dataset JSONB snapshot
-- source_type     TEXT NOT NULL DEFAULT 'web'
-- collection_name TEXT NOT NULL             -- moved into actor_configs.vector_store.collection
-- settings        JSONB NOT NULL DEFAULT '{}' -- replaced by provider + actor_configs

ALTER TABLE pipeline_runs
    DROP COLUMN IF EXISTS "group",
    DROP COLUMN IF EXISTS source_type,
    DROP COLUMN IF EXISTS collection_name,
    DROP COLUMN IF EXISTS settings;

-- New snapshot columns. Using IF NOT EXISTS guards so re-running is safe.
ALTER TABLE pipeline_runs
    ADD COLUMN IF NOT EXISTS dataset      JSONB,
    ADD COLUMN IF NOT EXISTS provider     JSONB,
    ADD COLUMN IF NOT EXISTS actor_configs JSONB NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS status       TEXT  NOT NULL DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS started_at   TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS finished_at  TIMESTAMPTZ;

-- Backfill: rows inserted by 011 before this migration ran will have NULL
-- dataset/provider; set them to empty objects so the NOT NULL constraint
-- added below doesn't block the ALTER.
UPDATE pipeline_runs SET dataset  = '{}'::jsonb WHERE dataset  IS NULL;
UPDATE pipeline_runs SET provider = '{}'::jsonb WHERE provider IS NULL;

-- Now tighten the constraints on the new columns.
ALTER TABLE pipeline_runs
    ALTER COLUMN dataset  SET NOT NULL,
    ALTER COLUMN provider SET NOT NULL;

-- Remove old indexes that referenced dropped columns.
DROP INDEX IF EXISTS pipeline_runs_group_idx;
DROP INDEX IF EXISTS pipeline_runs_group_key;
DROP INDEX IF EXISTS pipeline_runs_settings_idx;

-- Useful indexes on the new shape.
CREATE INDEX IF NOT EXISTS pipeline_runs_status_idx
    ON pipeline_runs (status);

CREATE INDEX IF NOT EXISTS pipeline_runs_dataset_idx
    ON pipeline_runs USING GIN (dataset);

CREATE INDEX IF NOT EXISTS pipeline_runs_actor_configs_idx
    ON pipeline_runs USING GIN (actor_configs);
