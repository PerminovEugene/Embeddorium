-- Collapse the providers table's per-type flat columns into a single `config`
-- JSONB blob, validated at the application layer against the selected
-- provider-type adapter's declared fields (backend/plugins/provider_types).
--
-- Migrations here run in full on every startup, so every step must be
-- idempotent: the backfill + column drops live in a DO block gated on the old
-- columns still existing, so a second run is a no-op.
ALTER TABLE providers
    ADD COLUMN IF NOT EXISTS config JSONB NOT NULL DEFAULT '{}'::jsonb;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'providers' AND column_name = 'model_name'
    ) THEN
        -- Backfill config from the old flat columns; jsonb_strip_nulls drops
        -- the keys that don't apply to a row's provider_type.
        UPDATE providers
        SET config = jsonb_strip_nulls(jsonb_build_object(
            'port', port,
            'model_name', model_name,
            'url', base_url,
            'api_key', api_key,
            'organization', organization
        ))
        WHERE config = '{}'::jsonb;

        -- The former generic "remote" provider type is now the "openai"
        -- (OpenAI-compatible) adapter.
        UPDATE providers SET provider_type = 'openai' WHERE provider_type = 'remote';

        ALTER TABLE providers DROP COLUMN port;
        ALTER TABLE providers DROP COLUMN model_name;
        ALTER TABLE providers DROP COLUMN base_url;
        ALTER TABLE providers DROP COLUMN api_key;
        ALTER TABLE providers DROP COLUMN organization;
    END IF;
END $$;
