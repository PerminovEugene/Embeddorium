import os
from typing import FrozenSet

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name!r} is not set")
    return value


# Embedding provider used by the legacy env fallback (no pipeline_id). Only
# remote/API providers and the trivial mock are supported: "ollama" calls a
# remote Ollama server over HTTP (e.g. qwen3-embedding); "openai" calls an
# OpenAI-compatible API; "mock" returns random vectors instead, so the
# crawl/embed pipeline can be exercised quickly without any real model.
EMBED_PROVIDER: str = os.getenv("EMBED_PROVIDER", "ollama")

# Vector dimension used by the mock embedding provider. Defaults to 4096 (the
# Qwen/Qwen3-Embedding-8B dimension) so mock and real collections stay
# compatible by default.
MOCK_EMBED_DIM: int = int(os.getenv("MOCK_EMBED_DIM", "4096"))

# Ollama embeddings (EMBED_PROVIDER=ollama). This is the embedding pipeline's
# OWN Ollama endpoint — deliberately separate from the chat agent's
# OLLAMA_BASE_URL (backend.agent.config), because the embed worker runs in
# docker while the agent runs on the host, so they need different URLs.
# OLLAMA_EMBED_BASE_URL must be reachable from wherever the embed worker runs:
# - docker compose, Ollama as a compose service: http://ollama:11434
#   (the service name — not localhost; containers have their own loopback).
# - docker compose, Ollama on the host (Mac/Windows Docker Desktop):
#   http://host.docker.internal:11434
# - process running directly on the host: http://localhost:11434
OLLAMA_EMBED_BASE_URL: str = os.getenv(
    "OLLAMA_EMBED_BASE_URL", "http://localhost:11434"
)
OLLAMA_EMBED_MODEL: str = os.getenv("OLLAMA_EMBED_MODEL", "qwen3-embedding")

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
INSECURE_TLS_DOMAINS: FrozenSet[str] = frozenset(
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

# Per-URL file logging. Base directory holding one nested folder + log file
# per crawl target (see backend.shared.log_routing).
LOG_DIR: str = os.getenv("LOG_DIR", "logs")

# Per-pipeline-run log root. When a pipeline_id is active, actor logs land
# under <PIPELINE_RUNS_DIR>/<pipeline_id>/logs/ with the same nested per-URL
# structure as LOG_DIR. Defaults to /tmp/pipeline_runs so run logs are
# transient and don't fill persistent storage.
PIPELINE_RUNS_DIR: str = os.getenv("PIPELINE_RUNS_DIR", "/tmp/pipeline_runs")

# JSON plugin output limits. Structured data is rejected, never truncated.
PARSER_METADATA_MAX_BYTES: int = int(os.getenv("PARSER_METADATA_MAX_BYTES", "262144"))
PARSER_INTERMEDIATE_MAX_BYTES: int = int(
    os.getenv("PARSER_INTERMEDIATE_MAX_BYTES", "8388608")
)
CHUNK_METADATA_MAX_BYTES: int = int(os.getenv("CHUNK_METADATA_MAX_BYTES", "262144"))
