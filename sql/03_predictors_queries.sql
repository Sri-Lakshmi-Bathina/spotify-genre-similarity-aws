-- Top features for a selected genre (example: rock)
SELECT genre, feature, importance_norm
FROM spotify_similarity_db.results_genre_predictors
WHERE genre = 'rock'
ORDER BY importance_norm DESC
LIMIT 20;

-- List genres available in predictors
SELECT DISTINCT genre
FROM spotify_similarity_db.results_genre_predictors
ORDER BY genre;
