"""Shared fixtures for the test suite.

Every test runs against its own database in a temporary directory, so the
real data/espresso.db is never touched.

Two ways of pointing the code at that temporary database are used, because
db.py resolves DB_PATH once at import time:

- CLI tests start a new process, so the ESPRESSO_DB environment variable
  works exactly as intended (see the run_cli fixture).
- In-process tests pass the path directly to get_connection() / init_db(),
  which both accept a db_path argument for this purpose.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
CLI = SRC / "log_shot.py"

# Make the project's own modules importable, the same way log_shot.py does.
sys.path.insert(0, str(SRC))

from db import get_connection, init_db  # noqa: E402


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Path to a database file that does not exist yet."""
    return tmp_path / "espresso.db"


@pytest.fixture
def db(db_path: Path) -> Path:
    """The same path, with the schema already applied."""
    init_db(db_path)
    return db_path


@pytest.fixture
def conn(db: Path):
    """An open connection to an initialised, empty database."""
    connection = get_connection(db)
    yield connection
    connection.close()


@pytest.fixture
def bean_id(conn) -> int:
    """Insert one bean and return its id, for shots to refer to."""
    cursor = conn.execute(
        "INSERT INTO beans (name, roaster, roast_date) VALUES (?, ?, ?)",
        ("Test Bean", "Test Roaster", "2026-07-01"),
    )
    conn.commit()
    return cursor.lastrowid


@pytest.fixture
def run_cli(db_path: Path):
    """Run log_shot.py as a real subprocess against the temporary database.

    Testing through the command line rather than by importing the functions
    means the argument parsing, the exit codes and the printed output are
    covered too.
    """
    def run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            capture_output=True,
            text=True,
            cwd=ROOT,
            # sys.executable keeps the tests on the same interpreter as the
            # virtual environment they were started from.
            env={**os.environ, "ESPRESSO_DB": str(db_path)},
        )

    return run
