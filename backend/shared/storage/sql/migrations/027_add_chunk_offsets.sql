-- Chunk position within the source document.
--
-- Adds start_offset / end_offset to document_chunks: character offsets of the
-- chunk within the parsed source text (the document's text_path content),
-- start inclusive / end exclusive. Written by chunk_document from the chunker
-- plugin's output so retrieval can highlight or locate a chunk in its source.
--
-- Both columns are nullable: existing rows predate position tracking, and
-- chunkers whose output is not a contiguous slice of the source (e.g. the
-- structure-aware legal_xml chunker) legitimately don't report positions.
--
-- Idempotent (the runner re-applies every file on every boot): IF NOT EXISTS
-- guards both columns.

ALTER TABLE document_chunks
    ADD COLUMN IF NOT EXISTS start_offset INTEGER;

ALTER TABLE document_chunks
    ADD COLUMN IF NOT EXISTS end_offset INTEGER;
