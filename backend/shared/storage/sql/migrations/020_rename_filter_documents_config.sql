-- Rename the filter_tax_acts key in pipeline_runs.actor_configs to
-- filter_documents, and update crawl_targets.skip_reason to the generic value.
-- Idempotent: the WHERE clause guards against applying twice.

UPDATE pipeline_runs
SET actor_configs = actor_configs - 'filter_tax_acts'
    || jsonb_build_object('filter_documents', actor_configs -> 'filter_tax_acts')
WHERE actor_configs ? 'filter_tax_acts';

UPDATE crawl_targets
SET skip_reason = 'not_relevant'
WHERE skip_reason = 'not_tax_related';
