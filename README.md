# Embeddorium

A Python agent for fetching, parsing, embedding, and querying legislative documents.

## Pipeline flow

Ingestion runs as a chain of single-responsibility Dramatiq actors. Each stage advances the crawl target through its status machine and hands off to the next stage via the transactional outbox (no actor enqueues RabbitMQ directly).

### Web crawl chain

```
UI → POST /pipeline-runs → server creates pipeline_run row + publishes seed → crawl_frontier_manager
        ^                                                                                            |
        |_______________________ discovered links loop back (with pipeline_id) ____________________|
                                                                                                    |
crawl_frontier_manager  ->  fetch_source  ->  parse_source  ->  chunk_document  ->  schedule_embeddings  ->  schedule_discovered_links
                                                                                            |
                                                                                       embed_chunks
```

1. **UI / API** — `POST /pipeline-runs` with a dataset id, provider id, and optional chunking/similarity overrides. The server creates the `pipeline_runs` row (status `pending`), publishes the seed message carrying `pipeline_id`, then advances to `running`.
2. **crawl_frontier_manager** — dedup gate; normalizes the URL, creates a `crawl_target` (`queued`), enqueues fetch with `pipeline_id`. Discovered links loop back here carrying the same `pipeline_id`.
3. **fetch_source** — fetches the URL (TLS verified), classifies failures (transient vs permanent), rejects unsupported content types, stores the raw fetch + provenance. Passes `pipeline_id` forward.
4. **parse_source** — picks a parser by content type, extracts normalized text, saves the `Document` with metadata/hashes. Passes `pipeline_id` forward.
5. **chunk_document** — reads chunk settings from the run's `actor_configs` via `pipeline_id`, splits text into chunks and persists discovered links.
6. **schedule_embeddings** — emits one embed job per chunk batch (with `pipeline_id`), then triggers link scheduling.
7. **schedule_discovered_links** — schedules persisted links back to the frontier (carrying `pipeline_id`), then marks the target `processed`.
8. **embed_chunks** — reads provider/model and collection from the run's snapshots via `pipeline_id`, embeds chunks and upserts vectors into Qdrant (point id = chunk id).

### Local XML file chain

A parallel chain ingests a local dump of XML files instead of crawling links, and optionally filters documents by keyword. It re-joins the web chain at `parse_source`, so everything downstream is shared:

```
UI → POST /pipeline-runs → server creates row + publishes seed(s) → fetch_file_source
                                 (one message per *.xml file)
                                                  |
                            fetch_file_source  ->  filter_documents  ->  parse_source  ->  chunk_document  ->  schedule_embeddings  ->  embed_chunks
                            (read file →           (relevant?           (shared with the web chain from here on)
                             SourceFetch)           yes/no)
                                                       |
                                                       v
                                                skipped (not_relevant)
```

1. **UI / API** — `POST /pipeline-runs` with a local dataset. The server creates the run row and enumerates `*.xml` files from the dataset's `paths`, publishing one `fetch_file_source` message per file carrying `pipeline_id`.
2. **fetch_file_source** — merges "frontier create" + "fetch" for local files: normalizes the path to `file://<abs_path>`, dedups against an already-queued target, reads the file, stores the raw content as a `SourceFetch`. Passes `pipeline_id` forward.
3. **filter_documents** — extracts the document title from the XML and checks it against a configurable keyword list. When no keywords are configured every document passes through. Documents that do not match any keyword are marked `skipped` (`skip_reason="not_relevant"`) and the chain stops there; matching documents advance to `filtered` and re-join the web chain at `parse_source`.
4. **parse_source** onward — unchanged from the web chain (`XmlParser` is picked by content type `application/xml`/`text/xml`); `chunk_document`, `schedule_embeddings`, and `embed_chunks` are reused as-is. `schedule_discovered_links` finds zero links for XML documents, which is expected.

The **`pipeline_runs` row** is created by the server before any seed message is published. Every actor receives `pipeline_id` in its payload and loads its configuration (chunk size/overlap, embedding provider/model, Qdrant collection) from that row. The embeddings-tester UI lists these runs so a DB search reuses exactly a run's collection + embedding model.

The **outbox dispatcher** (`python -m backend.outbox.dispatcher`) publishes committed outbox events to RabbitMQ; delivery is at-least-once and every stage is idempotent.

## Project structure

