"""The database rejects invalid data on its own.

These tests write straight to SQLite, bypassing the CLI, so they prove the
CHECK and FOREIGN KEY constraints in schema.sql hold no matter which client
inserts the row.
"""

from __future__ import annotations

import sqlite3

import pytest

from db import TASTE_NOTES, WATER_TEMPS_C

# A shot that violates nothing. Individual tests override one field at a time.
VALID_SHOT = {
    "shot_date": "2026-08-01",
    "dose_g": 18.0,
    "grind_setting": 3.5,
    "extraction_time_s": 28,
    "yield_g": 36.0,
    "water_temp_c": 94.0,
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
# Controlled vocabularies
#
# These parametrise over the constants in db.py rather than over a second
# hand-written list. If db.py and schema.sql ever disagree, a value here will
# be rejected by the database and the test turns red — the copy in Python
# cannot drift away from the schema unnoticed.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("temperature", WATER_TEMPS_C)
def test_every_offered_water_temperature_is_accepted(conn, bean_id,
                                                     temperature):
    shot_id = insert_shot(conn, bean_id, water_temp_c=temperature)

    stored = conn.execute(
        "SELECT water_temp_c FROM shots WHERE id = ?", (shot_id,)
    ).fetchone()
    assert stored["water_temp_c"] == temperature


@pytest.mark.parametrize("temperature", [93.0, 90.0, 100.0])
def test_other_water_temperatures_are_rejected(conn, bean_id, temperature):
    """The machine has three settings; anything else is a typo."""
    with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
        insert_shot(conn, bean_id, water_temp_c=temperature)


@pytest.mark.parametrize("note", TASTE_NOTES)
def test_every_offered_taste_note_is_accepted(conn, bean_id, note):
    shot_id = insert_shot(conn, bean_id, taste_notes=note)

    stored = conn.execute(
        "SELECT taste_notes FROM shots WHERE id = ?", (shot_id,)
    ).fetchone()
    assert stored["taste_notes"] == note


@pytest.mark.parametrize(
    "note",
    ["a bit sour", "balanced", "BALANCED", "Very  Sour", ""],
)
def test_free_text_taste_notes_are_rejected(conn, bean_id, note):
    """Including near misses: the spelling has to match exactly."""
    with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
        insert_shot(conn, bean_id, taste_notes=note)


@pytest.mark.parametrize(
    "retired_note",
    ["Chocolatey & Cocoa", "Nutty & Toasty", "Sweet & Caramelized"],
)
def test_retired_flavour_categories_are_rejected(conn, bean_id, retired_note):
    """taste_notes used to hold eight flavour categories.

    They were replaced by the extraction balance scale, not extended by it.
    This test proves the swap actually took effect: a value from the old
    list must no longer be accepted.
    """
    with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
        insert_shot(conn, bean_id, taste_notes=retired_note)


@pytest.mark.parametrize("column", ["water_temp_c", "taste_notes"])
def test_restricted_columns_still_accept_null(conn, bean_id, column):
    """Both columns stay optional despite their fixed value lists.

    A CHECK rejects a row only when the expression is FALSE. `NULL IN (...)`
    is NULL rather than false, so an empty field passes — no extra
    `OR ... IS NULL` needed in the schema.
    """
    shot_id = insert_shot(conn, bean_id, **{column: None})

    stored = conn.execute(
        f"SELECT {column} FROM shots WHERE id = ?", (shot_id,)
    ).fetchone()
    assert stored[column] is None


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
