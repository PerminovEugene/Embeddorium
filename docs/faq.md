# Frequently asked questions

## Do I need an embedding model for the first run?

No. Create a `mock` embedding provider. It produces random vectors and is useful
for validating ingestion, but its search results have no semantic meaning.

## Why are pipeline creation and launch separate?

`POST /pipeline-runs` saves a `pending` run and its configuration snapshot.
`POST /pipeline-runs/{id}/launch` publishes seed messages and changes it to
`running`. The split also permits relaunching completed or failed runs.

## Can I ingest arbitrary local files?

No. The source browser and seeder currently list and recurse over `*.xml` only.
The built-in parsers accept HTML, XHTML, plain text, and XML for web responses,
but local ingestion is XML-specific.

## Does web crawling honor depth and cross-domain settings?

`follow_child_links` is enforced. `max_depth` and `follow_cross_domain` are
stored in the run but are not enforced. Discovered web links are currently
restricted to the parent document's origin by `validate_source`.

## Which searches are implemented?

`semantic`, `keyword`, and `hybrid`. Keyword search uses PostgreSQL BM25;
hybrid search combines semantic and keyword rankings with RRF. Cross-encoder
reranking is available only for hybrid search.

## Why does Ollama fail at `localhost`?

The embedding worker runs inside Docker, where `localhost` is the worker
container. For Ollama on a Docker Desktop host, configure the saved provider
with `http://host.docker.internal` and port `11434`.

## Are searches and runs scoped to a dataset?

Search is scoped to a pipeline run. Dense results are filtered by the
`pipeline_run_id` Qdrant payload; BM25 joins chunks to crawl targets for the same
run. A run contains a dataset snapshot.

## Is the MCP server ready to use?

No. `backend/mcp/server.py` contains an incomplete `search_knowledge_base`
implementation and cannot currently be imported. The agent depends on that
tool, so the documented supported path is the web UI or REST API.

## Where are raw and parsed files?

With Compose they are bind-mounted under `tmp/pipeline_run/`. Run folders may
be named `<run-id>__<run-name>`; each source has `raw/` and `parsed/` children.

## What should I check when the stack does not start?

```sh
docker compose ps
docker compose logs migrate
docker compose logs postgres
docker compose logs rabbitmq
```

Workers depend on a healthy RabbitMQ and a successful migration job. Missing
`.env` credentials and occupied host ports are common local startup failures.

## What should I check when a run stays `running`?

Confirm all actor services and `worker-outbox-dispatcher` are running, then
inspect the stage logs:

```sh
docker compose logs worker-outbox-dispatcher
docker compose logs worker-embed-chunks
docker compose logs worker-track-pipeline-status
```

Use `GET /pipeline-runs/{id}/targets` or Indexing Runs to find the target still
in an active state. A `failed_*` or `skipped*` target is terminal and does not by
itself prevent the run from completing.

## How do I reset all local state?

`scripts/full-clean.sh` purges RabbitMQ messages, deletes every Qdrant
collection, resets PostgreSQL, clears logs, and rebuilds the workers. It is
destructive to local data. `docker compose down -v` removes the named Compose
volumes instead.
