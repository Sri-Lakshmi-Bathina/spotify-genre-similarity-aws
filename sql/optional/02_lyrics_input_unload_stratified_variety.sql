-- Optional: Generate a STRATIFIED lyrics input file (balanced sampling across many genres).
--
-- Default pipeline behavior (recommended):
-- - Use only the TOP_N genres to keep Glue costs low and runs fast.
--
-- This alternative:
-- - Samples up to PER_GENRE tracks from every eligible genre (min track threshold), which gives broader coverage.
--
-- Tune:
-- - PER_GENRE: number of tracks per genre
-- - MIN_TRACKS_PER_GENRE: exclude tiny genres
-- - TOTAL_CAP: optional overall cap (safety)
--
-- Output columns match job_fetch_lyrics_sample expectations:
--   track_id, track_name, artist_name_primary, genre

UNLOAD (
  WITH base AS (
    SELECT
      id   AS track_id,
      name AS track_name,
      artist_name_primary,
      genre,
      row_number() OVER (PARTITION BY genre ORDER BY rand()) AS rn
    FROM spotify_similarity_db.curated_tracks_by_genre
    WHERE id IS NOT NULL
      AND name IS NOT NULL
      AND artist_name_primary IS NOT NULL
      AND genre IS NOT NULL
  ),
  stratified AS (
    SELECT *
    FROM base
    WHERE rn <= 10 -- PER_GENRE (default)
  )
  SELECT track_id, track_name, artist_name_primary, genre
  FROM stratified
  LIMIT 5000 -- TOTAL_CAP (optional safety)
)
TO 's3://spotify-genre-similarity-sri/curated/lyrics_input_stratified_safe/'
WITH (
  format = 'TEXTFILE',
  field_delimiter = ',',
  compression = 'NONE',
  output_file_extension = '.csv',
  write_header = true
);
