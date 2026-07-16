# Embeddorium Server

FastAPI backend for the Embeddorium UI (`../../ui`). It is the control plane and
query surface for the RAG pipeline:

- **Compare** (`/compare`) — embed user-supplied *source* and *candidate* texts
  with a selected provider and score every pair with the requested similarity
  metrics, in-process (no Qdrant round-trip).
- **Search** (`/search`) — treat each source text as a *query* against a Qdrant
  collection already populated by an ingestion pipeline run, via semantic,
  keyword (BM25), or hybrid (RRF-fused, optionally reranked) retrieval.
- **Management CRUD** — providers, datasets, and pipeline runs (create → launch →
  monitor), plus read-only plugin metadata (chunkers, actor strategies) and a
  server-side source-file browser.

It reuses the main project's shared code rather than duplicating it:

- `backend.plugins.provider_types` — provider adapters (Ollama, OpenAI-compatible,
  mock); the embedding type/model/endpoint all come from a saved provider
  record's `config`, so there is no global embedding-host env var.
- `backend.shared.storage.sql` — the `SqlStore` façade over repositories.
- `backend.shared.storage.vector.vector_store.VectorStore` — Qdrant access.
- `backend.shared.clients.queue` — the Dramatiq broker used to seed a run.
- `backend.shared.config` — `QDRANT_URL` and the shared env contract.

## Layout

The server is organized **component-first**: each feature owns its router,
schemas, and logic in one folder, instead of being split across top-level
`routers/` / `schemas/` / `services/` layers.

| Path                         | Purpose                                                           |
| ---------------------------- | ---------------------------------------------------------------- |
| `main.py`                    | App assembly only: `FastAPI()`, lifespan, CORS, routers, `/health` |
| `dependencies.py`            | `Depends(...)` providers for the shared `SqlStore` / Qdrant / broker |
| `compare/`                   | `/compare` — `router`, `schemas`, `service`, `embedder`, `matcher` |
| `search/`                    | `/search` + `/searches` history — `router`, `schemas`, `history`, `service/` |
| `search/service/`            | Orchestrator (`__init__`) + strategies (`semantic`/`keyword`/`hybrid`), `rrf`, `reranker`, `results`, `params` |
| `pipeline/`                  | `/pipeline-runs` — `router`, `schemas`, `runs`, `launch`, `service/` |
| `pipeline/service/`          | One module per operation: `create`, `launch`, `lifecycle`, `common` |
| `providers/`                 | `/providers` CRUD + `/providers/configs` — `router`, `schemas`, `config_schemas` |
| `datasets/`                  | `/datasets` CRUD — `router`, `schemas`                            |
| `chunkers/`                  | `/chunkers` read-only plugin metadata — `router`, `schemas`       |
| `actor_configs/`             | `/actor-configs` read-only per-actor strategy metadata — `router`, `schemas` |
| `source_files/`              | `/source-files` browse endpoint — `router`, `schemas`, `service`, `source_root` |

`compare/embedder.py`'s `get_embeddings` is shared: `search/service` imports it
rather than duplicating the provider-dispatch, so `/compare` and `/search` embed
text identically.

## Architecture

### Request lifecycle: router → service → repository

Routers are **thin controllers**. A handler parses/validates the request (mostly
via its Pydantic schema), calls one service function, and returns the result.
All business logic — status-transition rules, provider resolution, snapshotting,
retrieval strategy — lives in the component's `service` module (or `service/`
package when an endpoint group has several distinct operations, as
`pipeline/service/` and `search/service/` do).

Persistence stays behind `SqlStore` repositories (`store.providers`,
`store.pipeline_runs`, `store.chunks`, …) and `VectorStore` for Qdrant. Services
call repositories; they never build SQL or open sessions themselves.

### Dependency injection

`main.py`'s `lifespan` builds exactly one `SqlStore` (engine + pool), one
`QdrantClient` (HTTP pool), and one Dramatiq broker on startup, stashes them on
`app.state`, and closes them on shutdown. Handlers receive them through
`Depends(get_sql_store)` / `Depends(get_qdrant_client)` / `Depends(get_broker)`
(`dependencies.py`). Sharing one instance of each lets its connection pool be
reused across requests instead of each request spinning up and tearing down its
own. Nothing constructs these clients per-request.

### Data-model boundaries

Three representations, converted at fixed seams:

- **ORM models** (`backend.shared.storage.sql.models`) never leave the storage
  layer — repositories convert them to **domain models** (`backend.shared.models`)
  before returning, so services and routers never touch a live ORM instance.
