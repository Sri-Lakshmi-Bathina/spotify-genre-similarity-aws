# Workflow Runbook (S3 + Glue + Athena + QuickSight)

This runbook mirrors the steps used to generate the final dashboard. It is written so you can recreate the project end-to-end.

## 0) Prerequisites
- Region: `us-east-1`
- S3 bucket: `spotify-genre-similarity-sri`
- Athena Workgroup: `primary`
- Athena database: `spotify_similarity_db`
- Athena query results: `s3://spotify-genre-similarity-sri/athena-query-results/`
- Glue service role: `AWSGlueServiceRole-spotify-genre-similarity`
  - Attach `iam/GlueS3Access-spotify-genre-similarity-sri.json` (project S3 permissions)
  - Also attach AWS-managed `AWSGlueServiceRole`

## 1) Upload raw data to S3
1. Download dataset from Kaggle (see README).
2. Upload:
   - `tracks.csv` → `s3://spotify-genre-similarity-sri/raw/tracks/`
   - `artists.csv` → `s3://spotify-genre-similarity-sri/raw/artists/`

## 2) Create Glue crawlers for raw tables
Create two crawlers (run on demand):

### Crawler: `crawler_raw_tracks`
- Target: `s3://spotify-genre-similarity-sri/raw/tracks/`
- Database: `spotify_similarity_db`
- Table: `raw_tracks`
- Classifier: auto-detect (CSV)
- Schema change policy (recommended defaults):
  - **Update**: Update in database
  - **Delete**: Deprecate in database

### Crawler: `crawler_raw_artists`
- Target: `s3://spotify-genre-similarity-sri/raw/artists/`
- Database: `spotify_similarity_db`
- Table: `raw_artists`
- Same schema policy as above

Run both crawlers. Then validate in Athena with `sql/01_validate_catalog.sql`.

## 3) Curate tracks by genre (Glue job + crawler)
### Glue job: `job_curate_tracks_by_genre` (Spark)
- Script: `glue/job_curate_tracks_by_genre.py`
- Output: `s3://spotify-genre-similarity-sri/curated/tracks_by_genre/` (Parquet, partitioned by `genre`)
- Workers: 2 (smallest available)

Run the job.

### Crawler: `crawler_curated_tracks_by_genre`
- Target: `s3://spotify-genre-similarity-sri/curated/tracks_by_genre/`
- Database: `spotify_similarity_db`
- Table: `curated_tracks_by_genre` (your console might show a slightly different name; adjust SQL accordingly)
- Classifier: Parquet
- Schema change policy: same recommended defaults

Run the crawler.

## 4) Genre distribution QA (Athena)
Run `sql/02_genre_distribution.sql` to confirm:
- top genres by track count
- you have enough tracks per genre for evaluation

## 5) Per-genre predictor importance (Glue job + crawler)
### Glue job: `job_genre_predictors` (Spark)
- Script: `glue/job_genre_predictors.py`
- Input: `spotify_similarity_db.curated_tracks_by_genre`
- Output: `s3://spotify-genre-similarity-sri/results/genre_predictors/` (Parquet)

> **Genre coverage control (default: TOP_N genres):**  
> The Spark jobs can run in `top_n` mode (recommended) or `top_n_plus_variety` mode for broader coverage.  
> See `docs/GENRE_SELECTION.md` for the exact Glue job parameters (`--GENRE_MODE`, `--TOP_GENRES`, etc.).

Run the job.

### Crawler: `crawler_results_genre_predictors`
- Target: `s3://spotify-genre-similarity-sri/results/genre_predictors/`
- Table: `results_genre_predictors`

Run the crawler.

## 6) Audio-only evaluation (Glue job + crawler)
### Glue job: `job_eval_audio_similarity` (Spark)
- Script: `glue/job_eval_audio_similarity.py`
- Output: `s3://spotify-genre-similarity-sri/results/eval_audio_similarity/`

Run the job.

### Crawler: `crawler_results_eval_audio_similarity`
- Target: `s3://spotify-genre-similarity-sri/results/eval_audio_similarity/`
- Table: `results_eval_audio_similarity`

Run the crawler.

## 7) Create lyrics fetch input (Athena UNLOAD)
Run `sql/05_lyrics_input_unload.sql`.

This generates a small CSV in:
- `s3://spotify-genre-similarity-sri/curated/lyrics_input_header/` *(or similar, depending on your query)*

## 8) Fetch lyrics sample (Glue Python Shell job)
### Glue job: `job_fetch_lyrics_sample` (Python Shell)
- Script: `glue/job_fetch_lyrics_sample.py`
- Additional modules: `requests==2.31.0`
- Input CSV: `s3://spotify-genre-similarity-sri/curated/lyrics_input_header/lyrics_input.csv`
- Output JSONL:
  - `s3://spotify-genre-similarity-sri/curated/lyrics_by_track_sample/lyrics_sample.jsonl`

Run the job and confirm non-zero `lyrics_found` in logs.

## 9) Convert lyrics JSONL → Parquet (Glue job + crawler)
### Glue job: `job_convert_lyrics_jsonl_to_parquet` (Spark)
- Script: `glue/job_convert_lyrics_jsonl_to_parquet.py`
- Output: `s3://spotify-genre-similarity-sri/curated/lyrics_by_track_sample_parquet/` (partitioned by `genre`)

Run the job.

### Crawler: `crawler_curated_lyrics_sample`
- Target: `s3://spotify-genre-similarity-sri/curated/lyrics_by_track_sample_parquet/`
- Table: `curated_lyrics_by_track_sample_parquet`

Run the crawler.

## 10) Build lyrics-enriched dataset (Glue job + crawler)
### Glue job: `job_build_lyrics_enriched_by_genre` (Spark)
- Script: `glue/job_build_lyrics_enriched_by_genre.py`
- Output: `s3://spotify-genre-similarity-sri/curated/lyrics_enriched_by_genre/`

Run the job.

### Crawler (recommended): `crawler_curated_lyrics_enriched_by_genre`
- Target: `s3://spotify-genre-similarity-sri/curated/lyrics_enriched_by_genre/`
- Table: `curated_lyrics_enriched_by_genre`

Run the crawler.

## 11) Audio+lyrics evaluation (Glue job + crawler)
### Glue job: `job_eval_audio_lyrics_similarity` (Spark)
- Script: `glue/job_eval_audio_lyrics_similarity.py`
- Output: `s3://spotify-genre-similarity-sri/results/eval_audio_lyrics_similarity/`

Run the job.

### Crawler: `crawler_results_eval_audio_lyrics_similarity`
- Target: `s3://spotify-genre-similarity-sri/results/eval_audio_lyrics_similarity/`
- Table: `results_eval_audio_lyrics_similarity`

Run the crawler.

## 12) Build delta/flagged table for QuickSight (Athena CTAS)
Run `sql/07_delta_flagged_ctas.sql` to create:
- `results_eval_delta_audio_vs_audio_lyrics_flagged`

This table includes:
- `baseline_available` flag
- `delta_recall` and `delta_mrr`

## 13) QuickSight analysis → dashboard
Use `docs/QUICKSIGHT_DASHBOARD.md` to:
- create datasets
- build visuals + genre dropdown + zero reference line
- publish and export the dashboard PDF

## 14) Cost controls (Free Tier)
- Stop Glue **job runs** (nothing keeps running after completion).
- Delete or lifecycle-expire intermediate data under:
  - `athena-query-results/Unsaved/`
  - any scratch `curated/lyrics_input_*`
- Prefer SPICE with a small refresh schedule (or manual refresh) to avoid repeated Athena scans.