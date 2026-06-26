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

# Embedding provider. "huggingface" loads the real (slow) SentenceTransformer
# model; "mock" returns random vectors instead, so the crawl/embed pipeline can
# be exercised quickly without loading any model.
EMBED_PROVIDER: str = os.getenv("EMBED_PROVIDER", "huggingface")

# Vector dimension used by the mock embedding provider. Defaults to the real
# model's dimension (Qwen/Qwen3-Embedding-8B = 4096) so mock and real
# collections stay compatible by default.
MOCK_EMBED_DIM: int = int(os.getenv("MOCK_EMBED_DIM", "4096"))

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

# Per-URL file logging. Base directory holding one nested folder + log file
# per crawl target (see laws_agent.log_routing).
LOG_DIR: str = os.getenv("LOG_DIR", "logs")