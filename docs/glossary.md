# Glossary

**Actor**  
A Dramatiq worker function responsible for one ingestion stage. Each actor has
its own queue and container.

**Actor configuration**  
The per-stage settings saved in `pipeline_runs.actor_configs`. Plugin-backed
settings are described by `GET /actor-configs`.

**Chunk**  
A persisted segment of a document. PostgreSQL stores its text, position,
metadata, offsets, and embedding status; Qdrant stores its vector under the
same chunk UUID.

**Crawl target**  
The per-source work record and status machine for one URL or local file in one
pipeline run.

**Dataset**  
A named source definition: either one web seed URL or a list of local paths.
Crawl behavior is configured on a run, not on the dataset.

**Document**  
The normalized result of parsing a source fetch, including hashes, provenance,
parser metadata, and the path to parsed text.

**Hybrid search**  
Run-scoped semantic and BM25 retrieval whose ranked chunk IDs are combined with
Reciprocal Rank Fusion (RRF).

**Outbox**  
The `outbox_events` table and dispatcher used to commit downstream messages
with domain changes before publishing them to RabbitMQ.

**Pipeline run**  
An immutable snapshot of a dataset and actor settings, including the selected
embedding provider. The UI labels this object a pipeline on the Pipelines page
and exposes its execution details on the Indexing Runs page.

**Provider**  
A saved model backend configuration. `provider_type` selects a runtime adapter;
`model_type` identifies a capability such as `embedding` or `cross-encoder`.

**Reranker**  
An optional cross-encoder HTTP model that re-scores the fused results of hybrid
search and keeps a requested number of results.

**Search Lab**  
The UI page that compares persisted search results by chunk, document, or rank.

**Semantic search**  
Dense-vector retrieval in Qdrant. The query uses the embedding provider
snapshot from the selected pipeline run.

**Source fetch**  
Provenance for retrieved raw content: final URL, status, MIME type, hashes,
redirects, and the on-disk raw artifact path.
