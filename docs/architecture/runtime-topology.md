# Runtime topology

Docker Compose starts infrastructure, one API, one UI, one migration job, one
outbox loop, and one worker container per actor.

| Service | Responsibility | Host exposure |
| --- | --- | --- |
| `postgres` | PostgreSQL 17 plus `pg_textsearch` | `${POSTGRES_PORT:-5432}` |
| `qdrant` | Dense-vector storage | `6333`, `6334` |
| `rabbitmq` | Dramatiq broker and management UI | `${RABBITMQ_PORT:-5672}`, `${RABBITMQ_MANAGEMENT_PORT:-15672}` |
| `migrate` | Reapply ordered SQL migrations, then exit | none |
| `server` | FastAPI and synchronous retrieval | `8000` |
| `ui` | Vite development server | `5173` |
| `worker-outbox-dispatcher` | Poll committed events and publish messages | none |
| `worker-*` | One ingestion stage each | none |

## Worker concurrency

Every Dramatiq service is launched with `--processes 1 --threads 1` and consumes
one queue. Compose defines one replica per service, so the shipped concurrency
for each stage—including embedding—is one message at a time.

There is no application rate limiter or semaphore. Increasing worker processes,
threads, or replicas increases concurrent calls to providers. The embed client
cache is lazily populated and the Compose comment explicitly relies on a single
thread to avoid first-initialization races.

The outbox dispatcher is a single poll loop. It reads up to 100 pending events
at a time and sleeps one second only when it publishes none.

## Startup ordering

Workers wait for RabbitMQ health and successful migration completion. Most
database dependencies use `service_started`, not a Postgres health check; the
migration entry point retries database connections up to 60 times at one-second
intervals.

The server and Qdrant do not have Compose health checks.
