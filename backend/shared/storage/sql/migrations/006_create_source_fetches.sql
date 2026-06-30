-- Raw fetch result + provenance, written by fetch_source, read by parse_source.
CREATE TABLE IF NOT EXISTS source_fetches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    crawl_target_id UUID NOT NULL REFERENCES crawl_targets (id) ON DELETE CASCADE,
    final_url       TEXT NOT NULL,
    http_status     INTEGER NOT NULL,
    content_type    TEXT,
    content_hash    TEXT NOT NULL,
    raw_content     TEXT NOT NULL,
    redirect_chain  JSONB NOT NULL DEFAULT '[]',
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One fetch per crawl target; a retry upserts rather than duplicates.
CREATE UNIQUE INDEX IF NOT EXISTS source_fetches_crawl_target_id_key
    ON source_fetches (crawl_target_id);
