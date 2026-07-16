# Ingestion pipelines

An ingestion pipeline is a persisted run configuration plus its execution
state. The backend entity is `PipelineRun`; the UI presents creation and launch
on **Pipelines** and execution details on **Indexing Runs**.

## Run snapshot

The saved `actor_configs` object contains:

| Block | Purpose |
| --- | --- |
| `validate_source` | URL normalization and per-run dedup |
| `fetch_source` | TLS verification, read timeout, MIME allowlist |
| `filter_documents` | Gate toggle and include/exclude keywords |
| `parse_source` | Parser override or content-type auto selection |
| `chunk_document` | Chunker name and plugin-specific settings |
| `schedule_embeddings` | Number of chunks per embed job |
| `schedule_discovered_links` | Child-link and currently unenforced scope knobs |
| `embed_chunks` | Full embedding provider snapshot |
| `vector_store` | Derived collection name and similarity metric |

The default chunker is `text_markdown`. The model default for embedding job
size is `32`; the current UI initializes its field to `64`, and the submitted
value is stored in the run.

## Execution

One web seed or many local XML seeds enter `validate_source`. Actors claim a
target through compare-and-set status updates, persist outputs, and normally
write the next message to the transactional outbox. The dispatcher publishes
committed events to RabbitMQ.

Embedding batches and link scheduling fan out after chunking. A target reaches
`processed` only when its link scheduling is durable and every chunk is marked
`embedded`. The run status tracker rechecks both target activity and embedding
batch counters before completing the run.

See [Ingestion flow](../architecture/ingestion-flow.md) for the stage-by-stage
path.
