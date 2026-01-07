-- Optional: Build a reusable genre list that includes:
--   (a) TOP_N genres by track count (recommended baseline), PLUS
--   (b) VARIETY_M additional genres sampled at random from the remaining genres (for coverage)
--
-- Why this exists:
-- - The default pipeline evaluates TOP_N genres for fast / low-cost Glue runs.
-- - This optional table lets you include a "variety" slice without hand-picking genres.
--
-- How to use:
-- 1) Run this statement once in Athena.
-- 2) Use the resulting table to filter downstream queries or to set Glue job parameters.
--
-- Notes:
-- - If you re-run CTAS into the same external_location, delete the existing S3 prefix first.
-- - Edit the constants TOP_N / VARIETY_M / MIN_TRACKS as needed.

CREATE TABLE spotify_similarity_db.genre_list_topn_plus_variety
WITH (
  format = 'PARQUET',
  external_location = 's3://spotify-genre-similarity-sri/results/genre_selection/topn_plus_variety/'
) AS
WITH
  genre_counts AS (
    SELECT genre, COUNT(*) AS n_tracks
    FROM spotify_similarity_db.curated_tracks_by_genre
    WHERE genre IS NOT NULL
    GROUP BY 1
  ),
  top_genres AS (
    SELECT genre, n_tracks, 'top_n' AS reason
    FROM genre_counts
    ORDER BY n_tracks DESC
    LIMIT 10  -- TOP_N (default)
  ),
  rest_eligible AS (
    SELECT genre, n_tracks
    FROM genre_counts
    WHERE genre NOT IN (SELECT genre FROM top_genres)
      AND n_tracks >= 500  -- MIN_TRACKS
  ),
  variety_genres AS (
    SELECT genre, n_tracks, 'variety' AS reason
    FROM (
      SELECT genre, n_tracks, row_number() OVER (ORDER BY rand()) AS rn
      FROM rest_eligible
    )
    WHERE rn <= 10 -- VARIETY_M (default)
  )
SELECT * FROM top_genres
UNION ALL
SELECT * FROM variety_genres
;
