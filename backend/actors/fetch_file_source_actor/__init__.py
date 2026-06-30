"""fetch_file_source actor package (local XML chain entry point).

Importable at ``backend.actors.fetch_file_source_actor`` so Dramatiq can
load it by module path and tests can import the pure ``fetch_file_source``
handler.
"""

from backend.actors.fetch_file_source_actor.handler import fetch_file_source
from backend.actors.fetch_file_source_actor.launcher import (
    fetch_file_source as fetch_file_source_actor,
    rabbitmq_broker,
    sql_store,
)

__all__ = [
    "fetch_file_source",
    "fetch_file_source_actor",
    "rabbitmq_broker",
    "sql_store",
]
