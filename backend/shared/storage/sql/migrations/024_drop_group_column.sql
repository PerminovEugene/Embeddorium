-- Drop the redundant "group" column from crawl_targets, documents, and
-- discovered_links.
--
-- "group" was always set to the dataset's own name at seed time (see
-- server/pipeline_launch.py: `dataset.get("name", "")`) and carried verbatim
-- through every downstream actor payload/row purely as a copy — it never
-- diverged from the dataset name and was never used to partition anything
-- that ``pipeline_id`` doesn't already partition:
--
-- * Dedup (``CrawlTargetRepository.find_active_by_normalized_url``) is scoped
--   to ``pipeline_id`` (see migration 017); filtering on "group" too was a
--   no-op since one pipeline run always has exactly one dataset/group.
-- * The Qdrant collection to write to is resolved from the run's own
--   recorded ``actor_configs.vector_store.collection`` (see
--   ``embed_chunks_actor.launcher._load_embed_config``), not from "group".
-- * The dataset name for any row with a ``pipeline_id`` is already reachable
--   via ``pipeline_runs.dataset ->> 'name'``.
--
-- This mirrors migration 015, which already dropped the equivalent "group"
-- column from ``pipeline_runs`` in favor of its ``dataset`` JSONB snapshot.
--
-- Idempotent (the runner re-applies every file on every boot): IF EXISTS
-- guards every drop, so this is a no-op on a database that has already been
-- migrated.

ALTER TABLE crawl_targets DROP COLUMN IF EXISTS "group";
ALTER TABLE documents DROP COLUMN IF EXISTS "group";
ALTER TABLE discovered_links DROP COLUMN IF EXISTS "group";
