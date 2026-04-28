from __future__ import annotations

from sqlalchemy import (
    create_engine,
)
from sqlalchemy.pool import QueuePool

from laws_agent import config

def build_dsn() -> str:
    return (
        f"postgresql+psycopg2://{config.SQL_USER}:{config.SQL_PASSWORD}"
        f"@{config.SQL_HOST}:{config.SQL_PORT}"
        f"/{config.SQL_DATABASE}"
    )

def create_sql_engine(dsn: str | None = None):
    return create_engine(
        dsn or build_dsn(),
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
    )