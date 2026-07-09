# Postgres infra

The `postgres` service in `docker-compose.yml` builds `infra/postgres/Dockerfile`
instead of running the stock `postgres:17` image, in order to get the
[`pg_textsearch`](https://www.pedroalonso.net/blog/postgres-bm25-search/)
extension, which provides BM25 full-text search (a `bm25` index access method
plus the `<@>` operator). This backs the `document_chunks.text` BM25 index
created in migration `025_add_chunk_bm25_search.sql` and queried by
`ChunkRepository.search_bm25` (`backend/shared/storage/sql/repositories/chunk_repo.py`).

## Why the base image changed (16 -> 17)

`pg_textsearch` requires Postgres 17 or 18; it is not available/compatible
with Postgres 16. `infra/postgres/Dockerfile` builds `FROM postgres:17` and
installs the extension.

There is no apt package for `pg_textsearch`, so the Dockerfile builds it from
source (it is a plain-C pgxs extension — no Rust/pgrx, no submodules) against
the `postgresql-server-dev-17` headers, pinned to tag `v1.3.1` via the
`PG_TEXTSEARCH_REF` build arg. The build toolchain is purged in the same layer
so the published image keeps only the runtime plus the compiled extension.
Override the version with `--build-arg PG_TEXTSEARCH_REF=...` (it must support
the Postgres major version of the base image).

## `shared_preload_libraries` requirement

`pg_textsearch` must be preloaded at server start — `CREATE EXTENSION
pg_textsearch` fails with "library not loaded" otherwise, and this cannot be
fixed after the fact without restarting the server with the preload in place.
Rather than maintaining a `postgresql.conf` file here, the `postgres` service
sets this directly via a `command:` override:

```yaml
command: postgres -c shared_preload_libraries=pg_textsearch
```

If this service ever needs other custom Postgres settings, prefer adding a
real `postgresql.conf` in this directory and mounting it instead of growing
a long list of `-c` flags.

## Major-version upgrade / existing `postgres_data` volume

**This is an operator action, not something automated by this change.**
Postgres does not support starting a newer major version's server binary
against an older major version's on-disk data directory. Any environment
with a pre-existing `postgres_data` volume (initialized under Postgres 16)
will fail to start the new Postgres 17 container until the data is migrated,
via one of:

- `pg_dump` / `pg_restore` (or `pg_dumpall`) the old 16 volume's data into a
  fresh volume under the new 17 container, or
- `pg_upgrade` between the old and new data directories.

A brand-new environment with no prior `postgres_data` volume is unaffected —
it simply initializes fresh under Postgres 17.

## How BM25 search is wired

1. `docker-compose.yml`'s `postgres` service builds this Dockerfile and sets
   `shared_preload_libraries=pg_textsearch` (above).
2. Migration `025_add_chunk_bm25_search.sql` runs
   `CREATE EXTENSION IF NOT EXISTS pg_textsearch;` and creates a `bm25` index
   on `document_chunks.text`. Both are idempotent (`IF NOT EXISTS`), since
   `run_migrations()` re-applies every migration file on every boot.
3. `ChunkRepository.search_bm25(query, limit)` queries with the `<@>`
   operator and returns `(DocumentChunk, score)` pairs ordered best match
   first. Note `<@>` returns a *negated* BM25 score, so lower/more negative
   is better — the repository method's docstring covers this in detail.
