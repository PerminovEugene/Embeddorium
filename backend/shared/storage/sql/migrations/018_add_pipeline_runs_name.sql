-- Add a user-supplied display name to pipeline runs.
--
-- Until now a run had no name of its own: the UI let the user type a pipeline
-- name but it was never persisted, so every list/select fell back to showing
-- the dataset name. This adds the column so the typed name round-trips.
--
-- Idempotent (the runner re-applies every file on every boot): IF NOT EXISTS
-- guard on the column, and the backfill only touches NULL rows.

ALTER TABLE pipeline_runs
    ADD COLUMN IF NOT EXISTS name TEXT;

-- Backfill pre-existing rows from the dataset snapshot's name so they keep a
-- sensible label instead of going blank.
UPDATE pipeline_runs
    SET name = COALESCE(NULLIF(dataset->>'name', ''), 'Untitled pipeline')
    WHERE name IS NULL;
