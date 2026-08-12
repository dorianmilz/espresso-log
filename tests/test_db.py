"""src/db.py — the settings every other module depends on."""

from __future__ import annotations

from pathlib import Path

from db import get_connection, init_db


def test_init_db_creates_tables_indexes_and_view(db_path: Path):
    init_db(db_path)

    with get_connection(db_path) as connection:
        names = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master")
        }

    assert {
        "beans",
        "shots",
        "v_shot_details",
        "idx_shots_bean_id",
        "idx_shots_shot_date",
    } <= names


def test_init_db_is_idempotent(db_path: Path):
    """Running it twice must not fail — every statement uses IF NOT EXISTS."""
    init_db(db_path)
    init_db(db_path)

    with get_connection(db_path) as connection:
        beans = connection.execute("SELECT COUNT(*) AS n FROM beans").fetchone()

    assert beans["n"] == 0


def test_init_db_returns_the_path_it_used(db_path: Path):
    assert init_db(db_path) == db_path


def test_get_connection_returns_rows_addressable_by_name(conn, bean_id):
    """row_factory = sqlite3.Row, so row["name"] works, not just row[0]."""
    row = conn.execute(
        "SELECT name, roaster FROM beans WHERE id = ?", (bean_id,)
    ).fetchone()

    assert row["name"] == "Test Bean"
    assert row["roaster"] == "Test Roaster"


def test_get_connection_enables_foreign_key_enforcement(conn):
    """SQLite defaults this to off, per connection — db.py turns it on."""
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_get_connection_creates_a_missing_parent_directory(tmp_path: Path):
    nested = tmp_path / "deeper" / "still" / "espresso.db"

    connection = get_connection(nested)
    connection.close()

    assert nested.parent.is_dir()
