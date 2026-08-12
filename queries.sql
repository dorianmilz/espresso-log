-- Espresso Log — analysis queries
--
-- Run all of them:
--     sqlite3 -header -column data/espresso.db < queries.sql
--
-- Each query answers one question about the shot log.


-- ===========================================================================
-- 1. Every shot with its brew ratio
--    Brew ratio = yield / dose. It is never stored, only computed.
-- ===========================================================================
SELECT
    s.shot_date,
    b.name AS bean,
    s.dose_g,
    s.yield_g,
    ROUND(s.yield_g / s.dose_g, 2) AS brew_ratio,
    s.extraction_time_s,
    s.taste_rating
FROM shots AS s
JOIN beans AS b ON b.id = s.bean_id
ORDER BY s.shot_date DESC
LIMIT 10;


-- ===========================================================================
-- 2. Which bean scored best?
--    HAVING filters on the aggregate, so bags with too few shots to judge
--    are excluded. (WHERE cannot do this — it runs before grouping.)
-- ===========================================================================
SELECT
    b.name AS bean,
    b.roaster,
    COUNT(*)                        AS shots,
    ROUND(AVG(s.taste_rating), 2)   AS avg_rating,
    ROUND(AVG(s.extraction_time_s)) AS avg_time_s,
    ROUND(AVG(s.yield_g / s.dose_g), 2) AS avg_brew_ratio
FROM shots AS s
JOIN beans AS b ON b.id = s.bean_id
GROUP BY b.id
HAVING COUNT(*) >= 5
ORDER BY avg_rating DESC;


-- ===========================================================================
-- 3. What was my best recipe?
--    The full parameter set of every top-rated shot, newest first.
-- ===========================================================================
SELECT
    shot_date,
    bean_name,
    dose_g,
    grind_setting,
    extraction_time_s,
    yield_g,
    brew_ratio,
    water_temp_c,
    taste_notes
FROM v_shot_details
WHERE taste_rating = 5
ORDER BY shot_date DESC;


-- ===========================================================================
-- 4. Does extraction time predict quality?
--    CASE turns a continuous number into named buckets, which is what makes
--    the averages comparable.
-- ===========================================================================
SELECT
    CASE
        WHEN extraction_time_s < 22 THEN 'a: under 22s (fast)'
        WHEN extraction_time_s <= 32 THEN 'b: 22-32s (target)'
        ELSE                              'c: over 32s (slow)'
    END AS extraction_band,
    COUNT(*)                      AS shots,
    ROUND(AVG(taste_rating), 2)   AS avg_rating,
    ROUND(AVG(brew_ratio), 2)     AS avg_brew_ratio
FROM v_shot_details
GROUP BY extraction_band
ORDER BY extraction_band;


-- ===========================================================================
-- 5. How long should beans rest after roasting?
--    days_off_roast comes from the view and is a julianday() difference.
-- ===========================================================================
SELECT
    CASE
        WHEN days_off_roast <  7 THEN 'a: 0-6 days'
        WHEN days_off_roast < 14 THEN 'b: 7-13 days'
        WHEN days_off_roast < 21 THEN 'c: 14-20 days'
        ELSE                          'd: 21+ days'
    END AS rest_period,
    COUNT(*)                    AS shots,
    ROUND(AVG(taste_rating), 2) AS avg_rating
FROM v_shot_details
WHERE days_off_roast IS NOT NULL
GROUP BY rest_period
ORDER BY rest_period;


-- ===========================================================================
-- 6. Am I getting better over time?
--    A window function computes a rolling average over the current row and
--    the four before it, which smooths out single good or bad shots.
-- ===========================================================================
SELECT
    shot_date,
    bean_name,
    taste_rating,
    ROUND(
        AVG(taste_rating) OVER (
            ORDER BY shot_date, id
            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        ), 2
    ) AS rolling_avg_5
FROM v_shot_details
ORDER BY shot_date, id;


-- ===========================================================================
-- 7. Which grinder setting hits the target window?
--    Only possible because grind_setting is stored as a number.
-- ===========================================================================
SELECT
    grind_setting,
    COUNT(*)                            AS shots,
    ROUND(AVG(extraction_time_s), 1)    AS avg_time_s,
    ROUND(AVG(brew_ratio), 2)           AS avg_brew_ratio,
    ROUND(AVG(taste_rating), 2)         AS avg_rating
FROM v_shot_details
WHERE grind_setting IS NOT NULL
GROUP BY grind_setting
ORDER BY grind_setting;
