-- Scope crawl_target dedup to a single pipeline run.
--
-- Before this migration dedup was global: a (group, normalized_url) pair that
-- existed in ANY previous run would prevent the same source from being
-- re-processed in a new run. After this migration dedup is per-run: two runs
-- on the same dataset share no dedup state, while within ONE run the same
-- source is still processed only once.
--
-- NULL pipeline_id is left valid for legacy rows (targets created before this
-- migration) so that the column addition is purely additive.
--
-- The ON DELETE CASCADE means deleting a pipeline_run also removes its
-- crawl_targets, which keeps the FK consistent without manual cleanup.

ALTER TABLE crawl_targets ADD COLUMN IF NOT EXISTS pipeline_id UUID
    REFERENCES pipeline_runs (id) ON DELETE CASCADE;

-- Supports the per-run dedup lookup in find_active_by_normalized_url
-- (pipeline_id, normalized_url) and the cascade-delete path.
CREATE INDEX IF NOT EXISTS crawl_targets_pipeline_normalized_url_idx
    ON crawl_targets (pipeline_id, normalized_url);