- **Domain models** are what services operate on.
- **camelCase DTOs** (each component's `schemas.py`) are the wire format matching
  the UI's TypeScript types. Conversions are explicit `*_to_out` /
  `*_in_to_domain` helpers, and routers set `response_model_by_alias=True` so
  responses serialize with camelCase aliases.

## Error handling

**Strategy: expected error conditions are raised as `fastapi.HTTPException` at
the point of failure, with an accurate status code and a human-readable
`detail`. FastAPI renders them as `{"detail": "..."}` with that status.** This is
the single, framework-canonical error currency across every endpoint — chosen
over a custom domain-exception + handler layer because the services here are
HTTP-only (never reused outside the web process), so that indirection would add
cost without payback.

Conventions:

- **Status codes.** `400` malformed/invalid input or parameters; `404` resource
  not found *and* unparseable ids (a non-UUID id is treated as "not found");
  `409` state conflict (e.g. launching a run that is already `running`); `422`
  request-body schema validation, produced automatically by Pydantic.
- **Where it's raised.** As close to the failure as possible — inside the service
  (or a small helper like `parse_run_id`, `_parse_id`, `_resolve_compare_provider`),
  not deferred to the router. Routers stay free of error branching.
- **Internal `ValueError` → HTTP at the boundary.** A few pure helpers raise
  `ValueError` (e.g. `search/service/reranker.resolve_reranker_target`,
  `source_files/source_root.safe_resolve_within_root`, `pipeline.launch.seed_pipeline`
  on an unsupported `source_type`). Each is caught by its calling service and
  re-raised as the appropriate `HTTPException` (all `400` today). Helpers stay
  framework-free; the service owns the HTTP mapping.
- **Best-effort paths never fail the request.** Search-history persistence
  (`_persist_search`) and cross-encoder reranking (`rerank_results`) catch, log,
  and continue — a transient DB/network problem must not break an
  otherwise-successful search. These are deliberate, documented at their call
  sites, and are *not* error paths.
- **Unexpected exceptions** fall through to FastAPI's default `500`
  (`{"detail": "Internal Server Error"}`, logged with a traceback). Handlers do
  not catch broad `Exception` to hide bugs.

Every endpoint follows this: the CRUD groups (`providers`, `datasets`,
`pipeline-runs`) 404 on unknown/unparseable ids and 400 on bad payloads;
`/compare` and `/search` 400 on bad configuration and 404 on an unknown run;
read-only metadata endpoints (`/chunkers`, `/actor-configs`, `/source-files`)
have no client-error branches beyond `/source-files`' 400/404 for a bad path.

Success responses return their data directly (the resource DTO for CRUD, the
result list for search). `/compare` and `/search` additionally wrap their
payload in a small `{"status": "success", ...}` envelope; the UI reads the data
keys (`matches` / `results`) and ignores `status`.

## Endpoints

| Method & path                        | Purpose                                              |
| ------------------------------------ | ---------------------------------------------------- |
| `POST /compare`                      | Embed source/candidate texts; return ranked pair scores |
| `POST /search`                       | Retrieve nearest chunks for each query from a run's collection |
| `GET /searches`                      | List persisted search launches (newest first)        |
| `GET /searches/{id}`                 | One persisted search with its stored hits            |
| `GET /pipeline-runs`                 | List ingestion runs (newest first)                   |
| `POST /pipeline-runs`                | Create a run (`status="pending"`); does not launch   |
| `GET /pipeline-runs/{id}`            | One run, with live chunk-progress counts             |
| `POST /pipeline-runs/{id}/launch`    | Launch/relaunch a run by seeding its messages        |
| `PATCH /pipeline-runs/{id}`          | Manually update a run's status                       |
| `DELETE /pipeline-runs/{id}`         | Delete a run and its on-disk files                   |
| `GET /pipeline-runs/{id}/targets`    | Paginated crawl targets for a run                    |
| `GET /providers`, `POST /providers`  | List / create providers                              |
| `GET /providers/configs`            | Discovered provider adapters + form metadata          |
| `GET/PUT/DELETE /providers/{id}`     | Fetch / replace / delete a provider                  |
| `GET /datasets`, `POST /datasets`    | List / create datasets                               |
| `GET/PUT/DELETE /datasets/{id}`      | Fetch / replace / delete a dataset                   |
| `GET /chunkers`                      | Discovered chunker plugins                            |
| `GET /actor-configs`                 | Discovered strategy configs per plugin-backed actor  |
| `GET /source-files`                  | Browse the ingestion source tree                     |
| `GET /health`                        | Liveness check                                        |

### `/search` request shape

```jsonc
{
  "configuration": {
    "runId": "3f2c…",          // the pipeline run; supplies collection + embed model
    "topK": 10,                 // hits per query (default DEFAULT_TOP_K)
    "searchMethod": "hybrid",   // semantic | keyword | hybrid
    "useReranking": true,       // hybrid-only, optional cross-encoder rerank
    "rerankerProviderId": "…",  // required when useReranking is true
    "rerankerTopK": 5
  },
  "source": { "inputs": [{ "id": "q1", "text": "your query" }] }
}
```

The collection and embedding model are always read off the selected run, never
from the request, so a query is embedded the same way the collection was indexed.

## Running with Docker (recommended)

The server is a service in the repo's `docker-compose.yml`, built from the shared
`Dockerfile.dev` (so `backend` is importable). It reads `.env.docker` for
`QDRANT_URL` plus the Postgres/RabbitMQ vars `backend.shared.config` requires at
import time.

```sh
# from the repo root
docker compose up -d --build qdrant server ui
```

- API: http://localhost:8000  (interactive docs at `/docs`)
- UI:  http://localhost:5173

Embeddings come from the provider selected in the UI (a saved provider record).
For a local Ollama provider, pull a model first, e.g.
`ollama pull nomic-embed-text`.

## Running standalone (on the host)

Because the server imports `backend`, install the project with the `server` extra
and run it from this directory. It uses the repo's `.env` (the same
Postgres/RabbitMQ vars are needed at import).

```sh
# from the repo root
python -m venv .venv && source .venv/bin/activate
pip install -e ".[server]"

cd backend/server
uvicorn main:app --reload --port 8000
```
