ALTER TABLE document_chunks DROP COLUMN IF EXISTS links;

CREATE TABLE IF NOT EXISTS crawl_targets (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "group"            TEXT NOT NULL,
    original_url       TEXT NOT NULL,
    normalized_url     TEXT NOT NULL,
    status             VARCHAR(32) NOT NULL DEFAULT 'discovered',
    depth              INTEGER NOT NULL DEFAULT 0,
    document_id        UUID REFERENCES documents (id) ON DELETE SET NULL,
    parent_chunk_id    UUID REFERENCES document_chunks (id) ON DELETE SET NULL,
    parent_document_id UUID REFERENCES documents (id) ON DELETE SET NULL,
    error              TEXT,
    skip_reason        TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS crawl_targets_normalized_url_idx
    ON crawl_targets (normalized_url);

CREATE INDEX IF NOT EXISTS crawl_targets_status_idx
    ON crawl_targets (status);

CREATE INDEX IF NOT EXISTS crawl_targets_parent_chunk_id_idx
    ON crawl_targets (parent_chunk_id);
