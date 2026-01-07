CREATE TABLE spotify_similarity_db.results_eval_delta_audio_vs_audio_lyrics_flagged
WITH (
  format = 'PARQUET',
  external_location = 's3://spotify-genre-similarity-sri/results/eval_delta_audio_vs_audio_lyrics_flagged/',
  partitioned_by = ARRAY['genre']
) AS
WITH a AS (
  SELECT genre, recall_at_k AS recall_audio, mrr_at_k AS mrr_audio
  FROM spotify_similarity_db.results_eval_audio_similarity
),
al AS (
  SELECT genre, recall_at_k AS recall_audio_lyrics, mrr_at_k AS mrr_audio_lyrics,
         alpha_audio_weight, n_queries, n_tracks_in_genre, run_ts
  FROM spotify_similarity_db.results_eval_audio_lyrics_similarity
)
SELECT
  CASE WHEN a.genre IS NULL THEN 0 ELSE 1 END AS baseline_available,
  a.recall_audio,
  al.recall_audio_lyrics,
  CASE WHEN a.genre IS NULL THEN NULL ELSE (al.recall_audio_lyrics - a.recall_audio) END AS delta_recall,
  a.mrr_audio,
  al.mrr_audio_lyrics,
  CASE WHEN a.genre IS NULL THEN NULL ELSE (al.mrr_audio_lyrics - a.mrr_audio) END AS delta_mrr,
  al.alpha_audio_weight,
  al.n_queries,
  al.n_tracks_in_genre,
  al.run_ts,
  al.genre
FROM al
LEFT JOIN a ON a.genre = al.genre;
