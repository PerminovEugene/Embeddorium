# Embeddings Tester Server

FastAPI backend for the **Embeddings Tester** UI (`../ui`). It embeds a set of
*source* and *candidate* texts with one or more Ollama models and scores every
source/candidate pair with the selected similarity metrics, returning a ranked
table of matches.

It is integrated with the main **laws-agent** project and reuses its code rather
than duplicating it:

- `laws_agent.clients.ollama_embed_client.OllamaEmbedClient` — embedding calls
  (the same client the ingestion pipeline uses for `EMBED_PROVIDER=ollama`).
- `laws_agent.storage.vector.vector_store.VectorStore` — Qdrant persistence
  (one collection per model: `embedorium_<model>_<dim>`).
- `laws_agent.config` — `QDRANT_URL` and the shared env contract.

## Layout

| File                   | Purpose                                                        |
| ---------------------- | ------------------------------------------------------------- |
| `main.py`              | FastAPI app + `/compare` and `/health` endpoints              |
| `models.py`            | Pydantic request models (`CompareRequest`)                    |
| `embedder.py`          | Embeddings via `OllamaEmbedClient`                            |
| `vector_store_utils.py`| Qdrant collection + upsert via `VectorStore`                 |
| `matcher.py`           | Similarity metrics + pairwise scoring                         |

## Running with Docker (recommended)

The server is a service in the repo's `docker-compose.yml`. It is built from the
shared `Dockerfile.dev` (so `laws_agent` is importable) and reads `.env.docker`
for `QDRANT_URL` plus the DB/RabbitMQ vars `laws_agent.config` requires at import
time.

```sh
# from the repo root
docker compose up -d --build qdrant server ui
```

- API: http://localhost:8000  (docs at `/docs`)
- UI:  http://localhost:5173

Embeddings are produced by an **Ollama** server. The Ollama port is chosen per
request in the UI; the host is set by `OLLAMA_HOST` (default
`host.docker.internal`, i.e. Ollama running on the Docker host). Pull a model
first, e.g. `ollama pull nomic-embed-text`.

## Running standalone (on the host)

Because the server imports `laws_agent`, install the project with the `server`
extra and run it from this directory. It uses the repo's `.env` (it needs the
same Postgres/RabbitMQ vars at import, even though `/compare` only touches
Qdrant + Ollama).

```sh
# from the repo root
python -m venv .venv && source .venv/bin/activate
pip install -e ".[server]"

cd server
OLLAMA_HOST=localhost uvicorn main:app --reload --port 8000
```

## Endpoints

- `POST /compare` — embed source/candidate texts and return ranked pair scores.
- `GET /health` — health check.
