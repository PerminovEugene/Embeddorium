#!/usr/bin/env python3
"""Run all pending SQL migrations against the configured database."""

import sys

from sqlalchemy.exc import OperationalError

from laws_agent import config
from laws_agent.storage.sql.sql_store import SqlStore


def main() -> None:
    dsn_display = (
        f"postgresql://{config.SQL_USER}@{config.SQL_HOST}:{config.SQL_PORT}"
        f"/{config.SQL_DATABASE}"
    )
    print(f"Connecting to {dsn_display}")

    try:
        with SqlStore() as store:
            applied = store.run_migrations()
    except OperationalError as exc:
        print(f"ERROR: could not connect to database — {exc.orig}", file=sys.stderr)
        sys.exit(1)

    if not applied:
        print("No migration files found.")
        return

    for name in applied:
        print(f"  ✓ {name}")
    print(f"\nApplied {len(applied)} migration(s).")


if __name__ == "__main__":
    main()
