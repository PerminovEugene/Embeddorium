# Postgres image with the pg_textsearch extension (BM25 full-text search),
# used for the document_chunks.text index created in migration
# 025_add_chunk_bm25_search.sql.
#
# pg_textsearch (https://github.com/timescale/pg_textsearch) is a plain C
# PostgreSQL extension (pgxs Makefile — no Rust/pgrx, no submodules) that
# supports Postgres 17 and 18 only. There is no apt package, so it is built
# from source against the matching server dev headers and installed into the
# image's PostgreSQL extension directories.
#
# It provides the `bm25` index access method and the `<@>` scoring operator
# (see ChunkRepository.search_bm25). Remember the two runtime prerequisites
# that live outside this file:
#   * `shared_preload_libraries = 'pg_textsearch'` before the server starts
#     (set via `command:` in docker-compose.yml).
#   * `CREATE EXTENSION pg_textsearch;` once per database (migration 025).

FROM postgres:17

# Pin the extension to a released tag for reproducible builds. Override with
# `--build-arg PG_TEXTSEARCH_REF=...` if you need a different version; it must
# support the Postgres major version of the FROM image above.
ARG PG_TEXTSEARCH_REF=v1.3.1

# Build from source, then purge the build toolchain in the same layer so the
# published image keeps only the runtime + the compiled extension (.so, .control
# and SQL files land in the base image's PostgreSQL extension dirs).
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        ca-certificates \
        postgresql-server-dev-17; \
    git clone --depth 1 --branch "${PG_TEXTSEARCH_REF}" \
        https://github.com/timescale/pg_textsearch.git /tmp/pg_textsearch; \
    make -C /tmp/pg_textsearch; \
    make -C /tmp/pg_textsearch install; \
    rm -rf /tmp/pg_textsearch; \
    apt-get purge -y --auto-remove \
        build-essential \
        git \
        postgresql-server-dev-17; \
    rm -rf /var/lib/apt/lists/*
