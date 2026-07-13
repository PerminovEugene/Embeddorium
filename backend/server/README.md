# Embeddings Tester Server

FastAPI backend for the **Embeddings Tester** UI (`../ui`). It embeds a set of
*source* and *candidate* texts with one or more Ollama models and scores every
source/candidate pair with the selected similarity metrics, returning a ranked
table of matches.

It is integrated with the main **embeddorium** project and reuses its code rather
than duplicating it:

- `backend.shared.clients.ollama_embed_client.OllamaEmbedClient` — embedding calls
  (the same client the ingestion pipeline uses for `EMBED_PROVIDER=ollama`).
- `backend.shared.storage.vector.vector_store.VectorStore` — Qdrant persistence
  (one collection per model: `embeddorium_<model>_<dim>`).
- `backend.shared.config` — `QDRANT_URL` and the shared env contract.

## Layout

The server is organized **component-first**: each feature owns its own
router, schemas and logic in one folder, rather than being split across
top-level `routers/`/`schemas/`/`services/` layers.

| Path                       | Purpose                                                        |
| -------------------------- | --------------------------------------------------------------- |
| `main.py`                  | App assembly only: `FastAPI()`, CORS, `include_router` per component, `/health` |
| `compare/router.py`        | `/compare` handler + provider resolution                      |
| `compare/schemas.py`       | `CompareRequest` (+ `TextGroup`/`TextItem`)                    |
| `compare/embedder.py`      | Embeddings via `OllamaEmbedClient` (also used by `search/`)    |
| `compare/matcher.py`       | Similarity metrics + pairwise scoring                          |
| `compare/vector_store.py`  | Qdrant upsert via `VectorStore`                                |
| `search/router.py`         | `/search` handler                                              |
| `search/schemas.py`        | `SearchRequest` (+ `TextGroup`/`TextItem`)                     |
| `search/service.py`        | Nearest-vector search over a run's collection + Postgres join  |
| `pipeline/router.py`       | `/pipeline-runs` CRUD + launch endpoints                       |
| `pipeline/schemas.py`      | camelCase `PipelineRun*` API schemas                           |
| `pipeline/launch.py`       | Seeds the ingestion pipeline from a created run                |
| `pipeline/runs.py`         | Lists/loads ingestion pipeline runs from Postgres              |
| `providers/router.py`      | `/providers` CRUD endpoints                                    |
| `providers/schemas.py`     | camelCase `Provider*` API schemas                              |
| `datasets/router.py`       | `/datasets` CRUD endpoints                                     |
| `datasets/schemas.py`      | camelCase `Dataset*` API schemas                                |
| `chunkers/router.py`       | `/chunkers` read-only metadata endpoint                        |
| `chunkers/schemas.py`      | camelCase `ChunkerConfig*` API schemas                          |
| `source_files/router.py`   | `/source-files` browse endpoint                                |
| `source_files/source_root.py` | Resolve/guard paths against the ingestion source root       |

`compare/embedder.py` is the one function shared across components:
`search/service.py` imports `get_embeddings` from it rather than duplicating
it, so both `/compare` and `/search` embed text identically.

## Running with Docker (recommended)

The server is a service in the repo's `docker-compose.yml`. It is built from the
shared `Dockerfile.dev` (so `backend` is importable) and reads `.env.docker`
for `QDRANT_URL` plus the DB/RabbitMQ vars `backend.shared.config` requires at import
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

Because the server imports `backend`, install the project with the `server`
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
- `GET /pipeline-runs` — list the ingestion pipeline runs (from Postgres)
  available as a source DB. Each run carries the collection it populated and the
  embedding provider/model it was built with.
- `POST /search` — embed each source text, return its 10 nearest vectors from
  the selected run's collection (the distance is fixed at collection-creation
  time, so no metric is passed), and enrich each hit with the chunk/document
  "batch info" joined from Postgres. The collection and embedding model are read
  off the run, not the request. Touches Qdrant, Ollama **and** Postgres.
- `GET /health` — health check.

### `/search` request shape

```jsonc
{
  "configuration": {
    "runId": "3f2c…" // the pipeline run; supplies the collection + embed model
  },
  "source": { "inputs": [{ "id": "q1", "text": "your query" }] }
}
```
