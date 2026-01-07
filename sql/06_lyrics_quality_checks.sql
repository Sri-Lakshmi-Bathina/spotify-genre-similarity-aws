-- Example: Parquet lyrics table created by crawler
SELECT
  COUNT(*) AS lyric_rows,
  SUM(CASE WHEN lyrics_found THEN 1 ELSE 0 END) AS found_rows
FROM spotify_similarity_db.curated_lyrics_by_track_sample_parquet;

-- Example: joined table created by your Glue job
SELECT
  genre,
  COUNT(*) AS tracks_in_curated,
  SUM(CASE WHEN lyrics IS NOT NULL AND length(lyrics) > 0 THEN 1 ELSE 0 END) AS tracks_with_lyrics
FROM spotify_similarity_db.curated_tracks_with_lyrics
GROUP BY 1
ORDER BY tracks_with_lyrics DESC;
