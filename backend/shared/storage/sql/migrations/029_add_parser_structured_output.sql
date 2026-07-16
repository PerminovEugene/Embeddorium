ALTER TABLE documents
    ADD COLUMN parser_name TEXT,
    ADD COLUMN parser_output_format TEXT,
    ADD COLUMN parser_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN parser_intermediate JSONB;
