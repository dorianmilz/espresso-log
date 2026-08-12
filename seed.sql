-- Espresso Log — sample data
--
-- Run against a fresh database:
--     python3 src/log_shot.py init
--     sqlite3 data/espresso.db < seed.sql
--
-- The ids are explicit, so this file is meant for an empty database. Running
-- it twice raises a UNIQUE constraint error rather than silently duplicating.
--
-- The numbers are invented but deliberately realistic: four bags of coffee
-- over two months, with a visible learning curve, one bag that clearly
-- outperforms the others, and a few failed shots.

BEGIN TRANSACTION;

INSERT INTO beans (id, name, roaster, roast_date, notes) VALUES
    (1, 'Ethiopia Sidamo',          'Roesterei Vier', '2026-06-10', 'Washed, floral, first bag on this machine'),
    (2, 'Brazil Fazenda Santa Ines','The Barn',       '2026-06-28', 'Natural, nutty, forgiving'),
    (3, 'Colombia Huila',           'Roesterei Vier', '2026-07-12', 'Washed, caramel sweetness'),
    (4, 'India Monsooned Malabar',  'Elbgold',        '2026-07-25', 'Very low acidity, heavy body');


INSERT INTO shots
    (bean_id, shot_date, dose_g, grind_setting, extraction_time_s, yield_g, water_temp_c, taste_rating, taste_notes)
VALUES
    -- Bag 1: learning the machine. Grinding too coarse at first.
    (1, '2026-06-12', 18.0, 5.0, 18, 42.0, 93.0, 2, 'Sour and thin, ran way too fast'),
    (1, '2026-06-13', 18.0, 4.5, 20, 38.0, 93.0, 2, 'Still sour, slightly more body'),
    (1, '2026-06-15', 18.0, 4.0, 24, 36.0, 93.0, 3, 'Balanced, a little sharp'),
    (1, '2026-06-17', 18.0, 3.5, 29, 34.0, 93.0, 3, 'Heavier, hint of bitterness'),
    (1, '2026-06-19', 18.0, 4.0, 26, 36.0, 94.0, 4, 'Blueberry note finally showing'),
    (1, '2026-06-21', 18.5, 4.0, 27, 37.0, 94.0, 4, 'Juicy finish, best of this bag'),
    (1, '2026-06-24', 18.5, 4.0, 25, 37.5, 94.0, 3, 'Fading, bag is getting old'),
    (1, '2026-06-26', 18.5, 3.5, 31, 35.0, 94.0, 3, 'Flat, past its best'),

    -- Bag 2: forgiving bean, used to dial in a repeatable routine.
    (2, '2026-06-30', 18.0, 4.0, 22, 36.0, 92.0, 3, 'Nutty but closed, very fresh roast'),
    (2, '2026-07-02', 18.0, 4.0, 25, 36.0, 92.0, 3, 'Chocolate, low acidity'),
    (2, '2026-07-04', 18.0, 3.5, 30, 34.0, 92.0, 4, 'Syrupy, thick crema'),
    (2, '2026-07-05', 18.0, 3.0, 38,  0.0, 92.0, 1, 'Choked completely, channelled, nothing came out'),
    (2, '2026-07-06', 18.0, 3.5, 28, 35.0, 92.0, 4, 'Back on track, sweet'),
    (2, '2026-07-08', 18.5, 3.5, 29, 36.0, 93.0, 4, 'Dark chocolate, thick'),
    (2, '2026-07-10', 18.5, 3.5, 27, 37.0, 93.0, 3, 'Slightly hollow in the middle'),
    (2, '2026-07-12', 18.5, 3.5, 30, 36.0, 93.0, 4, 'Consistent, easy bean'),

    -- Bag 3: the standout. Same recipe repeated on purpose.
    (3, '2026-07-15', 18.0, 4.0, 21, 38.0, 93.0, 3, 'Bright but underdeveloped, too young'),
    (3, '2026-07-17', 18.0, 3.5, 27, 36.0, 93.0, 4, 'Caramel, very clean'),
    (3, '2026-07-19', 18.0, 3.5, 29, 36.0, 94.0, 5, 'Caramel, red apple, long finish'),
    (3, '2026-07-21', 18.0, 3.5, 28, 36.0, 94.0, 5, 'Repeated yesterday exactly. This is the recipe.'),
    (3, '2026-07-23', 18.5, 3.5, 30, 37.0, 94.0, 5, 'Bigger dose, still excellent'),
    (3, '2026-07-25', 18.5, 3.5, 29, 37.0, 94.0, 4, 'Very good, marginally less sweet'),
    (3, '2026-07-27', 18.5, 4.0, 24, 39.0, 94.0, 4, 'Coarser and faster, more acidity'),
    (3, '2026-07-30', 18.5, 3.5, 31, 36.5, 94.0, 5, 'Peak of the bag'),
    (3, '2026-08-02', 18.5, 3.5, 30, 37.0, 94.0, 4, 'Starting to flatten out'),

    -- Bag 4: technically fine, simply not to my taste.
    (4, '2026-08-03', 18.0, 4.0, 23, 38.0, 92.0, 2, 'Woody, almost no acidity'),
    (4, '2026-08-05', 18.0, 3.5, 28, 36.0, 92.0, 3, 'Earthy, heavy body'),
    (4, '2026-08-06', 18.0, 3.0, 35, 33.0, 92.0, 2, 'Pushed too far, ashy'),
    (4, '2026-08-08', 18.5, 3.5, 29, 36.0, 93.0, 3, 'Decent in milk'),
    (4, '2026-08-09', 18.5, 3.5, 30, 37.0, 93.0, 4, 'Best this bag has given'),
    (4, '2026-08-11', 18.5, 3.5, 28, 36.5, 93.0, 3, 'Consistent but unexciting'),
    (4, '2026-08-12', 18.5, 4.0, 19, 40.0, 93.0, 2, 'Rushed the tamp, ran too fast again');

COMMIT;
