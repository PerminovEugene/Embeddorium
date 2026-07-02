CRAWL_FRONTIER_MANAGER_QUEUE = "ingest.crawl.frontier.manage.v1"
CRAWL_FRONTIER_MANAGER_ACTOR = "manage_crawl_frontier"

# Web-source ingestion pipeline (one actor / queue / worker per stage).
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

# Local-file (XML) ingestion pipeline. Re-joins the web chain at
# parse_source: fetch_file_source -> filter_documents -> parse_source -> ...
FETCH_FILE_SOURCE_QUEUE = "ingest.crawl.file.fetch.v1"
FETCH_FILE_SOURCE_ACTOR = "fetch_file_source"

FILTER_DOCUMENTS_QUEUE = "ingest.crawl.file.filter.v1"
FILTER_DOCUMENTS_ACTOR = "filter_documents"
