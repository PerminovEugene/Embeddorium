import os
from typing import FrozenSet

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name!r} is not set")
    return value


# Embedding provider/model/endpoint are NOT global config: they are recorded
# per pipeline run in the run's actor_configs.embed_chunks.provider snapshot
# (written from the provider the user picked in the UI) and read back by
# backend.actors.embed_chunks_actor.launcher. Provider *form defaults* are
# env-sourced inside each provider-type plugin (OLLAMA_URL / OLLAMA_PORT /
# OPENAI_BASE_URL); see backend.plugins.provider_types._remote.env_default.

# Vite dev server port. Read here only to build the dev CORS allowlist in
# backend.server.main; the UI itself picks it up via ui/vite.config.ts.
UI_PORT: int = int(os.getenv("UI_PORT", "5173"))

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
