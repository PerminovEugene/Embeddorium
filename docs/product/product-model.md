# Product model

Embeddorium's UI labels and backend entities do not always use the same name.
The Pipelines page manages `pipeline_runs`; there is no separate persisted
"ingestion pipeline template" entity.

| Product object | Persisted representation | Purpose |
| --- | --- | --- |
| Dataset | `datasets` | Named web seed or local paths |
| Provider | `providers` | Model runtime, capability, and validated config |
| Pipeline | `pipeline_runs` | Dataset and actor-config snapshot plus lifecycle |
| Source work item | `crawl_targets` | Per-run URL/file status and lineage |
| Fetch | `source_fetches` | Retrieval provenance and raw artifact path |
| Document | `documents` | Parsed provenance, structured output, text path |
| Chunk | `document_chunks` | Searchable text, metadata, offsets, embed status |
| Discovered link | `discovered_links` | Link lineage and scheduling state |
| Search input | `search_inputs` | Persisted query text |
| Search | `searches` | Run, strategy config, and ordered result JSON |

## Lifecycle

A run is created as `pending`, launched as `running`, then completed by the
status tracker when no active crawl target or embedding batch remains. An
operator can also set `failed`; completed and failed runs can be relaunched.

The dataset and selected embedding provider are copied into the run. Updating
or deleting the original dataset/provider does not rewrite the stored snapshot.

## Search identity

A search selects a pipeline run rather than a raw Qdrant collection. This gives
the server the exact embedding provider snapshot and collection recorded by
ingestion and provides the run ID used to scope both dense and BM25 results.
