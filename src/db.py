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


# The values schema.sql accepts for the two restricted columns. Both the CLI
# and the Streamlit page build their menus from these, so the lists exist
# once rather than twice. schema.sql stays the authority — tests insert every
# value below, so a list that drifts away from the schema fails the suite.
WATER_TEMPS_C = (92.0, 94.0, 96.0)

TEMP_LABELS = {92.0: "Low", 94.0: "Middle", 96.0: "High"}

TASTE_NOTES = (
    "Chocolatey & Cocoa",
    "Nutty & Toasty",
    "Fruity-Sweet",
    "Citrusy & Zesty",
    "Floral & Tea-like",
    "Spicy & Earthy",
    "Sweet & Caramelized",
    "Balanced & Mild",
)


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
