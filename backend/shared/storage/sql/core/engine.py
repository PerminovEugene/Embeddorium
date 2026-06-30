from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import (
    create_engine,
)
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

from backend.shared import config


@dataclass(frozen=True)
class SqlPoolConfig:
    """Per-process connection-pool sizing for one ``SqlStore``/engine.

    Each dramatiq worker pins ``--processes 1 --threads 4`` (see
    docker-compose.yml); without those overrides dramatiq would default to one
    process per CPU core and 8 threads each, making connection counts depend on
    host CPU count. Every process imports its actor launcher module once, which
    builds exactly one engine/pool — but that pool is then shared by all 4
    threads in that process. Keep ``pool_size`` small (threads queue for a
    connection rather than each holding one permanently) and keep
    ``max_overflow`` small too, so that
    ``total_connections ~= workers * processes_per_worker * (pool_size +
    max_overflow)`` stays comfortably under Postgres's default
    ``max_connections`` (100) even when every worker is busy at once.
    """

    pool_size: int = 2
    max_overflow: int = 3
    pool_timeout: float = 30.0
    # Recycle connections that the server may have already dropped (e.g. after
    # a network blip or idle timeout) instead of surfacing a stale-connection
    # error on the next checkout.
    pool_pre_ping: bool = True


# Conservative default shared by callers that don't need a custom pool size.
DEFAULT_POOL_CONFIG = SqlPoolConfig()


def build_dsn() -> str:
    return (
        f"postgresql+psycopg2://{config.SQL_USER}:{config.SQL_PASSWORD}"
        f"@{config.SQL_HOST}:{config.SQL_PORT}"
        f"/{config.SQL_DATABASE}"
    )


def create_sql_engine(
    dsn: str | None = None,
    *,
    pool_config: SqlPoolConfig | None = None,
    application_name: str | None = None,
) -> Engine:
    """Build a SQLAlchemy engine with an explicit, bounded connection pool.

    ``application_name`` is forwarded to psycopg2 so each actor's connections
    are identifiable in ``pg_stat_activity`` (otherwise every connection shows
    up anonymously, which makes "too many clients" incidents hard to debug).
    """
    pool_config = pool_config or DEFAULT_POOL_CONFIG
    connect_args = (
        {"application_name": application_name} if application_name else {}
    )

    return create_engine(
        dsn or build_dsn(),
        poolclass=QueuePool,
        pool_size=pool_config.pool_size,
        max_overflow=pool_config.max_overflow,
        pool_timeout=pool_config.pool_timeout,
        pool_pre_ping=pool_config.pool_pre_ping,
        connect_args=connect_args,
    )
