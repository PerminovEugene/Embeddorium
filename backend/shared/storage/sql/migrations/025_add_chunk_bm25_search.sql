-- BM25 full-text search over document_chunks.text via the pg_textsearch
-- extension (TigerData/Timescale), following the approach in
-- https://www.pedroalonso.net/blog/postgres-bm25-search/
--
-- pg_textsearch ships a custom index access method ("bm25") plus the `<@>`
-- operator, which returns a *negated* BM25 score (lower/more negative = a
-- better match) so a plain ascending ORDER BY on the operator drives an
-- efficient index scan instead of a full sort. See
-- ChunkRepository.search_bm25 for the query side.
--
-- Prerequisites that live outside this file (see infra/postgres/):
--   * Postgres 17 or 18 — pg_textsearch is not available/compatible with the
--     Postgres 16 image this repo used to run.
--   * `shared_preload_libraries = 'pg_textsearch'` must be set on the server
--     *before* Postgres starts. This is the #1 gotcha: without the preload,
--     `CREATE EXTENSION pg_textsearch` fails with "library not loaded", and
--     merely running this migration will not fix a server started without it.
--
-- Idempotency (required: run_migrations() re-executes every *.sql file in
-- migrations/ inside one transaction on every boot):
--   * `CREATE EXTENSION IF NOT EXISTS` is a no-op once the extension exists.
--   * `CREATE INDEX IF NOT EXISTS` is a no-op once the index exists.
-- Both statements run in the same transaction as every other migration file
-- (run_migrations() wraps the whole file glob in a single engine.begin()).
-- CREATE EXTENSION does not require a separate commit before the index can be
-- built against it in Postgres, so no special-casing is needed here.

CREATE EXTENSION IF NOT EXISTS pg_textsearch;

CREATE INDEX IF NOT EXISTS document_chunks_text_bm25_idx
    ON document_chunks USING bm25 (text) WITH (text_config = 'english');
