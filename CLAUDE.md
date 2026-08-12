# CLAUDE.md

Instructions for Claude Code when working in this repository.
This file is the single source of truth for the project setup.

## Project

Espresso Log: a SQL database project for tracking espresso shots
(DeLonghi La Specialista Arte). Part of a GitHub portfolio for a career
change into software development. The goal is to demonstrate a clean
relational data model and meaningful SQL analysis. No web frontend in
version 1.

## Tech stack (version 1)

- Language: Python (3.11+). The CLI uses the standard library only.
- Database: SQLite, local. The real `.db` file is never committed
  (see `.gitignore`) — only schema and seed data.
- Interface: a CLI script for logging (`src/log_shot.py`) and a Jupyter
  notebook for analysis (`notebooks/analyse.ipynb`). No web frontend.
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
  water_temp_c      REAL,
  taste_rating      INTEGER       CHECK (taste_rating BETWEEN 1 AND 5),
  taste_notes       TEXT,
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

## Folder structure

```
.
├── README.md
├── LICENSE
├── CLAUDE.md
├── .gitignore
├── requirements.txt
├── schema.sql
├── seed.sql
├── queries.sql
├── src/
│   ├── db.py
│   └── log_shot.py
├── notebooks/
│   └── analyse.ipynb
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
