"""The database rejects invalid data on its own.

These tests write straight to SQLite, bypassing the CLI, so they prove the
CHECK and FOREIGN KEY constraints in schema.sql hold no matter which client
inserts the row.
"""

from __future__ import annotations

import sqlite3

import pytest

# A shot that violates nothing. Individual tests override one field at a time.
VALID_SHOT = {
    "shot_date": "2026-08-01",
    "dose_g": 18.0,
    "grind_setting": 3.5,
    "extraction_time_s": 28,
    "yield_g": 36.0,
    "water_temp_c": 93.0,
    "taste_rating": 4,
}


def insert_shot(conn, bean_id: int, **overrides):
    """Insert a shot, replacing individual fields of VALID_SHOT."""
    values = {**VALID_SHOT, "bean_id": bean_id, **overrides}

    # The column names come from this module, never from user input; the
    # values themselves still go through ? placeholders.
    columns = ", ".join(values)
    placeholders = ", ".join("?" * len(values))

    cursor = conn.execute(
        f"INSERT INTO shots ({columns}) VALUES ({placeholders})",
        tuple(values.values()),
    )
    conn.commit()
    return cursor.lastrowid


# ---------------------------------------------------------------------------
# CHECK constraints — accepted
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "column, value",
    [
        ("dose_g", 18.0),
        ("dose_g", 0.1),
        ("extraction_time_s", 28),
        ("extraction_time_s", 1),
        ("grind_setting", 3.5),
        ("grind_setting", 0.5),
        ("yield_g", 36.0),
        ("taste_rating", 1),
        ("taste_rating", 3),
        ("taste_rating", 5),
    ],
)
def test_valid_value_is_accepted(conn, bean_id, column, value):
    shot_id = insert_shot(conn, bean_id, **{column: value})

    stored = conn.execute(
        "SELECT * FROM shots WHERE id = ?", (shot_id,)
    ).fetchone()
    assert stored[column] == value


# ---------------------------------------------------------------------------
# CHECK constraints — rejected
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "column, value",
    [
        ("dose_g", 0),
        ("dose_g", -1),
        ("extraction_time_s", 0),
        ("extraction_time_s", -5),
        ("grind_setting", 0),
        ("grind_setting", -1),
        ("yield_g", -0.1),
        ("taste_rating", 0),
        ("taste_rating", 6),
    ],
)
def test_invalid_value_is_rejected(conn, bean_id, column, value):
    with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
        insert_shot(conn, bean_id, **{column: value})


def test_zero_yield_is_accepted(conn, bean_id):
    """A choked shot that delivers nothing is a real, recordable result.

    This is the reason the constraint reads `yield_g >= 0` and not `> 0`.
    Tightening it would silently make failed shots impossible to log.
    """
    shot_id = insert_shot(conn, bean_id, yield_g=0.0, taste_rating=1)

    stored = conn.execute(
        "SELECT yield_g FROM shots WHERE id = ?", (shot_id,)
    ).fetchone()
    assert stored["yield_g"] == 0.0


# ---------------------------------------------------------------------------
# Foreign key
# ---------------------------------------------------------------------------

def test_shot_for_an_existing_bean_is_accepted(conn, bean_id):
    shot_id = insert_shot(conn, bean_id)

    stored = conn.execute(
        "SELECT bean_id FROM shots WHERE id = ?", (shot_id,)
    ).fetchone()
    assert stored["bean_id"] == bean_id


def test_shot_for_an_unknown_bean_is_rejected(conn, bean_id):
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        insert_shot(conn, 999)
