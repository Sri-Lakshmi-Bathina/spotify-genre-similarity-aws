SELECT genre, baseline_available, delta_recall, delta_mrr, alpha_audio_weight
FROM spotify_similarity_db.results_eval_delta_audio_vs_audio_lyrics_flagged
ORDER BY baseline_available ASC, delta_recall DESC;
