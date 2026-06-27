# Laws Agent

A Python agent for fetching, parsing, embedding, and querying legislative documents.

## Pipeline flow

Ingestion runs as a chain of single-responsibility Dramatiq actors. Each stage advances the crawl target through its status machine and hands off to the next stage via the transactional outbox (no actor enqueues RabbitMQ directly).

### Web crawl chain

```
crawl_frontier_manager  ->  fetch_source  ->  parse_source  ->  chunk_document  ->  schedule_embeddings  ->  schedule_discovered_links
        ^                                                                                                          |
        |__________________________________ discovered links loop back __________________________________________|
                                                                                                                     |
                                                                                                              embed_chunks
```

1. **crawl_frontier_manager** — dedup gate; normalizes the URL, creates a `crawl_target` (`queued`), enqueues fetch. Discovered links loop back here.
2. **fetch_source** — fetches the URL (TLS verified), classifies failures (transient vs permanent), rejects unsupported content types, stores the raw fetch + provenance.
3. **parse_source** — picks a parser by content type, extracts normalized text, saves the `Document` with metadata/hashes.
4. **chunk_document** — splits text into chunks and persists discovered links.
5. **schedule_embeddings** — emits one embed job per chunk batch, then triggers link scheduling.
6. **schedule_discovered_links** — schedules persisted links back to the frontier, then marks the target `processed`.
7. **embed_chunks** — embeds chunks and upserts vectors into Qdrant (point id = chunk id).

### Local XML file chain

A parallel chain ingests a local dump of legal-act XML files (e.g. the Estonian `xml.2026.en/` export) instead of crawling links, and keeps only **tax-related** acts. It re-joins the web chain at `parse_source`, so everything downstream is shared:

```
add_file_source_job (seed)  ->  fetch_file_source  ->  filter_tax_acts  ->  parse_source  ->  chunk_document  ->  schedule_embeddings  ->  embed_chunks
   (enumerate *.xml)             (read file ->            (tax act?          (shared with the web chain from here on)
                                   SourceFetch)             yes/no)
                                                              |
                                                              v
                                                       skipped (not_tax_related)
```

1. **add_file_source_job** — seed runner (not a Dramatiq actor); enumerates `*.xml` files for each `type: "xml"` source and enqueues one `fetch_file_source` message per file.
2. **fetch_file_source** — merges "frontier create" + "fetch" for local files (no link-discovery loop applies): normalizes the path to `file://<abs_path>`, dedups against an already-queued target, reads the file, and stores the raw content as a `SourceFetch` (content type `application/xml`).
3. **filter_tax_acts** — extracts the act title from the XML and classifies it with a keyword-based tax classifier. Non-tax acts are marked `skipped` (`skip_reason="not_tax_related"`) and the chain stops there; tax-related acts advance to `filtered` and re-join the web chain at `parse_source`.
4. **parse_source** onward — unchanged from the web chain (`XmlParser` is picked by content type `application/xml`/`text/xml`); `chunk_document`, `schedule_embeddings`, and `embed_chunks` are reused as-is. `schedule_discovered_links` finds zero links for XML documents, which is expected.