```
backend/                        # all Python code (importable package `backend`)
    shared/                     # common code reused across actors, server, agent
        config.py               # env-based configuration (single source of truth)
        logging_config.py       # logging setup
        log_routing.py          # per-URL log routing
        parsers/                # HTML→Markdown, link extraction, chunking, XML parsing, keyword filter
        clients/                # HuggingFace, LLM, embed, HTTP, queue clients
        models/                 # Pydantic domain models
        pipeline/               # hashing utilities
        storage/                # SQL store (SQLAlchemy) + Qdrant vector store
        prompts/                # prompt/reference material
    actors/                     # dramatiq pipeline stages (one dir per stage)
    outbox/
        dispatcher.py           # outbox → RabbitMQ publisher
    mcp/
        server.py               # FastMCP server exposing KB tools
    agent/                      # WIP LangGraph agent (graph, nodes, providers, CLI)
    server/                     # FastAPI embeddings-tester API (see below)
        pipeline_routes.py      # POST/GET/DELETE /pipeline-runs
        pipeline_launch.py      # seed helper (publishes entry messages to RabbitMQ)
    tests/                      # pytest suite
ui/                             # React/Vite embeddings-tester UI
infra/                          # broker/db config (rabbitmq/, postgres/, qdrant/)
docs/                           # architecture notes & plans
docker-compose.yml              # full local stack
```

Migrations are applied with `python -m backend.shared.storage.sql.migrate`.

## Setup

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your values:

```sh
cp .env.example .env
```

| Variable                | Required                   | Default                  | Description                                                                                                                                                        |
| ----------------------- | -------------------------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `HG_TOKEN`              | yes                        | —                        | HuggingFace API token                                                                                                                                              |
| `POSTGRES_USER`         | yes                        | —                        | PostgreSQL user                                                                                                                                                    |
| `POSTGRES_PASSWORD`     | yes                        | —                        | PostgreSQL password                                                                                                                                                |
| `POSTGRES_DB`           | yes                        | —                        | PostgreSQL database name                                                                                                                                           |
| `POSTGRES_HOST`         | no                         | `localhost`              | PostgreSQL host                                                                                                                                                    |
| `POSTGRES_PORT`         | no                         | `5432`                   | PostgreSQL port                                                                                                                                                    |
| `QDRANT_URL`            | no                         | `http://localhost:6333`  | Qdrant instance URL                                                                                                                                                |
| `EMBED_PROVIDER`        | no                         | `huggingface`            | `huggingface` (real local model), `ollama` (remote HTTP), or `mock` (random vectors)                                                                               |
| `MOCK_EMBED_DIM`        | no                         | `4096`                   | Vector dimension used by the `mock` provider                                                                                                                       |
| `OLLAMA_EMBED_BASE_URL` | if `EMBED_PROVIDER=ollama` | `http://localhost:11434` | Ollama server URL **for embeddings** — separate from the agent's `OLLAMA_BASE_URL` (see [Embedding provider](#embedding-provider) for the docker-compose hostname) |
| `OLLAMA_EMBED_MODEL`    | if `EMBED_PROVIDER=ollama` | `qwen3-embedding`        | Ollama embedding model name                                                                                                                                        |

### Agent env vars

| Variable          | Required           | Default                     | Description                                                                                |
| ----------------- | ------------------ | --------------------------- | ------------------------------------------------------------------------------------------ |
| `LLM_PROVIDER`    | no                 | `ollama`                    | `ollama` or `openai`                                                                       |
| `MCP_SERVER_URL`  | no                 | `http://localhost:8000/mcp` | FastMCP server endpoint                                                                    |
| `OPENAI_API_KEY`  | if provider=openai | —                           | OpenAI API key                                                                             |
| `OPENAI_MODEL`    | no                 | `gpt-4o-mini`               | OpenAI model name                                                                          |
| `OLLAMA_BASE_URL` | no                 | `http://localhost:11434`    | Ollama server URL **for the chat LLM** — separate from embeddings' `OLLAMA_EMBED_BASE_URL` |
| `OLLAMA_MODEL`    | no                 | `llama3.2`                  | Ollama chat model name                                                                     |

## Run

Apply migrations first, then bring up the pipeline:

```sh
python -m backend.shared.storage.sql.migrate
docker compose up -d --build
```

### Starting a pipeline run

Pipeline runs are created via the API — no separate seed scripts are needed. Use `POST /pipeline-runs` with the id of a Dataset and an embedding Provider you have already created via the `/datasets` and `/providers` endpoints:

