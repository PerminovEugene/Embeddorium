# Installation

The supported all-in-one development runtime is Docker Compose.

## Prerequisites

- Git
- Docker Engine or Docker Desktop with Compose v2 (`docker compose`)
- Free host ports `5173`, `8000`, `6333`, `6334`, `5432`, `5672`, and `15672`
  (`5173` and `8000` are overridable via `UI_PORT` / `SERVER_PORT` in `.env`)

Python and Node are not required for this path because the services run in
containers.

## Clone and configure

```sh
git clone https://github.com/PerminovEugene/web-knoweladge-indexer.git embeddorium
cd embeddorium
cat > .env <<'EOF'
POSTGRES_USER=embeddorium_user
POSTGRES_PASSWORD=embeddorium_pass
POSTGRES_DB=embeddorium_db
POSTGRES_PORT=5432
RABBITMQ_USER=embeddorium_user2
RABBITMQ_PASSWORD=embeddorium_pass2
RABBITMQ_PORT=5672
RABBITMQ_MANAGEMENT_PORT=15672
RABBITMQ_VHOST=/
SERVER_PORT=8000
UI_PORT=5173
EOF
```

Compose reads `.env` for Postgres and RabbitMQ credentials and port
interpolation — the variables above are the complete set it interpolates.
Containers load `.env.docker`, which uses Compose service names such as
`postgres`, `rabbitmq`, and `qdrant`; don't copy it over `.env`, since those
hostnames don't resolve outside the stack.

## Start the stack

```sh
docker compose up -d --build
docker compose ps
```

The one-shot `migrate` service runs SQL migrations before the workers start.
Open <http://localhost:5173> when the `server` and `ui` services are running.

## Stop or remove it

```sh
docker compose down
```

To also delete Postgres, Qdrant, and RabbitMQ volumes:

```sh
docker compose down -v
```

For a host-side Python development environment, use
[Development setup](../development/setup.md).
