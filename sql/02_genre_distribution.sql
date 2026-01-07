SELECT genre, COUNT(*) AS track_rows
FROM spotify_similarity_db.curated_tracks_by_genre
GROUP BY 1
ORDER BY track_rows DESC
LIMIT 50;
