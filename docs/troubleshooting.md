# Troubleshooting

Common problems running the local stack, with the actual commands to diagnose
them. Start with the two catch-alls:

```sh
docker compose ps          # what's up, what's restarting
docker compose logs -f <service>   # follow one service (e.g. server, worker-embed-chunks)
```

Service names are listed in [architecture.md](architecture.md#services).

## A Docker service won't start

```sh
docker compose ps                 # look for Exit / Restarting
docker compose logs migrate       # migrations must complete before workers run
docker compose logs postgres
```

- **Postgres exits immediately** — usually empty `POSTGRES_USER` / `PASSWORD`
  because there is no `.env`. Compose interpolates those from `.env`. Fix:
  `cp .env.example .env`, then `docker compose up -d`.
- **Workers restart in a loop** — they `depends_on` the `migrate` service and a
  healthy RabbitMQ. They're set to `restart: on-failure` and normally settle once
  those are ready. If they don't, read `docker compose logs migrate`.

## Port already in use

`Error ... port is already allocated` on start. Find and free the port, or remap
it.

```sh
lsof -i :5173   # or :8000, :6333, :5432, :5672, :15672
```

Then either stop the conflicting process, or change the **host** side of the port
mapping (Postgres/RabbitMQ ports come from `.env`; UI/API/Qdrant from
`docker-compose.yml`).

## RabbitMQ connection failures

Workers log `Connection refused` / AMQP errors on startup.

```sh
docker compose ps rabbitmq                 # should be healthy
docker compose logs rabbitmq
open http://localhost:15672                # management UI, laws_user / laws_pass
```

RabbitMQ has a healthcheck and workers wait for `service_healthy`, so this is
usually transient at first boot. Credentials must match between `.env` (Compose
interpolation) and `.env.docker` (inside containers).

## Qdrant unavailable

Runs never produce a collection, or the embed worker logs connection errors to
Qdrant.

```sh
docker compose ps qdrant
curl -s http://localhost:6333/collections   # from the host
open http://localhost:6333/dashboard
```

Inside containers Qdrant is `http://qdrant:6333` (`QDRANT_URL` in `.env.docker`),
**not** `localhost`.

## Postgres migration failure

The `migrate` service exits non-zero and workers won't start.

```sh
docker compose logs migrate
```

To reset the database and re-apply migrations from scratch:

```sh
scripts/clean-postgres.sh     # wipes tables + re-runs migrations
# or, nuke volumes entirely:
docker compose down -v && docker compose up -d --build
```

## Ollama not reachable from Docker

Only relevant when using the `ollama` embedding provider (the default mock path
needs none of this). The embed worker runs **in a container**, so
`http://localhost:11434` points at the container's own loopback, not your host.

```sh
# From inside the embed worker, test reachability:
docker compose exec worker-embed-chunks curl -s http://host.docker.internal:11434/api/tags
```

- **Ollama on the host (Docker Desktop):** use
  `OLLAMA_EMBED_BASE_URL=http://host.docker.internal:11434`.
- **Linux without Docker Desktop:** use the bridge IP (e.g.
  `http://172.17.0.1:11434`) or add
  `extra_hosts: ["host.docker.internal:host-gateway"]`.
- **Ollama in your own container:** attach it to the project's Compose network
  and use its container name (e.g. `http://ollama:11434`).

Full matrix in [embeddings.md](embeddings.md#pointing-a-container-at-ollama).

## Embedding model missing

Ollama returns a "model not found" error during embedding. Pull the model on
whichever host runs Ollama, and make sure the provider's model name matches.

```sh
ollama pull qwen3-embedding   # on whichever host/container runs Ollama
ollama list                   # confirm it's there
```

## The UI can't reach the API

UI loads but lists are empty or requests fail.

```sh
docker compose ps server
docker compose logs server
curl -s http://localhost:8000/datasets    # should return JSON (even [])
```

If the API responds on the host but the UI can't reach it, confirm the `server`
container is healthy and hasn't crash-looped on a bad env value.

## A run is stuck in `pending` or `running`

A run advances only while the workers and the **outbox dispatcher** are alive —
no dispatcher means messages never leave Postgres.

```sh
docker compose ps                              # all workers + worker-outbox-dispatcher up?
docker compose logs -f worker-outbox-dispatcher
docker compose logs -f worker-embed-chunks
```

Also inspect the run's per-URL logs and artifacts on the host:

```sh
ls tmp/pipeline_run/<run-id>/
```

A run flips to `completed` only once no active crawl targets remain **and** every
scheduled embed batch finished (see
[architecture.md](architecture.md#runs-are-self-contained)). If a stage failed,
its `crawl_target` will be in a `failed_*` or `skipped` state — check the API
(`GET /pipeline-runs/<id>`) or the worker logs for the failing stage.

## How to inspect logs and artifacts

```sh
docker compose logs -f <service>              # live logs for one service
docker compose logs --tail=200 <service>      # recent history
ls tmp/pipeline_run/<run-id>/                 # per-run logs + raw/parsed files
```

Artifacts live under
`tmp/pipeline_run/<run-id>/sources/<source-id>/{raw,parsed}/` — the raw fetched
bytes and the parsed text, exactly as each stage produced them.

## Full reset

When in doubt, wipe everything and start clean:

```sh
scripts/full-clean.sh          # queues + Qdrant + Postgres + logs + rebuild workers
# or
docker compose down -v && docker compose up -d --build
```
