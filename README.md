# Spotify Similarity — Genre Split, Predictors, Evaluation, Lyrics (AWS Free Tier)

End-to-end analytics workflow on **AWS S3 + Glue + Athena + QuickSight** for a genre-aware song similarity use case.

## Use case
1. **Split data by genre** so similarity is computed within a comparable musical context.
2. **Identify top predictors (audio metrics) per genre** to understand which features drive similarity.
3. **Evaluate effectiveness** of the similarity ranking using **Recall@K** and **MRR@K**.
4. **Extend with lyrics** (free lyrics API) and quantify the impact vs audio-only similarity.

## Dataset
- Kaggle: *Top Spotify Songs 2023* (tracks + artists)  
  Source: https://www.kaggle.com/datasets/nelgiriyewithana/top-spotify-songs-2023

## AWS environment (your run)
- Region: `us-east-1`
- S3 bucket: `spotify-genre-similarity-sri`
- Athena Workgroup: `primary`
- Athena database: `spotify_similarity_db`
- Athena query results location: `s3://spotify-genre-similarity-sri/athena-query-results/`

## Architecture (high level)
**S3 (raw)** → **Glue Crawlers (catalog)** → **Glue Jobs (curation + evaluation)** → **S3 (curated/results)** → **Athena SQL (CTAS + QA)** → **QuickSight Analysis → Dashboard**

## Repository structure
- `glue/` — Glue job scripts (PySpark + one Python Shell job)
- `sql/` — Athena queries used across the workflow (setup, validation, QA, CTAS)
- `docs/` — Runbook, dashboard build notes, and exported dashboard PDFs
- `iam/` — Glue service role S3 access policy used in this project

## S3 layout (prefixes)
- `raw/tracks/` — `tracks.csv`
- `raw/artists/` — `artists.csv`
- `curated/tracks_by_genre/` — curated parquet, partitioned by `genre`
- `curated/lyrics_input_*/` — small CSV exported from Athena (lyrics fetch input)
- `curated/lyrics_by_track_sample/` — lyrics JSONL fetched from API
- `curated/lyrics_by_track_sample_parquet/` — lyrics parquet, partitioned by `genre`
- `curated/lyrics_enriched_by_genre/` — tracks joined with lyrics (parquet)
- `results/genre_predictors/` — per-genre feature importances (parquet)
- `results/eval_audio_similarity/` — audio-only evaluation metrics (parquet)
- `results/eval_audio_lyrics_similarity/` — audio+lyrics evaluation metrics (parquet)
- `results/eval_delta_audio_vs_audio_lyrics*/` — delta metrics and baseline availability flags (parquet)

## Glue jobs (scripts in this repo)
1. `job_curate_tracks_by_genre.py` (Spark): build `curated/tracks_by_genre/` partitioned by `genre`
2. `job_genre_predictors.py` (Spark): compute per-genre “predictor importance” (feature contributions)
3. `job_eval_audio_similarity.py` (Spark): evaluate audio-only similarity (Recall@K, MRR@K)
4. `job_fetch_lyrics_sample.py` (Python Shell): call lyrics API (LRCLIB) and write JSONL to S3
5. `job_convert_lyrics_jsonl_to_parquet.py` (Spark): convert JSONL → parquet partitioned by `genre`
6. `job_build_lyrics_enriched_by_genre.py` (Spark): join curated tracks + lyrics
7. `job_eval_audio_lyrics_similarity.py` (Spark): evaluate audio+lyrics similarity (Recall@K, MRR@K)

## Glue crawlers (catalog registration)
This repo documents the crawlers used. If you are recreating from scratch, create crawlers for:
- `raw/tracks/` → `raw_tracks`
- `raw/artists/` → `raw_artists`
- `curated/tracks_by_genre/` → `curated_tracks_by_genre`
- `results/genre_predictors/` → `results_genre_predictors`
- `results/eval_audio_similarity/` → `results_eval_audio_similarity`
- `curated/lyrics_by_track_sample_parquet/` → `curated_lyrics_by_track_sample_parquet`
- `curated/lyrics_enriched_by_genre/` → `curated_lyrics_enriched_by_genre` *(recommended — sometimes missed)*
- `results/eval_audio_lyrics_similarity/` → `results_eval_audio_lyrics_similarity`

> Note: The “delta/flagged” tables are created via Athena CTAS in `sql/07_delta_flagged_ctas.sql`, so a crawler is not required.

## QuickSight datasets used in the dashboard
- `curated_tracks_by_genre` (distribution)
- `results_genre_predictors` (feature importances)
- `results_eval_audio_similarity` (audio-only effectiveness)
- `results_eval_delta_audio_vs_audio_lyrics_flagged` (lyrics impact + baseline availability)

## How to reproduce
Follow `docs/WORKFLOW.md` end-to-end, then use `docs/QUICKSIGHT_DASHBOARD.md` to recreate the dashboard layout.

## Exports
- Final dashboard PDF export: `docs/dashboard/Spotify Similarity — Genre Split, Predictors, Evaluation, Lyrics.pdf`

## License
MIT

## Documentation

- Genre selection options (default TOP_N): `docs/GENRE_SELECTION.md`
