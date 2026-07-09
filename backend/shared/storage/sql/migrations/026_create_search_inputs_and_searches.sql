-- Persists every search query launch and its results, split across two
-- tables:
--   * search_inputs: the raw user-supplied query text, stored separately so
--     it is not duplicated inline on every search row and can be inspected/
--     reused on its own (e.g. for search-history features).
--   * searches: one row per query launch, recording which pipeline run it
--     was executed against, the search parameters used (search_config), and
--     the result hits returned (results).
--
-- The ON DELETE CASCADE on both FKs means deleting a pipeline_run or a
-- search_input also removes any searches that reference it, keeping the FKs
-- consistent without manual cleanup.
--
-- Idempotency (required: run_migrations() re-executes every *.sql file in
-- migrations/ inside one transaction on every boot):
--   * CREATE TABLE IF NOT EXISTS is a no-op once the tables exist.
--   * CREATE INDEX IF NOT EXISTS is a no-op once the indexes exist.

CREATE TABLE IF NOT EXISTS search_inputs (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS searches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id     UUID NOT NULL REFERENCES pipeline_runs (id) ON DELETE CASCADE,
    user_input_id   UUID NOT NULL REFERENCES search_inputs (id) ON DELETE CASCADE,
    search_config   JSONB NOT NULL DEFAULT '{}',
    results         JSONB NOT NULL DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS searches_pipeline_id_idx
    ON searches (pipeline_id);

CREATE INDEX IF NOT EXISTS searches_created_at_idx
    ON searches (created_at);
