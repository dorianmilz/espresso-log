-- Espresso Log — database schema
--
-- Run with:  sqlite3 data/espresso.db < schema.sql
-- or via:    python3 src/log_shot.py init
--
-- Every statement uses IF NOT EXISTS, so running this file twice is safe.

-- SQLite does not enforce foreign keys unless asked to, per connection.
PRAGMA foreign_keys = ON;


-- ---------------------------------------------------------------------------
-- beans — one row per bag of coffee
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS beans (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    roaster    TEXT,
    roast_date DATE,
    notes      TEXT
);


-- ---------------------------------------------------------------------------
-- shots — one row per espresso pulled
--
-- CHECK constraints are validated by the database itself, so invalid data
-- cannot enter the table regardless of which client wrote it.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS shots (
    id                INTEGER PRIMARY KEY,
    bean_id           INTEGER REFERENCES beans(id),
    shot_date         DATE    NOT NULL,

    -- A shot without a dose is not a shot.
    dose_g            REAL    NOT NULL CHECK (dose_g > 0),

    -- Numbered grinder dial. REAL rather than INTEGER so half steps stay
    -- possible; storing it as a number allows averaging and sorting.
    grind_setting     REAL             CHECK (grind_setting > 0),

    extraction_time_s INTEGER          CHECK (extraction_time_s > 0),

    -- Deliberately >= 0: a fully choked, channelled shot yielding 0 g is a
    -- real and useful result, not a typo.
    yield_g           REAL             CHECK (yield_g >= 0),

    -- The three settings this machine model offers: Low / Middle / High.
    -- Deliberately tied to the DeLonghi La Specialista Arte — another
    -- machine with different steps could not be logged without changing
    -- this list.
    water_temp_c      REAL             CHECK (water_temp_c IN (92.0, 94.0, 96.0)),

    taste_rating      INTEGER          CHECK (taste_rating BETWEEN 1 AND 5),

    -- A five-point scale for extraction balance, not a flavour description.
    -- It has a direction: sour means under-extracted (the water was not on
    -- the coffee long enough), bitter means over-extracted, balanced is the
    -- target. That makes it analysable against grind_setting and
    -- extraction_time_s — the two settings that move the same axis.
    -- Kept in step with WATER_TEMPS_C / TASTE_NOTES in src/db.py.
    taste_notes       TEXT             CHECK (taste_notes IN (
                                           'Very Bitter',
                                           'Bitter',
                                           'Balanced',
                                           'Sour',
                                           'Very Sour'
                                       )),

    machine           TEXT    DEFAULT 'DeLonghi La Specialista Arte'
);

-- Note on both lists above: a CHECK rejects a row only when the expression
-- is FALSE. `NULL IN (...)` is neither true nor false but NULL, so leaving
-- either column empty still passes — both stay optional without an extra
-- `OR ... IS NULL`.


-- Indexes for the two columns queries filter and join on most often.
CREATE INDEX IF NOT EXISTS idx_shots_bean_id   ON shots (bean_id);
CREATE INDEX IF NOT EXISTS idx_shots_shot_date ON shots (shot_date);


-- ---------------------------------------------------------------------------
-- v_shot_details — a view, i.e. a stored query rather than a stored table.
--
-- Brew ratio and bean rest days are derived values: they are computed on
-- every read instead of being written into the shots table, so they can
-- never fall out of sync with the columns they depend on.
-- ---------------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_shot_details AS
SELECT
    s.id,
    s.shot_date,
    b.name    AS bean_name,
    b.roaster,
    s.dose_g,
    s.yield_g,
    s.grind_setting,
    s.extraction_time_s,
    s.water_temp_c,
    s.taste_rating,
    s.taste_notes,

    -- Brew ratio: how many grams out per gram in. NULL if yield is unknown.
    ROUND(s.yield_g / s.dose_g, 2) AS brew_ratio,

    -- Days between roasting and pulling the shot ("rest time").
    -- julianday() converts a date into a number of days, which makes the
    -- subtraction possible. CAST(... AS INTEGER) drops the fraction.
    CAST(julianday(s.shot_date) - julianday(b.roast_date) AS INTEGER)
        AS days_off_roast

FROM shots AS s
LEFT JOIN beans AS b ON b.id = s.bean_id;
