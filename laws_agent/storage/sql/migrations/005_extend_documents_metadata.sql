-- Fetch/parse provenance metadata for documents.
ALTER TABLE documents ADD COLUMN IF NOT EXISTS crawl_target_id UUID;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS normalized_url  TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS final_url       TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS http_status     INTEGER;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS content_type    TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS content_hash    TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS text_hash       TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS parser_version  TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS chunker_version TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS retrieved_at    TIMESTAMPTZ;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS "group"         TEXT;
-- Normalized parsed text, carried from parse_source to chunk_document.
ALTER TABLE documents ADD COLUMN IF NOT EXISTS text            TEXT;

-- language is real language now, no longer the crawl group.
ALTER TABLE documents ALTER COLUMN language SET DEFAULT 'unknown';

-- One processed document per crawl target (idempotent re-processing).
CREATE UNIQUE INDEX IF NOT EXISTS documents_crawl_target_id_key
    ON documents (crawl_target_id)
    WHERE crawl_target_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS documents_content_hash_idx ON documents (content_hash);
CREATE INDEX IF NOT EXISTS documents_text_hash_idx ON documents (text_hash);
