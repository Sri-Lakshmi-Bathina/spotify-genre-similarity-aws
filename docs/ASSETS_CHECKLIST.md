# Assets checklist (to ensure nothing is missing)

Use this checklist to verify your AWS environment matches what the repository expects.

## 1) S3 bucket + prefixes (project storage)

Bucket: `spotify-genre-similarity-sri`

- `s3://spotify-genre-similarity-sri/raw/`
  - `raw/tracks/` (source CSV)
  - `raw/artists/` (source CSV)
- `s3://spotify-genre-similarity-sri/curated/`
  - `curated/tracks_by_genre/` (Parquet, partitioned by `genre`)
  - `curated/lyrics_input_header/` (lyrics input CSV with header)
  - `curated/lyrics_by_track_sample/` (JSONL from LRCLIB)
  - `curated/lyrics_by_track_sample_parquet/` (Parquet, partitioned by `genre`)
  - `curated/lyrics_enriched_by_genre/` (joined dataset used for Audio+Lyrics evaluation)
- `s3://spotify-genre-similarity-sri/results/`
  - `results/genre_predictors/`
  - `results/eval_audio_similarity/`
  - `results/eval_audio_lyrics_similarity/`
  - `results/eval_delta_audio_vs_audio_lyrics/` (Athena CTAS)
  - `results/eval_delta_audio_vs_audio_lyrics_flagged/` (Athena CTAS; adds baseline flag)
- `s3://spotify-genre-similarity-sri/athena-query-results/` (Athena workgroup results)

## 2) Glue Data Catalog

Database:
- `spotify_similarity_db`

Tables (typical final set):
- `raw_tracks`
- `raw_artists`
- `curated_tracks_by_genre`
- `curated_lyrics_by_track_sample_parquet` (or similarly named)
- `curated_lyrics_enriched_by_genre`
- `results_genre_predictors`
- `results_eval_audio_similarity`
- `results_eval_audio_lyrics_similarity`
- `results_eval_delta_audio_vs_audio_lyrics` (CTAS)
- `results_eval_delta_audio_vs_audio_lyrics_flagged` (CTAS)

> Note: The `results_eval_delta_*` tables are created by Athena **CTAS** statements, so they appear in the Glue Catalog even without a crawler.

## 3) Glue crawlers (on-demand; default schema change policies)

From your notes (no custom schema policy changes):

- `crawler_raw_tracks` → `raw_tracks` (CSV)
- `crawler_raw_artists` → `raw_artists` (CSV)
- `crawler_curated_tracks_by_genre` → `curated_tracks_by_genre` (Parquet)

- `crawler_results_genre_predictors` → `results_genre_predictors` (Parquet)
- `crawler_results_eval_audio_similarity` → `results_eval_audio_similarity` (Parquet)
- `crawler_results_eval_audio_lyrics_similarity` → `results_eval_audio_lyrics_similarity` (Parquet)

- `crawler_curated_lyrics_sample` → `curated_lyrics_by_track_sample_parquet` (Parquet)

## 4) Glue jobs (7 total)

Spark (Glue ETL):
- `job_curate_tracks_by_genre`
- `job_genre_predictors`
- `job_eval_audio_similarity`
- `job_convert_lyrics_jsonl_to_parquet`
- `job_build_lyrics_enriched_by_genre`
- `job_eval_audio_lyrics_similarity`

Python Shell:
- `job_fetch_lyrics_sample`

Genre scope control (default **TOP_N**; optional variety):
- See `docs/GENRE_SELECTION.md`

## 5) IAM

Role:
- `AWSGlueServiceRole-spotify-genre-similarity`

Policies:
- AWS managed: `AWSGlueServiceRole`
- Inline policies to allow the role to:
  - Read/write the project S3 bucket prefixes (`raw/`, `curated/`, `results/`, `athena-query-results/`)
  - Access Glue/Athena as needed for the jobs

Repository copies:
- `iam/GlueS3Access-spotify-genre-similarity-sri.json` (inline policy)

## 6) Athena

- Workgroup: `primary`
- Database: `spotify_similarity_db`
- Query results: `s3://spotify-genre-similarity-sri/athena-query-results/`

Repository:
- `sql/*.sql` (core statements)
- `sql/optional/*.sql` (optional variety sampling)

## 7) QuickSight (dashboard layer)

Datasets used:
- `curated_tracks_by_genre` (distribution)
- `results_genre_predictors` (top predictors per genre)
- `results_eval_audio_similarity` (baseline evaluation)
- `results_eval_delta_audio_vs_audio_lyrics_flagged` (lyrics impact with baseline flag)

Docs:
- `docs/QUICKSIGHT_DASHBOARD.md`
