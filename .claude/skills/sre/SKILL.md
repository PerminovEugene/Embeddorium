---
name: sre
description: Conventions for infra, Docker Compose, and operating the pipeline services. Use when touching docker-compose, Dockerfiles, infra/, env config, or debugging the RabbitMQ/Postgres/Qdrant stack.
---

# SRE

Local-first stack: Postgres, Qdrant, RabbitMQ, and Dramatiq workers, wired by `docker-compose.yml`. Config in `infra/`.

- Config comes from env (`.env`, `.env.docker`) — never commit secrets, never hardcode hosts/ports. Add new vars to both the env template and compose.
- Keep the container image lean: the worker embed path uses HTTP clients only — no torch/sentence-transformers in the image. Heavy ML deps run by hand, not in compose.
- Services are independent workers; a stage failing must not silently wedge the queue. Rely on the outbox + Dramatiq retries, and make actors idempotent so a retry is safe.
- Health: each service should come up cleanly and be checkable (Postgres ready, RabbitMQ reachable, Qdrant `/healthz`). Add depends_on/healthchecks when adding a service.
- Pin image versions in compose; don't use `latest` for stateful services.
- Persist state via named volumes for Postgres/Qdrant; treat workers as disposable.
- Logs to stdout, structured where possible; no logging to files inside containers.
- Migrations run automatically via the Compose `migrate` service before workers start; by hand: `python -m backend.shared.storage.sql.migrate`.

## Reset & rebuild helpers (`scripts/`)
- `clean-postgres.sh` / `clean-qdrant.sh` / `purge-queues.sh` — wipe one store.
- `full-clean.sh` — wipe all three between experiment runs.
- `rebuild-workers.sh` — rebuild + restart worker containers after backend changes.

## Service URLs (local)
UI :5173 · API :8000/docs · Qdrant dashboard :6333/dashboard · RabbitMQ management :15672.

## Checks before done
- `docker compose config` validates.
- `docker compose up` brings the stack healthy from clean volumes.
- No secret or absolute local path left in tracked files.
