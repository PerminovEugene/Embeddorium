# Shared ingestion entry point: validates a source (web URL or local file)
# before a CrawlTarget is created. Both the web chain and the local-file chain
# start here; the actor picks a validation strategy per source type.
VALIDATE_SOURCE_QUEUE = "ingest.crawl.source.validate.v1"
VALIDATE_SOURCE_ACTOR = "validate_source"

# Shared ingestion pipeline (one actor / queue / worker per stage). The
# fetch_source actor serves both chains: a web target is fetched over HTTP and
# routed to parse_source; a local-file target is read from disk and routed to
# filter_documents (which re-joins the chain at parse_source).
FETCH_SOURCE_QUEUE = "ingest.crawl.source.fetch.v1"
FETCH_SOURCE_ACTOR = "fetch_source"

PARSE_SOURCE_QUEUE = "ingest.crawl.source.parse.v1"
PARSE_SOURCE_ACTOR = "parse_source"

CHUNK_DOCUMENT_QUEUE = "ingest.crawl.document.chunk.v1"
CHUNK_DOCUMENT_ACTOR = "chunk_document"

SCHEDULE_EMBEDDINGS_QUEUE = "ingest.crawl.embeddings.schedule.v1"
SCHEDULE_EMBEDDINGS_ACTOR = "schedule_embeddings"

SCHEDULE_DISCOVERED_LINKS_QUEUE = "ingest.crawl.links.schedule.v1"
SCHEDULE_DISCOVERED_LINKS_ACTOR = "schedule_discovered_links"

EMBED_CHUNKS_QUEUE = "ingest.embed.chunk.generate.v1"
EMBED_CHUNKS_ACTOR = "embed_chunks"

# Terminal, cross-cutting actor: not a pipeline "stage" of its own, but a
# listener triggered from the tail of both the crawl chain
# (schedule_discovered_links, when a target reaches "processed") and the embed
# chain (embed_chunks, when a batch finishes), so it can detect the moment a
# run has no more work coming and flip it to "completed".
TRACK_PIPELINE_STATUS_QUEUE = "ingest.pipeline.status.track.v1"
TRACK_PIPELINE_STATUS_ACTOR = "track_pipeline_status"

# Local-file-only relevance gate between fetch_source (local strategy) and
# parse_source.
FILTER_DOCUMENTS_QUEUE = "ingest.crawl.file.filter.v1"
FILTER_DOCUMENTS_ACTOR = "filter_documents"
