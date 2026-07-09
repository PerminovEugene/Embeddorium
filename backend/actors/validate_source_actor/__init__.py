"""Source Validator actor package (shared stage 0 of both ingestion chains).

Re-exports the public symbols so this package can be referenced as a single
module path, e.g. ``dramatiq backend.actors.validate_source_actor`` (see
docker-compose) and ``from backend.actors.validate_source_actor import
handle`` in tests.
"""

from backend.actors.validate_source_actor.handler import handle
from backend.actors.validate_source_actor.launcher import (
    rabbitmq_broker,
    sql_store,
    validate_source,
)

__all__ = [
    "handle",
    "validate_source",
    "rabbitmq_broker",
    "sql_store",
]
