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

from backend.shared.logging_config import configure_logging
from backend.shared.storage.sql.sql_store import SqlStore

logger = logging.getLogger(__name__)


def main() -> None:
    configure_logging()
    with SqlStore() as store:
        applied = store.run_migrations()
        logger.info("migrations applied count=%d files=%s", len(applied), applied)


if __name__ == "__main__":
    main()