```sh
curl -s -X POST http://localhost:8000/pipeline-runs \
  -H 'Content-Type: application/json' \
  -d '{"datasetId": "<dataset-uuid>", "providerId": "<provider-uuid>"}'
```

Optional `actorConfigs` overrides let you customize chunk size, chunk overlap, and Qdrant similarity metric:

```json
{
  "datasetId": "<dataset-uuid>",
  "providerId": "<provider-uuid>",
  "actorConfigs": {
    "chunkSize": 1200,
    "chunkOverlap": 150,
    "similarity": "cosine"
  }
}
```

The server:

1. Loads the Dataset and Provider from Postgres (404 if either is missing).
2. Validates that the provider has `model_type == "embedding"`.
3. Creates the `pipeline_runs` row (status `pending`) with full snapshots of both objects.
4. Publishes the seed message(s) to RabbitMQ carrying `pipeline_id`.
5. Advances the run to `running`.

Every actor along the pipeline chain receives `pipeline_id` and reads its configuration (chunk settings, embedding provider/model, Qdrant collection) from the saved row — never from global env config.

Make sure the pipeline workers and the outbox dispatcher are up. The server also needs the following env vars (in addition to the standard Postgres/Qdrant vars):

| Variable            | Required | Default     | Description       |
| ------------------- | -------- | ----------- | ----------------- |
| `RABBITMQ_USER`     | yes      | —           | RabbitMQ username |
| `RABBITMQ_PASSWORD` | yes      | —           | RabbitMQ password |
| `RABBITMQ_HOST`     | no       | `localhost` | RabbitMQ host     |
| `RABBITMQ_PORT`     | no       | `5672`      | RabbitMQ port     |
| `RABBITMQ_VHOST`    | no       | `/`         | RabbitMQ vhost    |

### Run the LangGraph agent

The agent connects to the MCP server and answers questions using the knowledge base.

Start the MCP server first:

```sh
python -m backend.mcp.server
```

Then send a prompt (defaults to Ollama):

```sh
python -m backend.agent.generate "What are the VAT rules in Estonia?"

# or explicitly choose a provider
python -m backend.agent.generate "What are the VAT rules?" ollama
python -m backend.agent.generate "What are the VAT rules?" openai

# or via the installed script
laws-generate "What are the VAT rules in Estonia?"
```

The provider can also be set via `LLM_PROVIDER` in `.env` instead of passing it as an argument.

### Embedding provider

The embed stage (`worker-embed-chunks`) runs in Docker like every other stage. The provider is selected by `EMBED_PROVIDER` in `.env.docker`:

- **`mock`** (the compose default) — returns random vectors of `MOCK_EMBED_DIM` dimensions. Imports neither `torch` nor `sentence-transformers` and loads no model, so embedding completes near-instantly and the container image stays light (`qdrant-client` only). Use this to exercise the **entire pipeline end to end quickly**. Mock vectors are random, so retrieval results are meaningless — this verifies the flow, not query quality.

  ```sh
  EMBED_PROVIDER=mock
  # optional — defaults to 4096 (the real model's dimension)
  MOCK_EMBED_DIM=4096
  ```

