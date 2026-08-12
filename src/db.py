"""Database access for the espresso log.

Central place for the connection settings, so every other module gets a
connection that behaves identically.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

# Repository root — this file lives in <root>/src/db.py
ROOT = Path(__file__).resolve().parent.parent

SCHEMA_PATH = ROOT / "schema.sql"

# The database lives in data/, which is git-ignored. Override with the
# ESPRESSO_DB environment variable, e.g. to run against a throwaway copy.
DB_PATH = Path(os.environ.get("ESPRESSO_DB", ROOT / "data" / "espresso.db"))


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Return a connection with the settings this project relies on."""
    path = Path(db_path) if db_path is not None else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)

    # Rows become mapping-like: row["dose_g"] instead of row[3].
    connection.row_factory = sqlite3.Row

    # SQLite ships with foreign key enforcement switched off for backwards
    # compatibility, and the setting is per connection. Without this line
    # the REFERENCES clause in schema.sql would be documentation only.
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def init_db(db_path: Path | None = None) -> Path:
    """Create the tables, indexes and view. Safe to run repeatedly."""
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with get_connection(db_path) as connection:
        # executescript() runs a file containing several statements, unlike
        # execute(), which accepts exactly one.
        connection.executescript(schema_sql)

    return Path(db_path) if db_path is not None else DB_PATH
