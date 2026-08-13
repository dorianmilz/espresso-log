"""src/log_shot.py driven through the command line.

These tests start the script as a real subprocess instead of importing its
functions, so the argument parsing, the exit codes and the printed output
are covered as well.

Exit codes used by the CLI:
    0   success
    1   rejected by the database, or no database / no beans yet
    2   a required value was missing and no terminal was attached
"""

from __future__ import annotations

import sqlite3

import pytest

from db import TASTE_NOTES

# Every field the CLI treats as required, with valid values. Rejection tests
# override exactly one of them, so the command reaches the database instead
# of stopping early at "missing required value" (exit code 2).
VALID_SHOT_ARGS = [
    "--dose-g", "18",
    "--grind", "3.5",
    "--time-s", "29",
    "--yield-g", "36",
    "--rating", "4",
    "--date", "2026-08-01",
]


@pytest.fixture
def cli(run_cli):
    """run_cli against an initialised but empty database."""
    assert run_cli("init").returncode == 0
    return run_cli


@pytest.fixture
def cli_with_bean(cli):
    """run_cli against a database that already holds bean #1."""
    result = cli("add-bean", "--name", "Test Bean",
                 "--roaster", "Test Roaster", "--roast-date", "2026-07-01")
    assert result.returncode == 0
    return cli


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

def test_init_creates_the_database_file(run_cli, db_path):
    result = run_cli("init")

    assert result.returncode == 0
    assert db_path.exists()


def test_commands_without_a_database_explain_what_to_do(run_cli):
    result = run_cli("list-beans")

    assert result.returncode == 1
    assert "log_shot.py init" in result.stderr


# ---------------------------------------------------------------------------
# add-bean / add-shot
# ---------------------------------------------------------------------------

def test_add_bean_reports_the_new_id(cli):
    result = cli("add-bean", "--name", "Ethiopia Sidamo",
                 "--roaster", "Roesterei Vier", "--roast-date", "2026-07-01")

    assert result.returncode == 0
    assert "Added bean #1" in result.stdout


def test_add_shot_reports_the_brew_ratio(cli_with_bean):
    result = cli_with_bean("add-shot", "--bean-id", "1", *VALID_SHOT_ARGS)

    assert result.returncode == 0
    assert "Added shot #1" in result.stdout
    # 36 g out of 18 g in.
    assert "Brew ratio: 1:2.00" in result.stdout


def test_add_shot_without_any_beans_points_at_add_bean(cli):
    result = cli("add-shot", "--bean-id", "1", *VALID_SHOT_ARGS)

    assert result.returncode == 1
    assert "add-bean" in result.stdout


def test_add_shot_missing_a_required_value_exits_with_2(cli_with_bean):
    """No --dose-g and no terminal attached: fail instead of prompting."""
    result = cli_with_bean("add-shot", "--bean-id", "1", "--rating", "4")

    assert result.returncode == 2
    assert "Missing required value" in result.stderr


# ---------------------------------------------------------------------------
# add-shot — rejected by the database
# ---------------------------------------------------------------------------

def test_add_shot_with_an_invalid_rating_is_rejected(cli_with_bean):
    args = [a if a != "4" else "9" for a in VALID_SHOT_ARGS]
    result = cli_with_bean("add-shot", "--bean-id", "1", *args)

    assert result.returncode == 1
    assert "CHECK constraint failed" in result.stderr
    assert "taste_rating" in result.stderr


def test_add_shot_with_a_zero_dose_is_rejected(cli_with_bean):
    args = [a if a != "18" else "0" for a in VALID_SHOT_ARGS]
    result = cli_with_bean("add-shot", "--bean-id", "1", *args)

    assert result.returncode == 1
    assert "CHECK constraint failed" in result.stderr
    assert "dose_g" in result.stderr


def test_add_shot_for_an_unknown_bean_is_rejected(cli_with_bean):
    result = cli_with_bean("add-shot", "--bean-id", "999", *VALID_SHOT_ARGS)

    assert result.returncode == 1
    assert "FOREIGN KEY constraint failed" in result.stderr


def test_add_shot_with_zero_yield_is_accepted(cli_with_bean):
    """The choked-shot case: 0 g out is a result, not an input error."""
    args = [a if a != "36" else "0" for a in VALID_SHOT_ARGS]
    result = cli_with_bean("add-shot", "--bean-id", "1", *args)

    assert result.returncode == 0
    assert "Added shot #1" in result.stdout


# ---------------------------------------------------------------------------
# Controlled vocabularies on the command line
# ---------------------------------------------------------------------------

def test_offered_water_temperature_is_stored(cli_with_bean, db_path):
    result = cli_with_bean("add-shot", "--bean-id", "1", "--temp-c", "94",
                           *VALID_SHOT_ARGS)

    assert result.returncode == 0

    with sqlite3.connect(db_path) as connection:
        stored = connection.execute("SELECT water_temp_c FROM shots").fetchone()
    assert stored[0] == 94.0


def test_other_water_temperature_is_refused_by_the_parser(cli_with_bean):
    """argparse rejects it before the database is even opened."""
    result = cli_with_bean("add-shot", "--bean-id", "1", "--temp-c", "93",
                           *VALID_SHOT_ARGS)

    assert result.returncode == 2
    assert "invalid choice" in result.stderr


def test_notes_flag_takes_a_number_and_stores_the_label(cli_with_bean,
                                                        db_path):
    """--notes 7 is the seventh entry of TASTE_NOTES, not the literal "7"."""
    result = cli_with_bean("add-shot", "--bean-id", "1", "--notes", "7",
                           *VALID_SHOT_ARGS)

    assert result.returncode == 0

    with sqlite3.connect(db_path) as connection:
        stored = connection.execute("SELECT taste_notes FROM shots").fetchone()
    assert stored[0] == TASTE_NOTES[6] == "Sweet & Caramelized"


# ---------------------------------------------------------------------------
# list-beans / list-shots
# ---------------------------------------------------------------------------

def test_list_beans_shows_the_bean_and_its_shot_count(cli_with_bean):
    cli_with_bean("add-shot", "--bean-id", "1", *VALID_SHOT_ARGS)

    result = cli_with_bean("list-beans")

    assert result.returncode == 0
    assert "Test Bean" in result.stdout
    # Header, separator, one bean row.
    assert len(result.stdout.strip().splitlines()) == 3


def test_list_beans_on_an_empty_database_says_so(cli):
    result = cli("list-beans")

    assert result.returncode == 0
    assert "no rows yet" in result.stdout


def test_list_shots_respects_the_limit(cli_with_bean):
    for _ in range(3):
        cli_with_bean("add-shot", "--bean-id", "1", *VALID_SHOT_ARGS)

    result = cli_with_bean("list-shots", "--limit", "2")

    assert result.returncode == 0
    # Header, separator, two shot rows.
    assert len(result.stdout.strip().splitlines()) == 4
