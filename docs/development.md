# Development

## Environment

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The project is packaged with optional extras (see `pyproject.toml`), so for a
particular piece of work you can install just what you need — `web`, `embed`,
`embedding`, `server`, `mcp`, `agent`, or `dev`. For example:

```sh
pip install -e ".[dev]"          # tests, ruff, mypy
pip install -e ".[server,agent]" # API + chat agent
```

## Database migrations

Migrations are plain SQL files applied in order. The Compose `migrate` service
runs them on startup; to run them by hand:

```sh
python -m backend.shared.storage.sql.migrate
```

## Tests

```sh
.venv/bin/python -m pytest backend/tests -q
```

A single file:

```sh
.venv/bin/python -m pytest backend/tests/actors/test_parse_source_actor.py -v
```

## Formatting & linting

[Ruff](https://docs.astral.sh/ruff/) handles both:

```sh
ruff check .     # lint
ruff format .    # format
```

The codebase targets [PEP 8](https://peps.python.org/pep-0008/) and Python 3.11+.

## Dependencies

`requirements.txt` is the pinned lockfile; regenerate it after changing packages:

```sh
pip install <package>
pip freeze > requirements.txt
```

## Resetting local state

The `scripts/` folder has helpers for wiping the local stack between runs:

| Script | What it clears |
| ------ | -------------- |
| `scripts/clean-postgres.sh` | Postgres tables |
| `scripts/clean-qdrant.sh` | Qdrant collections |
| `scripts/purge-queues.sh` | RabbitMQ queues |
| `scripts/full-clean.sh` | All of the above |
| `scripts/rebuild-workers.sh` | Rebuild + restart the worker containers |
