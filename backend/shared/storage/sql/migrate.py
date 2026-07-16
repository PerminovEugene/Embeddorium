"""Migration entrypoint.

Applies every pending SQL migration to the configured Postgres database.
Run as a one-off command before starting the workers:

    python -m backend.shared.storage.sql.migrate

All migrations are written with ``IF NOT EXISTS`` guards, so this is safe to
run repeatedly (e.g. on every deploy or container start) without erroring on
already-applied schema objects.
"""

from __future__ import annotations

import logging
import time

from sqlalchemy.exc import OperationalError

from backend.shared.logging_config import configure_logging
from backend.shared.storage.sql.sql_store import SqlStore

logger = logging.getLogger(__name__)

_MAX_DATABASE_ATTEMPTS = 60
_DATABASE_RETRY_DELAY_SECONDS = 1.0


def run_when_database_ready() -> list[str]:
    """Run migrations, retrying while PostgreSQL is still starting."""
    for attempt in range(1, _MAX_DATABASE_ATTEMPTS + 1):
        try:
            with SqlStore() as store:
                return store.run_migrations()
        except OperationalError:
            if attempt == _MAX_DATABASE_ATTEMPTS:
                raise
            logger.info(
                "database not ready; retrying migration attempt=%d/%d",
                attempt,
                _MAX_DATABASE_ATTEMPTS,
            )
            time.sleep(_DATABASE_RETRY_DELAY_SECONDS)

    raise RuntimeError("unreachable")


def main() -> None:
    configure_logging()
    applied = run_when_database_ready()
    logger.info("migrations applied count=%d files=%s", len(applied), applied)


if __name__ == "__main__":
    main()
