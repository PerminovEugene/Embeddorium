# Postgres image with the pg_textsearch extension (BM25 full-text search),
# used for the document_chunks.text index created in migration
# 025_add_chunk_bm25_search.sql.
#
# ---------------------------------------------------------------------------
# UNVERIFIED INSTALL METHOD — no web access was available while writing this
# Dockerfile, so the install steps below could not be checked against the
# real pg_textsearch packaging/release artifacts. Before relying on this in
# any environment, confirm against the authoritative sources:
#   * https://www.pedroalonso.net/blog/postgres-bm25-search/
#   * the pg_textsearch project itself (TigerData/Timescale) — check its repo
#     for the current release process, supported Postgres major versions
#     (this Dockerfile assumes 17; 18 is the other option called out in the
#     article), and whether it ships as a `.deb`/apt repo, a prebuilt
#     `.so` release archive, or requires building from source with
#     `pgxs`/`cargo pgrx` (pg_textsearch, like pgvectorscale, may be a
#     Rust/pgrx extension rather than a plain C extension).
# ---------------------------------------------------------------------------

FROM postgres:17

# TODO(verify): the package name, repository/channel, and install mechanism
# below are best-effort placeholders, not confirmed working steps. Replace
# this block with whatever TigerData's own install instructions specify
# (this may be `apt-get install postgresql-17-pg-textsearch` from a
# TigerData apt repo, a `cargo pgrx package` build, or a release tarball
# copied into the Postgres extension directories — pick whichever the
# upstream project documents once verified).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
    # TODO(verify): replace with the real pg_textsearch package/install step.
    && echo "TODO(verify): install pg_textsearch for PG17 here" \
    && rm -rf /var/lib/apt/lists/*
