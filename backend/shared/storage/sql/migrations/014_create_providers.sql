-- A provider supplies a model, discriminated by `provider_type`, and is used
-- for a particular `model_type` (embedding/text/long-text/reranker).
-- Variant-specific fields are kept as flat, nullable columns (rather than a
-- JSONB blob) so they stay queryable/indexable like every other table here;
-- only the columns relevant to a row's `provider_type` are populated.
CREATE TABLE IF NOT EXISTS providers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    provider_type   TEXT NOT NULL,
    model_type      TEXT NOT NULL,

    -- ollama
    port            INTEGER,

    -- ollama + remote
    model_name      TEXT,

    -- remote
    base_url        TEXT,
    api_key         TEXT,
    organization    TEXT,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS providers_created_at_idx
    ON providers (created_at);
