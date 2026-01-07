# Glue Jobs (as used in this deployment)

## Job inventory (uploaded)
1. `job_curate_tracks_by_genre.py`
2. `job_genre_predictors.py`
3. `job_eval_audio_similarity.py`
4. `job_fetch_lyrics_sample.py`
5. `job_convert_lyrics_jsonl_to_parquet.py`
6. `job_build_lyrics_enriched_by_genre.py`
7. `job_eval_audio_lyrics_similarity.py`

## Recommended run order
1) Curate / genre-split:
- Run `job_curate_tracks_by_genre.py`
- Run a **Glue crawler** on `s3://<bucket>/curated/tracks_by_genre/` to create `curated_tracks_by_genre`

2) Predictors + audio evaluation:
- Run `job_genre_predictors.py` → crawler to create `results_genre_predictors`
- Run `job_eval_audio_similarity.py` → crawler to create `results_eval_audio_similarity`

3) Lyrics workflow:
- In **Athena**, run `sql/05_lyrics_input_unload.sql` to create the input CSV in S3
- Run `job_fetch_lyrics_sample.py` to call the lyrics API and write JSONL
- Run `job_convert_lyrics_jsonl_to_parquet.py` → crawler to create `curated_lyrics_by_track_sample_parquet`
- Run `job_build_lyrics_enriched_by_genre.py` → crawler to create `curated_lyrics_enriched_by_genre`

4) Audio+Lyrics evaluation:
- Run `job_eval_audio_lyrics_similarity.py` → crawler to create `results_eval_audio_lyrics_similarity`
- In **Athena**, run `sql/07_delta_flagged_ctas.sql` (single statement) to create `results_eval_delta_audio_vs_audio_lyrics_flagged`

## Notes
- Glue **crawlers** and Athena SQL are not “jobs” but are required to reproduce the tables.
- `job_fetch_lyrics_sample.py` uses an external HTTP API. If your Glue job runs in a VPC, you may need a NAT gateway for outbound internet access.
