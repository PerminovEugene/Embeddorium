-- One chunk per (document, index): chunk_document can re-run without duplicating.
CREATE UNIQUE INDEX IF NOT EXISTS document_chunks_doc_idx_key
    ON document_chunks (document_id, chunk_index);