- **`ollama`** — calls a remote Ollama server over HTTP using `OllamaEmbeddings` (from `langchain-ollama`), so the worker container stays light (no `torch`/`sentence-transformers`; `langchain-ollama`/`ollama` are thin `httpx`-based clients, already in the `embed` extra). Default model is `qwen3-embedding`.

  ```sh
  EMBED_PROVIDER=ollama
  OLLAMA_EMBED_MODEL=qwen3-embedding
  # see "Pointing at Ollama" below for the correct value
  OLLAMA_EMBED_BASE_URL=http://host.docker.internal:11434
  ```

  > **Note:** embeddings use their own `OLLAMA_EMBED_BASE_URL`, deliberately separate from the chat agent's `OLLAMA_BASE_URL` (`backend/agent/config.py`). The embed worker runs in docker (so it needs `host.docker.internal`/the compose service name), while the agent runs on the host (so `localhost`), and they can point at different Ollama servers and models entirely.

  Pull the model once, on whichever host runs Ollama:

  ```sh
  ollama pull qwen3-embedding
  ```

  #### Pointing at Ollama from inside a container

  `OLLAMA_EMBED_BASE_URL` must be reachable from inside the `worker-embed-chunks` container — `http://localhost:11434` does **not** work there, since each container has its own loopback interface, separate from the host's:
  - **Ollama as a compose service** — this repo's `docker-compose.yml` defines an optional `ollama` service (`image: ollama/ollama`, profile `ollama`, not started by a plain `docker compose up -d`). Start it explicitly and use the **service name** as the hostname:

    ```sh
    docker compose --profile ollama up -d ollama
    docker compose exec ollama ollama pull qwen3-embedding
    ```

    ```sh
    # .env.docker
    OLLAMA_EMBED_BASE_URL=http://ollama:11434
    ```

  - **Ollama running on the host** (e.g. natively on a Mac, to use Metal acceleration) — pull the model on the host, then point containers at the host's special DNS name (Docker Desktop on Mac/Windows):

    ```sh
    ollama pull qwen3-embedding   # run on the host, not in a container
    ```

    ```sh
    # .env.docker
    OLLAMA_EMBED_BASE_URL=http://host.docker.internal:11434
    ```

    (On Linux without Docker Desktop, use the host's Docker-bridge IP, e.g. `http://172.17.0.1:11434`, or add `extra_hosts: ["host.docker.internal:host-gateway"]` to the service.)

Bring the stack up and seed as usual; the embed worker drains the queue automatically:

```sh
docker compose up -d --build
scripts/seed.sh config.json
```

#### Real local model (optional)

Embedding with the real `Qwen/Qwen3-Embedding-8B` model is heavy (multi-GB `torch`/`sentence-transformers` install + slow inference) and isn't installed in the compose image. To use it, install the `embedding` extra (`pip install -e ".[embedding]"`), leave `EMBED_PROVIDER` unset (or set it to `huggingface`) in `.env`, and run the actor locally:

```sh
dramatiq backend.actors.embed_chunks_actor --processes 1 --threads 1
```

## Embeddings tester (UI + API)

A small web tool for **eyeballing how an embedding model scores text against
text**: enter source and candidate texts, pick one or more Ollama models and
similarity metrics, and get a ranked table of every source/candidate pair.

- `backend/server/` — FastAPI API (`/compare`). Reuses `backend`'s `VectorStore`,
  `OllamaEmbedClient`, and `config`, so it embeds and stores vectors exactly
  like the ingestion pipeline. Built from `Dockerfile.dev` with the `server`
  extra.
- `ui/` — React + Vite front end.

```sh
docker compose up -d --build qdrant server ui
```

- UI: http://localhost:5173
- API: http://localhost:8000 (docs at `/docs`)

Embeddings come from an **Ollama** server (port chosen per request in the UI;
host via `OLLAMA_HOST`, default `host.docker.internal`). Pull a model first, e.g.
`ollama pull nomic-embed-text`. See [`server/README.md`](server/README.md) for
standalone (non-Docker) usage.

## Dependency management

```sh
# Add a package
pip install <package>
pip freeze > requirements.txt

# Remove a package
pip uninstall <package>
pip freeze > requirements.txt
```

---

## Code style & best practices

This project follows [PEP 8](https://peps.python.org/pep-0008/) and standard Python conventions.

### Formatting & linting

Use [Ruff](https://docs.astral.sh/ruff/) as a single tool for both linting and formatting:

```sh
pip install ruff
ruff check .          # lint
ruff format .         # format (replaces Black)
```

### PEP 8 compliance check

```sh
pip install pycodestyle
pycodestyle .
```

## Testing

```sh
.venv/bin/python3 -m pytest tests/ -v
```

Run a specific test file:

```sh
.venv/bin/python3 -m pytest tests/runners/test_add_web_source_job.py -v
```

## Local dev

1. for management qdarnt - http://0.0.0.0:6333/dashboard
2. for management psql - install `https://dbeaver.io`
3. for management rabbitmq http://localhost:15672/

##

## Sources

Local legal-act XML dumps (e.g. the Estonian `xml.2026.en/` export) live in the gitignored `sources/` folder at the repo root.

The folder is bind-mounted into two containers via `docker-compose.yml`:

| Service                    | Host path   | Container path |
| -------------------------- | ----------- | -------------- |
| `worker-fetch-file-source` | `./sources` | `/app/sources` |
| `server`                   | `./sources` | `/app/sources` |

`worker-fetch-file-source` reads individual `.xml` files and stores their content in the DB. The `server` (`pipeline_launch.py::_seed_local`) enumerates `*.xml` files from the dataset's configured paths before publishing seed messages.

Downstream actors (`filter_documents`, `parse_source`, etc.) read content from the DB, not from disk, so they do not need this mount.
