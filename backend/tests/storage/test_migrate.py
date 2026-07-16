from unittest.mock import MagicMock, patch

from sqlalchemy.exc import OperationalError

from backend.shared.storage.sql.migrate import run_when_database_ready


def _not_ready() -> OperationalError:
    return OperationalError("connect", {}, Exception("database is starting"))


def test_migration_retries_until_database_is_ready() -> None:
    unavailable_store = MagicMock()
    unavailable_store.__enter__.return_value.run_migrations.side_effect = _not_ready()
    ready_store = MagicMock()
    ready_store.__enter__.return_value.run_migrations.return_value = ["001.sql"]

    with (
        patch(
            "backend.shared.storage.sql.migrate.SqlStore",
            side_effect=[unavailable_store, ready_store],
        ),
        patch("backend.shared.storage.sql.migrate.time.sleep") as sleep,
    ):
        assert run_when_database_ready() == ["001.sql"]

    sleep.assert_called_once_with(1.0)
