CRAWL_FRONTIER_MANAGER_QUEUE = "laws.crawl.frontier.manage.v1"
CRAWL_FRONTIER_MANAGER_ACTOR = "manage_crawl_frontier"

# Web-source ingestion pipeline (one actor / queue / worker per stage).
FETCH_SOURCE_QUEUE = "laws.crawl.source.fetch.v1"
FETCH_SOURCE_ACTOR = "fetch_source"

PARSE_SOURCE_QUEUE = "laws.crawl.source.parse.v1"
PARSE_SOURCE_ACTOR = "parse_source"

CHUNK_DOCUMENT_QUEUE = "laws.crawl.document.chunk.v1"
CHUNK_DOCUMENT_ACTOR = "chunk_document"

SCHEDULE_EMBEDDINGS_QUEUE = "laws.crawl.embeddings.schedule.v1"
SCHEDULE_EMBEDDINGS_ACTOR = "schedule_embeddings"

SCHEDULE_DISCOVERED_LINKS_QUEUE = "laws.crawl.links.schedule.v1"
SCHEDULE_DISCOVERED_LINKS_ACTOR = "schedule_discovered_links"

EMBED_CHUNKS_QUEUE = "laws.embed.chunk.generate.v1"
EMBED_CHUNKS_ACTOR = "embed_chunks"

# Local-file (XML) ingestion pipeline. Re-joins the web chain at
# parse_source: fetch_file_source -> filter_tax_acts -> parse_source -> ...
FETCH_FILE_SOURCE_QUEUE = "laws.crawl.file.fetch.v1"
FETCH_FILE_SOURCE_ACTOR = "fetch_file_source"

FILTER_TAX_ACTS_QUEUE = "laws.crawl.file.filter.v1"
FILTER_TAX_ACTS_ACTOR = "filter_tax_acts"
