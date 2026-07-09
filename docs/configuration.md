# Configuration

Configuration is entirely environment-based — there is no config file to edit
and no seed script to run. Copy the template and fill it in:

```sh
cp .env.example .env
```

There are two env files:

- **`.env`** — host/local runs. Use `localhost` for everything.
- **`.env.docker`** — the Compose stack. Use Compose service names as hosts
  (`postgres`, `qdrant`, `rabbitmq`), and `host.docker.internal` or the `ollama`
  service name to reach Ollama (see [embeddings.md](embeddings.md)).

## Core

| Variable | Required | Default | Description |
| -------- | -------- | ------- | ----------- |
| `POSTGRES_USER` | yes | — | PostgreSQL user |
| `POSTGRES_PASSWORD` | yes | — | PostgreSQL password |
| `POSTGRES_DB` | yes | — | PostgreSQL database name |
| `POSTGRES_HOST` | no | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | no | `5432` | PostgreSQL port |
| `QDRANT_URL` | no | `http://localhost:6333` | Qdrant instance URL |
| `HG_TOKEN` | no | — | HuggingFace token. Only the `huggingface` embedding provider uses it; it no-ops when unset. |

## Message broker

The server and workers need RabbitMQ credentials.

| Variable | Required | Default | Description |
| -------- | -------- | ------- | ----------- |
| `RABBITMQ_USER` | yes | — | RabbitMQ username |
| `RABBITMQ_PASSWORD` | yes | — | RabbitMQ password |
| `RABBITMQ_HOST` | no | `localhost` | RabbitMQ host |
| `RABBITMQ_PORT` | no | `5672` | RabbitMQ port |
| `RABBITMQ_VHOST` | no | `/` | RabbitMQ vhost |

## Embeddings

Fallbacks for how chunk vectors are produced — each run normally carries its
own provider snapshot, which takes precedence. See [embeddings.md](embeddings.md)
for the full rundown of each provider and the Ollama networking details.

| Variable | Required | Default | Description |
| -------- | -------- | ------- | ----------- |
| `EMBED_PROVIDER` | no | `huggingface` | `huggingface` (local model), `ollama` (remote HTTP), or `mock` (random vectors) |
| `MOCK_EMBED_DIM` | no | `4096` | Vector dimension for the `mock` provider |
| `OLLAMA_EMBED_BASE_URL` | if `ollama` | `http://localhost:11434` | Ollama server URL **for embeddings** |
| `OLLAMA_EMBED_MODEL` | if `ollama` | `qwen3-embedding` | Ollama embedding model |

## Chat agent

Used only by the optional LangGraph agent (`agent-generate`). Its provider,
endpoint, and model are deliberately independent from the embedding settings
above — the agent usually runs on the host while the embed worker runs in Docker.

| Variable | Required | Default | Description |
| -------- | -------- | ------- | ----------- |
| `LLM_PROVIDER` | no | `ollama` | `ollama` or `openai` |
| `MCP_SERVER_URL` | no | `http://localhost:8000/mcp` | FastMCP server endpoint |
| `OLLAMA_BASE_URL` | no | `http://localhost:11434` | Ollama server URL **for the chat LLM** |
| `OLLAMA_MODEL` | no | `llama3.2` | Ollama chat model |
| `OPENAI_API_KEY` | if `openai` | — | OpenAI API key |
| `OPENAI_MODEL` | no | `gpt-4o-mini` | OpenAI model |

> The two `OLLAMA_*_BASE_URL` variables are separate on purpose. Embeddings use
> `OLLAMA_EMBED_BASE_URL` (from a container), the agent uses `OLLAMA_BASE_URL`
> (from the host). They can point at entirely different Ollama servers and
> models.
