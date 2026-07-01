-- Legal-structure-aware chunking: tag each chunk with its type (legal_body,
-- act_title, amendment_history, legal_metadata, or generic "passage") and carry
-- structured legal metadata (actTitle, chapterTitle, sectionNumber, legalPath,
-- subsectionRange, ...) so retrieval can prefer legal_body and filter the rest.
ALTER TABLE document_chunks
    ADD COLUMN IF NOT EXISTS chunk_type TEXT NOT NULL DEFAULT 'passage';

ALTER TABLE document_chunks
    ADD COLUMN IF NOT EXISTS chunk_metadata JSONB NOT NULL DEFAULT '{}';

CREATE INDEX IF NOT EXISTS document_chunks_chunk_type_idx
    ON document_chunks (chunk_type);
