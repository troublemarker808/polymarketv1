import sqlite3
from pathlib import Path

from pm_bot.storage.schema import DDL, SCHEMA_VERSION, SNAPSHOT_VERSION


def connect_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute("PRAGMA journal_mode = WAL;")
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(DDL)
    connection.execute(
        """
        INSERT INTO metadata(key, value) VALUES('schema_version', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (str(SCHEMA_VERSION),),
    )
    connection.execute(
        """
        INSERT INTO metadata(key, value) VALUES('snapshot_version', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (str(SNAPSHOT_VERSION),),
    )
    connection.commit()


def read_metadata_value(connection: sqlite3.Connection, key: str) -> str | None:
    row = connection.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return str(row["value"])
    return str(row[0])


def require_supported_versions(connection: sqlite3.Connection) -> None:
    schema_value = read_metadata_value(connection, "schema_version")
    snapshot_value = read_metadata_value(connection, "snapshot_version")

    if schema_value != str(SCHEMA_VERSION):
        msg = f"Unsupported schema version: expected {SCHEMA_VERSION}, got {schema_value}"
        raise RuntimeError(msg)

    if snapshot_value != str(SNAPSHOT_VERSION):
        msg = f"Unsupported snapshot version: expected {SNAPSHOT_VERSION}, got {snapshot_value}"
        raise RuntimeError(msg)