See [Local XML file ingestion](#local-xml-file-ingestion) below for the runner, config, and Docker service details.

The **outbox dispatcher** (`python -m laws_agent.outbox.dispatcher`) publishes committed outbox events to RabbitMQ; delivery is at-least-once and every stage is idempotent.

## Project structure

```
laws_agent/
    config.py               # env-based configuration (single source of truth)
    parsers/
        html_parser.py      # HTML → Markdown via trafilatura
        link_extractor.py   # Markdown link extraction
        text_splitter.py    # Markdown chunking via LangChain
    clients/
        hg_client.py            # HuggingFace Hub login + model loading
        llm_client.py            # Text generation + embedding client
        mock_embed_client.py     # Random-vector embedding client (EMBED_PROVIDER=mock)
        ollama_embed_client.py   # Ollama HTTP embedding client (EMBED_PROVIDER=ollama)
    models/
        document.py         # Document Pydantic model
        document_chunk.py   # DocumentChunk Pydantic model
    storage/
        sql_store.py        # PostgreSQL ORM models + repository (SQLAlchemy)
        vector_store.py     # Qdrant vector store wrapper
    mcp/
        server.py           # FastMCP server exposing KB tools
    agent/
        config.py           # agent env vars (dotenv)
        mcp_client.py       # MultiServerMCPClient factory
        graph.py            # LangGraph ReAct agent builder
        generate.py         # CLI entry point
        providers/
            ollama.py       # ChatOllama factory
            openai.py       # ChatOpenAI factory
main.py                     # Indexing entry point
migrate.py                  # Migration runner
```

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

| Variable            | Required | Default                 | Description              |
| ------------------- | -------- | ----------------------- | ------------------------ |
| `HG_TOKEN`          | yes      | —                       | HuggingFace API token    |
| `POSTGRES_USER`     | yes      | —                       | PostgreSQL user          |
| `POSTGRES_PASSWORD` | yes      | —                       | PostgreSQL password      |
| `POSTGRES_DB`       | yes      | —                       | PostgreSQL database name |
| `POSTGRES_HOST`     | no       | `localhost`             | PostgreSQL host          |
| `POSTGRES_PORT`     | no       | `5432`                  | PostgreSQL port          |
| `QDRANT_URL`        | no       | `http://localhost:6333` | Qdrant instance URL      |
| `EMBED_PROVIDER`       | no       | `huggingface`           | `huggingface` (real local model), `ollama` (remote HTTP), or `mock` (random vectors) |
| `MOCK_EMBED_DIM`       | no       | `4096`                  | Vector dimension used by the `mock` provider |
| `OLLAMA_EMBED_BASE_URL`| if `EMBED_PROVIDER=ollama` | `http://localhost:11434` | Ollama server URL **for embeddings** — separate from the agent's `OLLAMA_BASE_URL` (see [Embedding provider](#embedding-provider) for the docker-compose hostname) |
| `OLLAMA_EMBED_MODEL`   | if `EMBED_PROVIDER=ollama` | `qwen3-embedding`   | Ollama embedding model name |

### Agent env vars

| Variable         | Required             | Default                      | Description                    |
| ---------------- | -------------------- | ---------------------------- | ------------------------------ |
| `LLM_PROVIDER`   | no                   | `ollama`                     | `ollama` or `openai`           |
| `MCP_SERVER_URL` | no                   | `http://localhost:8000/mcp`  | FastMCP server endpoint        |
| `OPENAI_API_KEY` | if provider=openai   | —                            | OpenAI API key                 |
| `OPENAI_MODEL`   | no                   | `gpt-4o-mini`                | OpenAI model name              |
| `OLLAMA_BASE_URL`| no                   | `http://localhost:11434`     | Ollama server URL **for the chat LLM** — separate from embeddings' `OLLAMA_EMBED_BASE_URL` |
| `OLLAMA_MODEL`   | no                   | `llama3.2`                   | Ollama chat model name         |

## Run

Apply migrations first, then run the indexer:

```sh
python migrate.py
python main.py
```

### Enqueue web sources

`laws_agent/runners/add_web_source_job.py` reads a sources config file and publishes one crawl message per source URL to RabbitMQ. Run it after the queue workers are up.

```sh
.venv/bin/python3 -m laws_agent.runners.add_web_source_job config.json
```

When the stack runs in Docker, seed inside the compose network instead (so it reaches `rabbitmq`/`postgres` by service name via `.env.docker`):

```sh
scripts/seed.sh config.json          # defaults to config.json
# equivalent to:
docker compose run --rm seed config.json
```

The `seed` service is in the `tools` profile, so `docker compose up -d` never starts it. The config path is relative to the repo root (mounted at `/app`).

The config file must be a JSON file with this structure:

```json
{
  "groups": [
    {
      "name": "Estonia",
      "attributes": { "code": "EE" },
      "sources": [
        { "description": "Tax authority", "link": "emta.ee" },
        { "description": "Laws", "link": "https://riigiteataja.ee" }
      ]
    }
  ]
}
```

The unit is a **group**; each group lists one or more `sources`. To crawl **different URLs in one group**, add more entries under `sources`. To crawl **different groups**, add more group objects:

- Each `sources[].link` becomes one seed crawl target tagged with its group `name`. The group flows through the whole pipeline and becomes the Qdrant collection suffix (e.g. `LAWS_Estonia_qwen_embed_8b`).
- A link without a scheme (`emta.ee`) is treated as `https://emta.ee`.
- `name`, `attributes` (object), and `sources` (list of `{description, link}`) are all required.
- Re-running with the same URLs is safe — the frontier manager dedups by normalized URL, so already-crawled targets aren't re-queued.
- You only seed entry points: each seed fans out automatically as discovered same-origin links loop back into the frontier.

Make sure the pipeline workers and the outbox dispatcher are up before seeding. The script requires the following env vars in addition to the standard ones:

| Variable            | Required | Default     | Description       |
| ------------------- | -------- | ----------- | ----------------- |
| `RABBITMQ_USER`     | yes      | —           | RabbitMQ username |
| `RABBITMQ_PASSWORD` | yes      | —           | RabbitMQ password |
| `RABBITMQ_HOST`     | no       | `localhost` | RabbitMQ host     |
| `RABBITMQ_PORT`     | no       | `5672`      | RabbitMQ port     |
| `RABBITMQ_VHOST`    | no       | `/`         | RabbitMQ vhost    |

### Local XML file ingestion

See [Local XML file chain](#local-xml-file-chain) above for the actor-by-actor
flow. This section covers seeding it: a local dump of legal-act XML files
(e.g. the Estonian `xml.2026.en/` export, ~5600 files) instead of crawling
links, keeping only **tax-related** acts.

A source with `"type": "xml"` enumerates files instead of crawling a link:

```json
{
  "groups": [
    {
      "name": "Estonia",
      "attributes": { "code": "EE", "Country": "Estonia" },
      "sources": [
        { "description": "Estonian acts XML dump (English).", "type": "xml", "path": "xml.2026.en", "glob": "*.xml" }
      ]
    }
  ]
}
```

- `path` is resolved relative to the repo root; `glob` defaults to `*.xml`.
- This config form lives in `config.files.json` at the repo root.

Seed it the same way as the web chain, just with the file-chain runner/script:

```sh
.venv/bin/python3 -m laws_agent.runners.add_file_source_job config.files.json
```

```sh
scripts/seed_files.sh config.files.json   # defaults to config.files.json
# equivalent to:
docker compose run --rm seed-files config.files.json
```

The chain runs on two new worker services (`worker-fetch-file-source`,
`worker-filter-tax-acts`), both in the `tools`-adjacent default profile like
the rest of the pipeline workers — bring the stack up as usual with
`docker compose up -d --build` before seeding.

### Run the LangGraph agent

The agent connects to the MCP server and answers questions using the knowledge base.

Start the MCP server first:

```sh
python -m laws_agent.mcp.server
```

Then send a prompt (defaults to Ollama):

```sh
python -m laws_agent.agent.generate "What are the VAT rules in Estonia?"

# or explicitly choose a provider
python -m laws_agent.agent.generate "What are the VAT rules?" ollama
python -m laws_agent.agent.generate "What are the VAT rules?" openai

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

  > **Note:** embeddings use their own `OLLAMA_EMBED_BASE_URL`, deliberately separate from the chat agent's `OLLAMA_BASE_URL` (`laws_agent/agent/config.py`). The embed worker runs in docker (so it needs `host.docker.internal`/the compose service name), while the agent runs on the host (so `localhost`), and they can point at different Ollama servers and models entirely.

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
dramatiq laws_agent laws_agent.actors.embed_chunks_actor --processes 1 --threads 1
```

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
