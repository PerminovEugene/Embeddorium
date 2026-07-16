-- Crawl scope (follow child links / cross-domain / depth) is configured on the
-- ingestion pipeline's `schedule_discovered_links` actor config, which is the
-- single source of truth the actor actually reads. These dataset-level columns
-- were never consumed by any actor (dormant duplicates) — drop them.
ALTER TABLE datasets
    DROP COLUMN IF EXISTS process_child_links,
    DROP COLUMN IF EXISTS process_cross_domain_links,
    DROP COLUMN IF EXISTS depth;
