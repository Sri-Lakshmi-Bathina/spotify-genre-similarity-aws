-- Audio-only evaluation
SELECT genre, n_queries, k, recall_at_k, mrr_at_k, run_ts
FROM spotify_similarity_db.results_eval_audio_similarity
ORDER BY recall_at_k DESC;

-- Audio+Lyrics evaluation
SELECT genre, n_queries, k, recall_at_k, mrr_at_k, alpha_audio_weight, n_tracks_in_genre, run_ts
FROM spotify_similarity_db.results_eval_audio_lyrics_similarity
ORDER BY recall_at_k DESC;
