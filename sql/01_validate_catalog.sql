SHOW TABLES IN spotify_similarity_db;

SELECT COUNT(*) AS raw_tracks_rows FROM spotify_similarity_db.raw_tracks;
SELECT COUNT(*) AS raw_artists_rows FROM spotify_similarity_db.raw_artists;
SELECT COUNT(*) AS curated_rows FROM spotify_similarity_db.curated_tracks_by_genre;

SELECT * FROM spotify_similarity_db.raw_tracks LIMIT 5;
SELECT * FROM spotify_similarity_db.raw_artists LIMIT 5;
SELECT * FROM spotify_similarity_db.curated_tracks_by_genre LIMIT 5;
