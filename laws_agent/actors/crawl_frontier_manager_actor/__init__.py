"""Crawl Frontier Manager actor package.

Re-exports the public symbols so this package can still be referenced as a
single module path, e.g. ``dramatiq laws_agent.actors.crawl_frontier_manager_actor``
(see docker-compose) and ``from laws_agent.actors.crawl_frontier_manager_actor
import handle`` in tests.
"""

from laws_agent.actors.crawl_frontier_manager_actor.handler import handle
from laws_agent.actors.crawl_frontier_manager_actor.url_helper import is_allowed_url
from laws_agent.actors.crawl_frontier_manager_actor.launcher import (
    manage_crawl_frontier,
    rabbitmq_broker,
    sql_store,
)

__all__ = [
    "handle",
    "is_allowed_url",
    "manage_crawl_frontier",
    "rabbitmq_broker",
    "sql_store",
]
