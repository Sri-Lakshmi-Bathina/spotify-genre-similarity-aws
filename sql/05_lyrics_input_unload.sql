UNLOAD (
WITH top_genres AS (
  SELECT genre
  FROM spotify_similarity_db.curated_tracks_by_genre
  GROUP BY 1
  HAVING COUNT(*) >= 1000
  ORDER BY COUNT(*) DESC
  LIMIT 20
),
candidates AS (
  SELECT
    COALESCE(track_id, id) AS track_id,
    COALESCE(track_name, name) AS track_name,
    COALESCE(artist_name_primary, artist_names, artists) AS artist_name_primary,
    genre,
    row_number() OVER (PARTITION BY genre ORDER BY rand()) AS rn
  FROM spotify_similarity_db.curated_tracks_by_genre
  WHERE genre IN (SELECT genre FROM top_genres)
)
SELECT track_id, track_name, artist_name_primary, genre
FROM candidates
WHERE rn <= 40
) TO 's3://spotify-genre-similarity-sri/curated/lyrics_input_header/'
WITH (
  format = 'TEXTFILE',
  field_delimiter = ',',
  compression = 'NONE',
  write_header = true
);
