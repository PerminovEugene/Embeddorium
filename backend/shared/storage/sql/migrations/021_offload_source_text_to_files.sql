-- Move large raw/parsed text out of Postgres onto disk; store file paths instead.
-- The raw fetched content and normalised parsed text are now written to
-- {PIPELINE_RUNS_DIR}/{pipeline_id}/sources/{source_id}/{kind}/content.{ext}
-- and only the relative path (relative to PIPELINE_RUNS_DIR) is persisted here.
ALTER TABLE source_fetches ADD COLUMN IF NOT EXISTS raw_content_path TEXT;
ALTER TABLE source_fetches DROP COLUMN IF EXISTS raw_content;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS text_path TEXT;
ALTER TABLE documents DROP COLUMN IF EXISTS text;
