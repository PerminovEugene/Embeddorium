-- Links discovered while parsing, persisted before being scheduled to the frontier.
CREATE TABLE IF NOT EXISTS discovered_links (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_document_id UUID REFERENCES documents (id) ON DELETE CASCADE,
    source_chunk_id    UUID REFERENCES document_chunks (id) ON DELETE CASCADE,
    raw_url            TEXT NOT NULL,
    normalized_url     TEXT NOT NULL,
    anchor_text        TEXT,
    context_text       TEXT,
    "group"            TEXT NOT NULL,
    status             VARCHAR(32) NOT NULL DEFAULT 'pending',
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One discovered link per (source chunk, normalized url): retries are no-ops.
CREATE UNIQUE INDEX IF NOT EXISTS discovered_links_chunk_url_key
    ON discovered_links (source_chunk_id, normalized_url);

CREATE INDEX IF NOT EXISTS discovered_links_status_idx
    ON discovered_links (status);
