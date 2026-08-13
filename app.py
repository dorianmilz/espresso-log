"""Streamlit web interface for logging espresso shots.

Built for one job: logging a shot from a phone, seconds after pulling it,
with as little typing as possible. Bean, dose and grind setting are
pre-filled from the last shot, because in practice only the extraction
time and the rating change between two shots.

Run locally:
    streamlit run app.py

Reachable from a phone on the same network:
    streamlit run app.py --server.address 0.0.0.0

Database access goes through src/db.py, so this interface obeys exactly
the same connection settings as the CLI and the tests.
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import date
from pathlib import Path

import streamlit as st

# Make the project's own modules importable, the same way src/log_shot.py
# and tests/conftest.py do it.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from db import DB_PATH, get_connection  # noqa: E402

# Fallbacks for the very first shot, when there is nothing to copy from.
DEFAULT_DOSE_G = 18.0
DEFAULT_GRIND = 3.5
DEFAULT_TIME_S = 28
DEFAULT_YIELD_G = 36.0
DEFAULT_TEMP_C = 93.0


# ---------------------------------------------------------------------------
# Database helpers
#
# Streamlit re-runs this whole script on every interaction, sometimes on a
# different thread, and SQLite connections are bound to the thread that
# created them. So each helper opens its own short-lived connection instead
# of caching one — against a local file that costs practically nothing.
# ---------------------------------------------------------------------------

def fetch_beans() -> list[sqlite3.Row]:
    connection = get_connection()
    try:
        return connection.execute(
            "SELECT id, name, roaster FROM beans ORDER BY name"
        ).fetchall()
    finally:
        connection.close()


def fetch_last_shot() -> sqlite3.Row | None:
    """The most recently entered shot — the source of the pre-filled values."""
    connection = get_connection()
    try:
        return connection.execute(
            "SELECT bean_id, dose_g, grind_setting"
            "  FROM shots ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        connection.close()


def fetch_recent_shots(limit: int = 5) -> list[sqlite3.Row]:
    connection = get_connection()
    try:
        return connection.execute(
            "SELECT shot_date, bean_name, dose_g, yield_g, brew_ratio,"
            "       grind_setting, extraction_time_s, taste_rating"
            "  FROM v_shot_details"
            " ORDER BY shot_date DESC, id DESC"
            " LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        connection.close()


def insert_bean(name, roaster, roast_date, notes) -> int:
    connection = get_connection()
    try:
        with connection:
            cursor = connection.execute(
                "INSERT INTO beans (name, roaster, roast_date, notes)"
                " VALUES (?, ?, ?, ?)",
                (name, roaster, roast_date, notes),
            )
        return cursor.lastrowid
    finally:
        connection.close()


def insert_shot(bean_id, shot_date, dose_g, grind_setting, extraction_time_s,
                yield_g, water_temp_c, taste_rating, taste_notes) -> int:
    connection = get_connection()
    try:
        with connection:
            cursor = connection.execute(
                "INSERT INTO shots (bean_id, shot_date, dose_g, grind_setting,"
                " extraction_time_s, yield_g, water_temp_c, taste_rating,"
                " taste_notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (bean_id, shot_date, dose_g, grind_setting, extraction_time_s,
                 yield_g, water_temp_c, taste_rating, taste_notes),
            )
        return cursor.lastrowid
    finally:
        connection.close()


def blank_to_none(text: str) -> str | None:
    """Store an empty text field as NULL rather than an empty string."""
    return text.strip() or None


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Espresso Log", page_icon="☕")

st.title("☕ Espresso Log")
st.caption("Log a shot in a few taps, right after pulling it.")

if not DB_PATH.exists():
    st.error(
        f"No database at `{DB_PATH}`.\n\n"
        "Create it first:\n\n"
        "```bash\npython3 src/log_shot.py init\n```"
    )
    st.stop()

beans = fetch_beans()
last_shot = fetch_last_shot()


# --- Log a shot ------------------------------------------------------------

st.subheader("Log a shot")

if not beans:
    st.info("No beans yet — add one under **Add a new bean** below first.")
else:
    bean_ids = [row["id"] for row in beans]
    bean_labels = {
        row["id"]: f"{row['name']} — {row['roaster']}" if row["roaster"]
        else row["name"]
        for row in beans
    }

    # Pre-fill from the last shot; fall back to sensible defaults. The
    # columns are nullable, so a stored NULL falls back as well.
    bean_index = 0
    dose_default = DEFAULT_DOSE_G
    grind_default = DEFAULT_GRIND

    if last_shot is not None:
        if last_shot["bean_id"] in bean_ids:
            bean_index = bean_ids.index(last_shot["bean_id"])
        if last_shot["dose_g"] is not None:
            dose_default = float(last_shot["dose_g"])
        if last_shot["grind_setting"] is not None:
            grind_default = float(last_shot["grind_setting"])

    # One form, so the phone does not reload the page after every field.
    with st.form("log_shot"):
        bean_id = st.selectbox(
            "Bean", bean_ids, index=bean_index,
            format_func=lambda identifier: bean_labels[identifier],
        )

        left, right = st.columns(2)
        with left:
            # No tight bounds on purpose: the CHECK constraints in schema.sql
            # are the single authority on what counts as valid. A dose of 0
            # can be entered here and is then rejected by the database.
            dose_g = st.number_input("Dose (g)", min_value=0.0,
                                     value=dose_default, step=0.1,
                                     format="%.1f")
            grind_setting = st.number_input("Grind setting", min_value=0.0,
                                            value=grind_default, step=0.5,
                                            format="%.1f")
            extraction_time_s = st.number_input("Extraction time (s)",
                                                min_value=0,
                                                value=DEFAULT_TIME_S, step=1)
        with right:
            # 0 g is allowed: a fully choked shot is a real result.
            yield_g = st.number_input("Yield (g)", min_value=0.0,
                                      value=DEFAULT_YIELD_G, step=0.5,
                                      format="%.1f")
            water_temp_c = st.number_input("Water temperature (°C)",
                                           min_value=0.0,
                                           value=DEFAULT_TEMP_C, step=1.0,
                                           format="%.1f")
            taste_rating = st.slider("Taste rating", 1, 5, 3)

        shot_date = st.date_input("Date", value=date.today())
        taste_notes = st.text_input("Taste notes",
                                    placeholder="caramel, long finish")

        saved = st.form_submit_button("Save shot", type="primary")

    if saved:
        try:
            shot_id = insert_shot(
                bean_id,
                shot_date.isoformat(),
                dose_g,
                grind_setting,
                extraction_time_s,
                yield_g,
                water_temp_c,
                taste_rating,
                blank_to_none(taste_notes),
            )
        except sqlite3.IntegrityError as error:
            # A CHECK or FOREIGN KEY constraint said no. Show the reason
            # instead of crashing with a stack trace.
            st.error(f"Rejected by the database: {error}")
        else:
            ratio = f"1:{yield_g / dose_g:.2f}" if dose_g else "n/a"
            st.success(f"Saved shot #{shot_id} — brew ratio {ratio}")


# --- Add a new bean --------------------------------------------------------

# Collapsed by default: a new bag is opened every week or two, a shot is
# logged several times a day.
with st.expander("Add a new bean"):
    with st.form("add_bean", clear_on_submit=True):
        bean_name = st.text_input("Name")
        bean_roaster = st.text_input("Roaster")
        bean_roast_date = st.date_input("Roast date", value=date.today())
        bean_notes = st.text_input("Notes")

        bean_saved = st.form_submit_button("Add bean")

    if bean_saved:
        if not bean_name.strip():
            st.error("A bean needs a name.")
        else:
            try:
                new_id = insert_bean(
                    bean_name.strip(),
                    blank_to_none(bean_roaster),
                    bean_roast_date.isoformat(),
                    blank_to_none(bean_notes),
                )
            except sqlite3.IntegrityError as error:
                st.error(f"Rejected by the database: {error}")
            else:
                st.success(f"Added bean #{new_id}: {bean_name.strip()}")
                # Reload so the new bean appears in the dropdown above.
                st.rerun()


# --- Recent shots ----------------------------------------------------------

st.subheader("Recent shots")

recent = fetch_recent_shots()
if recent:
    st.dataframe([dict(row) for row in recent], hide_index=True)
else:
    st.caption("Nothing logged yet.")
