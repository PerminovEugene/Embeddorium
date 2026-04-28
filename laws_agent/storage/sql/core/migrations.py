from pathlib import Path

from sqlalchemy import text as sql_text
from sqlalchemy.engine import Engine

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def run_migrations(engine: Engine) -> list[str]:
    migration_files = sorted(_MIGRATIONS_DIR.glob("*.sql"))

    with engine.begin() as conn:
        for migration_file in migration_files:
            conn.execute(sql_text(migration_file.read_text()))

    return [migration_file.name for migration_file in migration_files]