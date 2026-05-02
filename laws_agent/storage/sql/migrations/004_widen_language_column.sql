DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'documents'
          AND column_name = 'language'
          AND data_type = 'character'
          AND character_maximum_length = 2
    ) THEN
        ALTER TABLE documents ALTER COLUMN language TYPE VARCHAR(100);
    END IF;
END $$;
