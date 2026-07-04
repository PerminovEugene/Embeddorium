<div align="center">

<img src="docs/assets/embeddorium-logo.png" alt="Embeddorium" width="170">

# Embeddorium

**A local-first RAG playground.** Crawl or import sources, chunk and embed them
with a provider you choose, store the vectors in Qdrant, and inspect the results
— all on your own machine.

![Python](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)
![Dramatiq](https://img.shields.io/badge/pipeline-Dramatiq-orange)
![Qdrant](https://img.shields.io/badge/vectors-Qdrant-DC244C)
![License](https://img.shields.io/badge/license-Apache%202.0-blue)

</div>

---

Embeddorium is a workshop for retrieval pipelines you can actually see into. It
runs the full ingest → chunk → embed → store → query loop as a set of small,
independent workers on your laptop, so you can swap embedding models, tweak
chunking, and watch exactly what each stage produced — without shipping your
data anywhere.

It ships with two ingestion front-ends out of the box (a web crawler and a local
XML importer) and a browser UI for eyeballing how an embedding model scores one
piece of text against another.

## Why

Most RAG demos are a single script and a black box. When retrieval is bad, you
can't tell whether the culprit was the fetch, the parse, the chunker, or the
embedding model. Embeddorium breaks the pipeline into stages that each leave a
durable, inspectable trace:

- **Swap embedders freely** — a `mock` provider for instant end-to-end runs,
  remote **Ollama** over HTTP.
- **Pluggable chunking** — drop a chunker plugin into `backend/plugins/chunkers/`
  and it's auto-discovered, selectable per run, no core code to touch. See
  [docs/plugins.md](docs/plugins.md).
- **See every artifact** — raw fetched bytes and parsed text land as real files
  under `tmp/pipeline_run/<id>/`, next to per-URL logs. The database stores paths
  and metadata, not giant blobs.
- **Reproducible runs** — every run snapshots its dataset and provider, so its
  settings and its Qdrant collection stay pinned to that run.
- **Restartable by design** — a transactional outbox means a message exists only
  if its data was committed; every stage is idempotent, so retries are safe.
- **Local and self-hosted** — Postgres, Qdrant, and RabbitMQ come up with one
  `docker compose` command.

## How it works

Ingestion is a chain of single-purpose [Dramatiq](https://dramatiq.io/) actors.
Each one does its job, writes its result plus the next message in one database
transaction, and an outbox dispatcher publishes that message to RabbitMQ.

```
POST /pipeline-runs
      │
      ▼
crawl_frontier_manager ─► fetch_source ─► parse_source ─► chunk_document ─► schedule_embeddings ─► embed_chunks ─► Qdrant
                                              ▲                                                          │
   fetch_file_source ─► filter_documents ─────┘                                          track_pipeline_status
```

Once every embedding batch a run scheduled has finished (and no crawl target
can schedule any more), `track_pipeline_status` flips the run to `completed`
and stamps `finished_at` automatically — no polling required.

The full walk-through — both chains, the outbox, the status machine, and where
data lives — is in **[docs/architecture.md](docs/architecture.md)**.

## Quick start

You'll need Docker and Python 3.11+.

```sh
# 1. Configure
cp .env.example .env        # fill in Postgres / RabbitMQ / Qdrant values

# 2. Migrate the database
python -m backend.shared.storage.sql.migrate

# 3. Bring up the whole stack
docker compose up -d --build
```

That starts Postgres, Qdrant, RabbitMQ, every pipeline worker, the API, and the
UI. The default embedding provider is `mock`, so you can watch a run flow end to
end in seconds before wiring up a real model.

Then create a dataset and a provider, and launch a run — see
**[docs/usage.md](docs/usage.md)**.

- UI — http://localhost:5173
- API + docs — http://localhost:8000/docs
- Qdrant dashboard — http://localhost:6333/dashboard
- RabbitMQ — http://localhost:15672

## Project layout

```
backend/
  shared/        # config, models, parsers, clients, storage (SQLAlchemy + Qdrant)
  actors/        # one directory per pipeline stage
  plugins/       # auto-discovered plugins (chunkers/ today — see docs/plugins.md)
  outbox/        # outbox → RabbitMQ dispatcher
  server/        # FastAPI API + embeddings tester backend
  mcp/           # FastMCP server exposing knowledge-base tools
  agent/         # optional LangGraph chat agent
  tests/         # pytest suite
ui/              # React + Vite front end
infra/           # broker / db / vector config
docs/            # architecture, configuration, usage, development
docker-compose.yml
```

## Documentation

| Guide                                  | Contents                                                              |
| -------------------------------------- | --------------------------------------------------------------------- |
| [Architecture](docs/architecture.md)   | The pipeline stages, outbox, status machine, and storage model        |
| [Configuration](docs/configuration.md) | Every environment variable, for host and Docker                       |
| [Embeddings](docs/embeddings.md)       | The `mock` / `ollama` / `huggingface` providers and Ollama networking |
| [Usage](docs/usage.md)                 | Starting runs, local XML sources, the agent, the embeddings tester    |
| [Plugins](docs/plugins.md)             | Writing your own chunker plugin, auto-discovery, the built-ins        |
| [Development](docs/development.md)     | Setup, tests, linting, migrations, resetting local state              |

## Contributing

Issues and pull requests are welcome. Before opening a PR, run the tests and
Ruff:

```sh
.venv/bin/python -m pytest backend/tests -q
ruff check . && ruff format --check .
```

## License

Licensed under the Apache License 2.0 — see [LICENSE.md](LICENSE.md).

## 🚀 Setup Instructions

1. Launch Ollama and pull the embedding models you want to use.
2. Install Docker and Docker Compose if you haven't already.
3. Clone the repository and start the server:

```sh
docker-compose up -d
```

4. Open your browser and navigate to:

```text
http://localhost:5173/
```

That's it — you're ready to experiment!
