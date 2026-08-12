# Espresso Log

A small SQLite database for tracking espresso shots on a DeLonghi La
Specialista Arte, and for answering the question every home barista argues
about: which settings actually produce a good cup?

Every shot is logged with its dose, grind setting, extraction time, yield and
a taste rating. The analysis is plain SQL — the interesting part of this
project is the data model and the queries, not the interface.

## Data model

Two tables. One bag of coffee has many shots.

```
beans                          shots
-----                          -----
id          INTEGER PK  <----  bean_id           INTEGER FK
name        TEXT                shot_date         DATE
roaster     TEXT                dose_g            REAL   > 0
roast_date  DATE                grind_setting     REAL   > 0
notes       TEXT                extraction_time_s INTEGER > 0
                                yield_g           REAL   >= 0
                                water_temp_c      REAL
                                taste_rating      INTEGER 1-5
                                taste_notes       TEXT
                                machine           TEXT
```

Three decisions worth pointing out:

- **Brew ratio is never stored.** It is `yield_g / dose_g`, so storing it
  would allow it to contradict the columns it derives from. It is computed
  in queries and exposed through the view `v_shot_details`, together with
  the bean's rest time in days.
- **`yield_g >= 0`, not `> 0`.** A choked shot that channels and delivers
  nothing is a real result worth recording, not an input error.
- **`grind_setting` is a number, not text.** That is what makes
  "which grinder setting hits the target extraction window?" answerable.

Value ranges are enforced by `CHECK` constraints in the database itself, so
invalid rows are rejected no matter which client writes them.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create the database and load the sample data:

```bash
python3 src/log_shot.py init
sqlite3 data/espresso.db < seed.sql
```

The real database is not part of this repository (see `.gitignore`) — it is
personal data and a binary file. `schema.sql` and `seed.sql` rebuild an
equivalent one in two commands.

## Logging shots

```bash
python3 src/log_shot.py add-bean          # asks for the values it needs
python3 src/log_shot.py add-shot          # same, and lists the beans first
python3 src/log_shot.py list-shots --limit 5
```

Every field can also be passed as a flag, which makes the CLI scriptable:

```bash
python3 src/log_shot.py add-shot --bean-id 3 --dose-g 18 --grind 3.5 \
    --time-s 29 --yield-g 36 --rating 5 --notes "caramel, long finish"
```

```
Added shot #33
Brew ratio: 1:2.00
```

Invalid values never reach the table:

```
$ python3 src/log_shot.py add-shot --bean-id 1 --dose-g 18 --rating 9
Rejected by the database: CHECK constraint failed: taste_rating BETWEEN 1 AND 5

$ python3 src/log_shot.py add-shot --bean-id 999 --dose-g 18 --rating 3
Rejected by the database: FOREIGN KEY constraint failed
```

## Analysis

All queries live in [`queries.sql`](queries.sql), commented one by one. Run
the whole file:

```bash
sqlite3 -header -column data/espresso.db < queries.sql
```

### Which bean scored best?

`GROUP BY` with `HAVING`, so bags with too few shots to judge are excluded.

```
bean                       roaster         shots  avg_rating  avg_time_s  avg_brew_ratio
-------------------------  --------------  -----  ----------  ----------  --------------
Colombia Huila             Roesterei Vier  9      4.33        28.0        2.02
Brazil Fazenda Santa Ines  The Barn        8      3.25        29.0        1.72
Ethiopia Sidamo            Roesterei Vier  8      3.0         25.0        2.03
India Monsooned Malabar    Elbgold         7      2.71        27.0        2.0
```

### Does extraction time predict quality?

`CASE` turns a continuous value into comparable buckets.

```
extraction_band      shots  avg_rating  avg_brew_ratio
-------------------  -----  ----------  --------------
a: under 22s (fast)  4      2.25        2.18
b: 22-32s (target)   26     3.69        1.99
c: over 32s (slow)   2      1.5         0.92
```

Shots inside the 22–32 second window average a full rating point above the
fast ones — and the fast shots also run thin, at a brew ratio well above 1:2.

### Which grinder setting hits the target window?

Only answerable because the grind setting is stored as a number.

```
grind_setting  shots  avg_time_s  avg_brew_ratio  avg_rating
-------------  -----  ----------  --------------  ----------
3.0            2      36.5        0.92            1.5
3.5            18     29.1        1.97            3.89
4.0            10     23.6        2.05            3.1
4.5            1      20.0        2.11            2.0
5.0            1      18.0        2.33            2.0
```

Setting 3.5 lands in the middle of the target window and rates highest.

The remaining queries cover the brew ratio per shot, the full parameter set
of every top-rated shot, the effect of bean rest time (a `julianday()`
difference), and a rating trend over time using a window function.

## Notebook

[`notebooks/analyse.ipynb`](notebooks/analyse.ipynb) loads the same data with
pandas and plots four of these questions, including a rolling average that
smooths out single good or bad shots.

```bash
jupyter lab notebooks/analyse.ipynb
```

## Development Process

I built this project with [Claude Code](https://claude.com/claude-code)
as an implementation assistant. The design decisions, the data model
(tables, constraints, the `v_shot_details` view), the SQL query set,
and the git workflow (branch and commit structure) were mine, reviewed
and adjusted before each implementation step. Claude Code wrote the
code under that direction and flagged trade-offs (e.g. `REAL` vs
`INTEGER` for `grind_setting`) for me to decide.

This project is part of a portfolio built to practice SQL and data
modeling. See the commit history for the incremental build order.

## Possible next steps

- Automated tests (`pytest`) for the CLI and the constraints
- A `pull` command that repeats the parameters of a previous shot
- Tracking water hardness and basket size
- Exporting a monthly summary

## License

MIT — see [LICENSE](LICENSE).
