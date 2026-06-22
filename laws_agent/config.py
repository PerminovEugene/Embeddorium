import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name!r} is not set")
    return value


# HuggingFace. Optional: only used by hg_client, which already no-ops when unset,
# so DB-only entrypoints (e.g. migrations) don't need a token.
HG_TOKEN: str = os.getenv("HG_TOKEN", "")

# PostgreSQL
SQL_USER: str = _require("POSTGRES_USER")
SQL_PASSWORD: str = _require("POSTGRES_PASSWORD")
SQL_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
SQL_PORT: str = os.getenv("POSTGRES_PORT", "5432")
SQL_DATABASE: str = _require("POSTGRES_DB")

# Qdrant
QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")

# Domains explicitly allowed to skip TLS verification (comma-separated).
# Empty by default — TLS is verified everywhere unless a domain is listed here.
INSECURE_TLS_DOMAINS: frozenset[str] = frozenset(
    d.strip().lower()
    for d in os.getenv("INSECURE_TLS_DOMAINS", "").split(",")
    if d.strip()
)

# RabbitMQ
RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT: str = os.getenv("RABBITMQ_PORT", "5672")
RABBITMQ_USER: str = _require("RABBITMQ_USER")
RABBITMQ_PASSWORD: str = _require("RABBITMQ_PASSWORD")
RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST", "/")