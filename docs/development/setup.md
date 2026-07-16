# Development setup

## Python

The package requires Python 3.11 or newer.

```sh
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,server,web,embed]'
cp .env.example .env
```

Optional extras also exist for `mcp` and `agent`, but the current MCP server is
incomplete and is not a working development entry point.

## Infrastructure

The backend requires environment variables for Postgres and RabbitMQ at import
time. Start the repository's configured services:

```sh
docker compose up -d --build postgres rabbitmq qdrant
python -m backend.shared.storage.sql.migrate
```

The custom Postgres image is required for BM25 because it builds and preloads
`pg_textsearch`.

## Environment reference

The backend loads `.env` on the host. Compose services load `.env.docker`, while
Compose itself reads `.env` for `${...}` interpolation.

| Variable | Required/default | Purpose |
| --- | --- | --- |
| `POSTGRES_USER` | required | Database user |
| `POSTGRES_PASSWORD` | required | Database password |
| `POSTGRES_DB` | required | Database name |
| `POSTGRES_HOST` | `localhost` | Database host |
| `POSTGRES_PORT` | `5432` | Database port |
| `QDRANT_URL` | `http://localhost:6333` | Vector API |
| `RABBITMQ_USER` | required | Broker user |
| `RABBITMQ_PASSWORD` | required | Broker password |
| `RABBITMQ_HOST` | `localhost` | Broker host |
| `RABBITMQ_PORT` | `5672` | AMQP port |
| `RABBITMQ_VHOST` | `/` | Broker virtual host |
| `SOURCE_ROOT` | `sources` | Root exposed by the source browser/seeder |
| `PIPELINE_RUNS_DIR` | `/tmp/pipeline_runs` | Run logs and artifact root |
| `LOG_DIR` | `logs` | Fallback logging root without a run |
| `INSECURE_TLS_DOMAINS` | empty | Comma-separated TLS-verification exceptions |

Embedding fallback variables are used only when no provider snapshot is
available: `EMBED_PROVIDER` (default `ollama`), `MOCK_EMBED_DIM` (`4096`),
`OLLAMA_EMBED_BASE_URL` (`http://localhost:11434`), and
`OLLAMA_EMBED_MODEL` (`qwen3-embedding`). Provider-form defaults may also read
`OLLAMA_URL`, `OLLAMA_PORT`, `OPENAI_BASE_URL`, and `RERANKER_PATH`.

Structured plugin output limits are bytes:
`PARSER_METADATA_MAX_BYTES=262144`,
`PARSER_INTERMEDIATE_MAX_BYTES=8388608`, and
`CHUNK_METADATA_MAX_BYTES=262144`.

Start the API on the host:

```sh
uvicorn backend.server.main:app --reload
```

Actors are normally developed through their Compose services so each queue has
the same process and mount layout as the full stack.

## UI

```sh
cd ui
npm ci
npm run dev
```

`VITE_SERVER_URL` can override the API base URL; it defaults to
`http://localhost:8000`.
