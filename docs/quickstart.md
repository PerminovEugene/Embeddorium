# Quick start

Get from a fresh clone to a **completed pipeline run** using the `mock`
embedding provider — no model, no external services. This is the detailed
version of the [README quick start](../README.md#quick-start). For a fully
guided, click-by-click walk-through see the
[first mock run tutorial](tutorials/first_mock_run.md).

## Prerequisites

- **Docker** with Compose v2 (`docker compose`, not `docker-compose`). Docker
  Desktop on Mac/Windows, or Docker Engine + the Compose plugin on Linux.
- **Git**.
- Free ports on the host: `5173` (UI), `8000` (API), `6333` (Qdrant), `5432`
  (Postgres), `5672` / `15672` (RabbitMQ).

You do **not** need Python installed for the Docker path — everything runs in
containers.

## 1. Clone and configure

```sh
git clone <repo-url> embeddorium && cd embeddorium
cp .env.example .env
```

The defaults in `.env` work as-is. Two env files are in play:

- **`.env`** — read by Docker Compose for `${...}` interpolation in
  `docker-compose.yml` (Postgres/RabbitMQ credentials and host ports). Required
  even for a pure-Docker run; that's why you copy it first.
- **`.env.docker`** — committed; loaded _inside_ the worker/API containers
  (hosts are Compose service names like `postgres`, `qdrant`, `rabbitmq`).

Full variable reference: [configuration.md](configuration.md).

## 2. Start the stack

```sh
docker compose up -d --build
```

This builds and starts Postgres, Qdrant, RabbitMQ, every pipeline worker, the
API, and the UI.

**Migrations run automatically.** A one-shot `migrate` service applies the SQL
migrations on startup, and every worker `depends_on` it completing successfully —
so there is no manual migration step for the Docker path. (To run them by hand
on the host: `python -m backend.shared.storage.sql.migrate`.)

Check everything came up:

```sh
docker compose ps
```

## 3. Service URLs

| Service             | URL                             | Notes                                   |
| ------------------- | ------------------------------- | --------------------------------------- |
| UI                  | http://localhost:5173           | Main app                                |
| API + docs          | http://localhost:8000/docs      | Interactive OpenAPI docs                |
| Qdrant dashboard    | http://localhost:6333/dashboard | Vector collections                      |
| RabbitMQ management | http://localhost:15672          | Queues; login `laws_user` / `laws_pass` |

**Default credentials** (from `.env.example`, change for anything non-local):
Postgres and RabbitMQ both use `embeddorium_user` / `embeddorium_pass`. The UI and API have no
auth — they are meant for local use only.

## 4. First run with the mock provider

The embedding provider is **not** a global setting you flip — you create a
provider record and select it per run. In the UI (http://localhost:5173):

1. **Providers** → **Create** → type **Mock**, model type **embedding**, give it
   a name. Save.
2. **Datasets** → **Create** → a **Web** dataset is simplest: a name, one URL,
   and depth `0` (fetch just that page, follow no links).
3. **Pipeline runs** → **Start / New run** → pick the dataset and the mock
   provider, then launch.

Prefer the API? The same thing over HTTP is in the
[first mock run tutorial](tutorials/first_mock_run.md#appendix-do-it-over-the-api).

## 5. Expected result

- The run appears in **Pipeline runs** and advances through its stages to
  **`completed`** (with a `finishedAt` timestamp) within a few seconds — the mock
  provider loads no model.
- A new **collection** shows up in the Qdrant dashboard
  (http://localhost:6333/dashboard) holding the chunk vectors.
- Raw and parsed artifacts appear on the host under
  `tmp/pipeline_run/<run-id>/sources/<source-id>/{raw,parsed}/`.

If the run stays in `running` or `pending`, see
[troubleshooting.md](troubleshooting.md#a-run-is-stuck-in-pending-or-running).

## 6. Reset local state

To wipe everything and start clean between experiments:

```sh
scripts/full-clean.sh
```

This ensures infra is up, stops workers, purges RabbitMQ queues, drops Qdrant
collections, wipes Postgres and re-runs migrations, clears logs, and rebuilds the
workers. Individual scripts (`clean-postgres.sh`, `clean-qdrant.sh`,
`purge-queues.sh`) are in `scripts/` — see [development.md](development.md).

To tear the whole stack down (and drop volumes):

```sh
docker compose down -v
```

## Common startup failures

| Symptom                              | Likely cause                                      | Fix                                                                             |
| ------------------------------------ | ------------------------------------------------- | ------------------------------------------------------------------------------- |
| `port is already allocated`          | Another process on 5173/8000/6333/5432/5672       | Stop it, or change the host port in `docker-compose.yml` / `.env`               |
| Postgres container exits immediately | Empty `POSTGRES_*` — no `.env`                    | `cp .env.example .env`, then `docker compose up -d`                             |
| Workers restart in a loop            | They start before `migrate` / RabbitMQ is healthy | Usually self-heals (`restart: on-failure`); check `docker compose logs migrate` |
| UI loads but shows no data / errors  | API not reachable                                 | Confirm `server` is up: `docker compose ps`, `docker compose logs server`       |

More in [troubleshooting.md](troubleshooting.md).
