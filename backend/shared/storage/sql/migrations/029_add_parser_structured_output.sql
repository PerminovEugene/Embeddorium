ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS parser_name TEXT,
    ADD COLUMN IF NOT EXISTS parser_output_format TEXT,
    ADD COLUMN IF NOT EXISTS parser_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS parser_intermediate JSONB;
