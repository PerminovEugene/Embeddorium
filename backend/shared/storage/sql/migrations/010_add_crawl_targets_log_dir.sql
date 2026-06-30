-- Relative per-URL log folder (nested under its parent's), used to route
-- file logging: see backend.shared.log_routing.
ALTER TABLE crawl_targets ADD COLUMN IF NOT EXISTS log_dir TEXT;
