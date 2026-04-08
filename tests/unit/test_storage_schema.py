import sqlite3

import pytest

from pm_bot.storage.db import initialize_database, require_supported_versions


def test_initialize_database_sets_required_versions() -> None:
    connection = sqlite3.connect(":memory:")
    initialize_database(connection)

    require_supported_versions(connection)


def test_snapshot_version_mismatch_is_rejected() -> None:
    connection = sqlite3.connect(":memory:")
    initialize_database(connection)
    connection.execute("UPDATE metadata SET value = '999' WHERE key = 'snapshot_version'")
    connection.commit()

    with pytest.raises(RuntimeError, match="Unsupported snapshot version"):
        require_supported_versions(connection)
