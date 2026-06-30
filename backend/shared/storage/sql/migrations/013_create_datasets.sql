-- A dataset describes where ingestion content comes from, discriminated by
-- `source_type`. Variant-specific fields are kept as flat, nullable columns
-- (rather than a JSONB blob) so they stay queryable/indexable like every
-- other table here; only the columns relevant to a row's `source_type` are
-- populated.
CREATE TABLE IF NOT EXISTS datasets (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                        TEXT NOT NULL,
    source_type                 TEXT NOT NULL,

    -- web
    url                         TEXT,
    process_child_links         BOOLEAN,
    process_cross_domain_links  BOOLEAN,
    depth                       INTEGER,

    -- local
    paths                       TEXT[],

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS datasets_created_at_idx
    ON datasets (created_at);
