# CLAUDE.md

Instructions for Claude Code when working in this repository.
This file is the single source of truth for the project setup.

## Project

Espresso Log: a SQL database project for tracking espresso shots
(DeLonghi La Specialista Arte). Part of a GitHub portfolio for a career
change into software development. The goal is to demonstrate a clean
relational data model and meaningful SQL analysis.

Version 1 deliberately shipped without a web frontend, to keep the focus
on the data model. Version 2 adds a Streamlit page (`app.py`) for logging
a shot from a phone on the same network — the analysis side stays SQL.

## Tech stack (version 2)

- Language: Python (3.11+). The CLI uses the standard library only.
- Database: SQLite, local. The real `.db` file is never committed
  (see `.gitignore`) — only schema and seed data.
- Interface: a CLI script for logging (`src/log_shot.py`), a Streamlit
  web page for quick entry (`app.py`), and a Jupyter notebook for
  analysis (`notebooks/analyse.ipynb`).
- Web interface: `streamlit`. It goes through `get_connection()` from
  `src/db.py` like everything else — no separate connection logic. The
  number fields deliberately impose no bounds of their own; the CHECK
  constraints in `schema.sql` remain the single authority on valid data.
- Tests: `pytest`, run with `pytest` from the repository root. Each test
  gets its own temporary database through `ESPRESSO_DB`; the real
  `data/espresso.db` is never touched.
- Language used in code, comments and README: English.

## Data model

```sql
CREATE TABLE beans (
  id         INTEGER PRIMARY KEY,
  name       TEXT NOT NULL,
  roaster    TEXT,
  roast_date DATE,
  notes      TEXT
);

CREATE TABLE shots (
  id                INTEGER PRIMARY KEY,
  bean_id           INTEGER REFERENCES beans(id),
  shot_date         DATE NOT NULL,
  dose_g            REAL NOT NULL CHECK (dose_g > 0),
  grind_setting     REAL          CHECK (grind_setting > 0),
  extraction_time_s INTEGER       CHECK (extraction_time_s > 0),
  yield_g           REAL          CHECK (yield_g >= 0),
  water_temp_c      REAL          CHECK (water_temp_c IN (92.0, 94.0, 96.0)),
  taste_rating      INTEGER       CHECK (taste_rating BETWEEN 1 AND 5),
  taste_notes       TEXT          CHECK (taste_notes IN (
                                    'Very Bitter', 'Bitter', 'Balanced',
                                    'Sour',        'Very Sour')),
  machine           TEXT DEFAULT 'DeLonghi La Specialista Arte'
);
```

Notes on the constraints:

- `grind_setting` is a **number**, not text — the grinder uses numbered
  settings, and storing it numerically allows analysing grind setting
  against extraction time and rating.
- `yield_g >= 0` (not `> 0`) on purpose: a choked, fully channelled shot
  with 0 g output is a real result worth recording, not an input error.
- Brew ratio (`yield_g / dose_g`) is **not stored**. It is computed in
  queries and exposed through the view `v_shot_details`.
- `water_temp_c` and `taste_notes` are **controlled vocabularies**. The
  three temperatures are the settings of this one machine model — the
  constraint is deliberately tied to it. `taste_notes` is a five-point
  extraction balance scale (sour = under-extracted, bitter = over-extracted,
  balanced = target), not a flavour description: it is the axis that grind
  setting and extraction time move, so it can be grouped against both.
- Both restricted columns stay **optional**: a CHECK rejects a row only
  when its expression is false, and `NULL IN (...)` is neither true nor
  false, so an empty field passes without an extra `OR ... IS NULL`.
- The allowed values live once in Python, as `WATER_TEMPS_C`, `TEMP_LABELS`
  and `TASTE_NOTES` in `src/db.py`; the CLI and the Streamlit page build
  their menus from them. `schema.sql` stays the authority — the schema
  tests insert every value from those constants, so a drift between the
  two turns the suite red.

## Folder structure

```
.
├── README.md
├── LICENSE
├── CLAUDE.md
├── .gitignore
├── requirements.txt
├── app.py           # Streamlit quick-entry page
├── schema.sql
├── seed.sql
├── queries.sql
├── src/
│   ├── db.py
│   └── log_shot.py
├── notebooks/
│   └── analyse.ipynb
├── tests/
│   ├── conftest.py  # shared fixtures
│   ├── test_schema.py
│   ├── test_db.py
│   └── test_cli.py
├── assets/          # charts exported from the notebook for the README
└── data/            # git-ignored, holds the real espresso.db
```

## Git workflow

- `main` stays commit-free until the first confirmed merge.
- All work happens on feature branches (e.g. `feature/v1-scaffold`).
- Merges into `main` are always discussed before they happen.
- Small, focused commits with descriptive messages — the history should
  read as a comprehensible build-up of the project.

### Commit plan for version 1

1. Project skeleton: README stub, `.gitignore`, `requirements.txt`,
   `LICENSE`, `CLAUDE.md`
2. `schema.sql`
3. `src/db.py`
4. `src/log_shot.py`
5. `seed.sql`
6. `queries.sql`
7. `notebooks/analyse.ipynb`
8. Final `README.md` including example output
