#!/usr/bin/env python3
"""Command line interface for the espresso log.

Examples:
    python3 src/log_shot.py init
    python3 src/log_shot.py add-bean                 # interactive
    python3 src/log_shot.py add-shot --bean-id 1 --dose-g 18 --yield-g 36
    python3 src/log_shot.py list-shots --limit 5

Any value not passed as a flag is asked for interactively, which is the
usual case when logging a shot right after pulling it.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import date
from pathlib import Path

# Allow running this file directly (python3 src/log_shot.py) by making the
# src/ directory importable, so "import db" resolves.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from db import DB_PATH, get_connection, init_db  # noqa: E402


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------

def ask(prompt: str, cast=str, default=None, required: bool = False):
    """Ask for one value until the input is valid.

    Returns None for optional fields left empty. When there is no terminal
    attached (piped input, CI, a shell script), nothing is asked: the default
    is used and optional fields stay empty, so the command stays scriptable.
    """
    if not sys.stdin.isatty():
        if default is not None:
            return default
        if required:
            print(f"Missing required value: {prompt}. Pass it as a flag.",
                  file=sys.stderr)
            raise SystemExit(2)
        return None

    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"{prompt}{suffix}: ").strip()

        if not raw:
            if default is not None:
                return default
            if required:
                print("  This field is required.")
                continue
            return None

        try:
            return cast(raw)
        except ValueError:
            print(f"  Could not read that as {cast.__name__}, try again.")


def valid_date(raw: str) -> str:
    """Accept YYYY-MM-DD only, so dates sort and compare correctly in SQL."""
    date.fromisoformat(raw)  # raises ValueError if malformed
    return raw


def fill(value, prompt: str, cast=str, default=None, required: bool = False):
    """Keep a value passed as a flag, otherwise ask for it."""
    return value if value is not None else ask(prompt, cast, default, required)


def print_table(rows: list[sqlite3.Row], columns: list[str]) -> None:
    """Print query results as an aligned text table."""
    if not rows:
        print("(no rows yet)")
        return

    cells = [[("" if r[c] is None else str(r[c])) for c in columns] for r in rows]
    widths = [
        max(len(col), *(len(row[i]) for row in cells))
        for i, col in enumerate(columns)
    ]

    header = "  ".join(col.ljust(widths[i]) for i, col in enumerate(columns))
    print(header)
    print("  ".join("-" * w for w in widths))
    for row in cells:
        print("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_init(args: argparse.Namespace) -> int:
    path = init_db()
    print(f"Database ready at {path}")
    return 0


def cmd_add_bean(args: argparse.Namespace) -> int:
    name = fill(args.name, "Bean name", required=True)
    roaster = fill(args.roaster, "Roaster")
    roast_date = fill(args.roast_date, "Roast date (YYYY-MM-DD)", valid_date)
    notes = fill(args.notes, "Notes")

    with get_connection() as connection:
        # Values are passed as parameters (the ? placeholders) rather than
        # formatted into the string — this is what prevents SQL injection.
        cursor = connection.execute(
            "INSERT INTO beans (name, roaster, roast_date, notes) "
            "VALUES (?, ?, ?, ?)",
            (name, roaster, roast_date, notes),
        )

    print(f"Added bean #{cursor.lastrowid}: {name}")
    return 0


def cmd_add_shot(args: argparse.Namespace) -> int:
    with get_connection() as connection:
        beans = connection.execute(
            "SELECT id, name, roaster FROM beans ORDER BY id"
        ).fetchall()

    if not beans:
        print("No beans yet — add one first with: log_shot.py add-bean")
        return 1

    if args.bean_id is None:
        print("Beans:")
        print_table(beans, ["id", "name", "roaster"])

    bean_id = fill(args.bean_id, "Bean id", int, required=True)
    shot_date = fill(args.date, "Shot date (YYYY-MM-DD)", valid_date,
                     default=date.today().isoformat())
    dose_g = fill(args.dose_g, "Dose in g", float, required=True)
    grind = fill(args.grind, "Grind setting", float)
    seconds = fill(args.time_s, "Extraction time in s", int)
    yield_g = fill(args.yield_g, "Yield in g", float)
    temp_c = fill(args.temp_c, "Water temperature in C", float)
    rating = fill(args.rating, "Taste rating 1-5", int)
    taste_notes = fill(args.notes, "Taste notes")

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                "INSERT INTO shots (bean_id, shot_date, dose_g, grind_setting,"
                " extraction_time_s, yield_g, water_temp_c, taste_rating,"
                " taste_notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (bean_id, shot_date, dose_g, grind, seconds, yield_g,
                 temp_c, rating, taste_notes),
            )
    except sqlite3.IntegrityError as error:
        # Raised when a CHECK or FOREIGN KEY constraint rejects the row.
        print(f"Rejected by the database: {error}", file=sys.stderr)
        return 1

    print(f"Added shot #{cursor.lastrowid}")
    if yield_g is not None:
        print(f"Brew ratio: 1:{yield_g / dose_g:.2f}")
    return 0


def cmd_list_beans(args: argparse.Namespace) -> int:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT b.id, b.name, b.roaster, b.roast_date,"
            "       COUNT(s.id) AS shots"
            "  FROM beans AS b"
            "  LEFT JOIN shots AS s ON s.bean_id = b.id"
            " GROUP BY b.id"
            " ORDER BY b.id"
        ).fetchall()

    print_table(rows, ["id", "name", "roaster", "roast_date", "shots"])
    return 0


def cmd_list_shots(args: argparse.Namespace) -> int:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, shot_date, bean_name, dose_g, yield_g, brew_ratio,"
            "       grind_setting, extraction_time_s, taste_rating"
            "  FROM v_shot_details"
            " ORDER BY shot_date DESC, id DESC"
            " LIMIT ?",
            (args.limit,),
        ).fetchall()

    print_table(rows, ["id", "shot_date", "bean_name", "dose_g", "yield_g",
                       "brew_ratio", "grind_setting", "extraction_time_s",
                       "taste_rating"])
    return 0


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="log_shot.py",
        description="Log and inspect espresso shots.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init", help="create the database and its tables")
    init_parser.set_defaults(func=cmd_init)

    bean_parser = subparsers.add_parser("add-bean", help="add a bag of coffee")
    bean_parser.add_argument("--name")
    bean_parser.add_argument("--roaster")
    bean_parser.add_argument("--roast-date", dest="roast_date")
    bean_parser.add_argument("--notes")
    bean_parser.set_defaults(func=cmd_add_bean)

    shot_parser = subparsers.add_parser("add-shot", help="add an espresso shot")
    shot_parser.add_argument("--bean-id", dest="bean_id", type=int)
    shot_parser.add_argument("--date")
    shot_parser.add_argument("--dose-g", dest="dose_g", type=float)
    shot_parser.add_argument("--grind", type=float, help="grinder setting")
    shot_parser.add_argument("--time-s", dest="time_s", type=int)
    shot_parser.add_argument("--yield-g", dest="yield_g", type=float)
    shot_parser.add_argument("--temp-c", dest="temp_c", type=float)
    shot_parser.add_argument("--rating", type=int, help="taste rating 1-5")
    shot_parser.add_argument("--notes")
    shot_parser.set_defaults(func=cmd_add_shot)

    beans_list_parser = subparsers.add_parser(
        "list-beans", help="show all beans and their shot counts")
    beans_list_parser.set_defaults(func=cmd_list_beans)

    shots_list_parser = subparsers.add_parser(
        "list-shots", help="show the most recent shots")
    shots_list_parser.add_argument("--limit", type=int, default=10)
    shots_list_parser.set_defaults(func=cmd_list_shots)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command != "init" and not DB_PATH.exists():
        print(f"No database at {DB_PATH}. Run: log_shot.py init",
              file=sys.stderr)
        return 1

    try:
        return args.func(args)
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
