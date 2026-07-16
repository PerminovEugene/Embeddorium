# Plugins

Plugins isolate behavior that varies from actor and orchestration plumbing.
Registries discover concrete subclasses under `backend/plugins` with
`pkgutil.walk_packages`, import them, and cache the resulting name-to-class map
for the process lifetime.

## Plugin-backed actors

| Actor | Built-in strategies |
| --- | --- |
| `validate_source` | `web`, `local` |
| `fetch_source` | `web`, `local` |
| `filter_documents` | `keyword` |
| `parse_source` | `content_type` plus format parsers `html`, `xml`, `plain` |
| `chunk_document` | `legal_xml`, `text_fixed`, `text_markdown`, `text_recursive`, `text_section`, `text_sentence`, `text_sliding_window` |
| `embed_chunks` | `standard` |

Provider types use the same discovery and field-metadata ideas under
`backend/plugins/provider_types`, with one connection adapter and one or more
model-type capability handlers.

## Metadata contract

Each strategy declares a stable name, label, description, and `FieldSpec`
list. The API publishes this metadata through `GET /actor-configs` and
`GET /providers/configs`; the UI builds controls from it.

Structured parsers may return text, custom metadata, an intermediate JSON
artifact, and an output format. Chunkers receive that information in
`ChunkInput`. Custom metadata cannot replace the reserved keys `chunk_id`,
`document_id`, `dataset_id`, `pipeline_run_id`, or `embedding_model`.

Configured JSON size limits are enforced by rejection, not truncation:

- Parser metadata: 256 KiB by default
- Parser intermediate data: 8 MiB by default
- Chunk metadata: 256 KiB by default

Discovery is cached, so adding or changing a plugin requires restarting the
server and relevant workers.
