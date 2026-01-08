<h1 align="center">🎧 Spotify Genre-Split Similarity on AWS: Predictors, Evaluation, and Lyrics Impact </h1>

<p align="center">
  <img src="https://img.shields.io/badge/Amazon%20S3-Data%20Lake-blue?logo=amazonaws&logoColor=white" />
  <img src="https://img.shields.io/badge/AWS%20Glue-ETL%20%2B%20Spark-orange?logo=amazonaws&logoColor=white" />
  <img src="https://img.shields.io/badge/Athena-Serverless%20SQL-yellow?logo=amazonaws&logoColor=white" />
  <img src="https://img.shields.io/badge/QuickSight-Dashboarding-informational?logo=amazonaws&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-Lyrics%20API-green?logo=python&logoColor=white" />
</p>

End-to-end analytics workflow on **AWS S3 + Glue + Athena + QuickSight** for a genre-aware song similarity use case.

---

## 📌 Project Overview

This project builds a **modern, serverless analytics pipeline on AWS** to answer a music-recommendation use case:

### Use Case
1. **Split Spotify tracks by genre** and find the **top audio predictors** (song metrics like tempo, loudness, energy, etc.) that drive similarity *within each genre*.
2. Build and evaluate **similarity ranking** (Top-K neighbors) using:
   - **Audio-only similarity**
   - **Audio + Lyrics similarity** (lyrics fetched via a free API)
3. Visualize outcomes in **Amazon QuickSight**.

Services used:
- **S3** (raw/curated/results zones)
- **Glue** (ETL + evaluation jobs)
- **Athena** (serverless SQL + query outputs)
- **QuickSight** (final dashboards)

---

## ⚙️ Tech Stack

| Component | Tool |
|---|---|
| Data Lake | Amazon S3 |
| ETL / Compute | AWS Glue (PySpark + Python Shell) |
| Query Engine | Amazon Athena |
| BI / Dashboard | Amazon QuickSight |
| Lyrics Retrieval | lrclib API |
| Language | Python |

---

## 🧾 Dataset

- Source (Kaggle): `Top Spotify Songs 2023`
- Link: https://www.kaggle.com/datasets/nelgiriyewithana/top-spotify-songs-2023
- Raw inputs used:
  - `raw/tracks/tracks.csv`
  - `raw/artists/artists.csv`

---

## 🏗️ Architecture 
**S3 (raw)**  **Glue Crawlers → (catalog)** → **Glue Jobs (curation + evaluation)** → **S3 (curated/results)** → **Athena Query** → **QuickSight Analysis → Dashboard**
<img width="1001" height="311" alt="Spotify_architecture drawio" src="https://github.com/user-attachments/assets/e5fe9420-803b-4d73-84ef-f9abc73730d3" />

---

## Prerequisites
- AWS Account (Free Tier), Region: `us-east-1`
- S3 bucket created: `spotify-genre-similarity-sri`
- Athena:
  - Workgroup: `primary`
  - Database: `spotify_similarity_db`
  - Query results location: `s3://spotify-genre-similarity-sri/athena-query-results/`
- IAM role for Glue: `AWSGlueServiceRole-spotify-genre-similarity`

---

## 📂 Repository structure
- `glue/` — Glue job scripts 
- `sql/` — Athena queries used across the workflow (setup, validation, QA, CTAS)
- `docs/` — Runbook, dashboard build notes, and exported dashboard PDFs
- `iam/` — Glue service role S3 access policy used in this project

---

## S3 layout 
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
<img width="1667" height="472" alt="S3 objects" src="https://github.com/user-attachments/assets/727fbe07-3e53-4831-80aa-1896a81b37d6" />
<img width="1639" height="344" alt="S3_raw" src="https://github.com/user-attachments/assets/9c4475c3-483b-4bde-902a-607df5ca646e" />
<img width="1636" height="522" alt="S3_curated" src="https://github.com/user-attachments/assets/2fcc1861-351a-41b5-8001-b5d8a4cfce69" />
<img width="1636" height="451" alt="S3_results" src="https://github.com/user-attachments/assets/d40bdb66-54ed-411c-863a-28f802de7417" />

---

## Glue jobs 
1. `job_curate_tracks_by_genre.py` (Spark): build `curated/tracks_by_genre/` partitioned by `genre`
2. `job_genre_predictors.py` (Spark): compute per-genre “predictor importance” (feature contributions)
3. `job_eval_audio_similarity.py` (Spark): evaluate audio-only similarity (Recall@K, MRR@K)
4. `job_fetch_lyrics_sample.py` (Python Shell): call lyrics API (LRCLIB) and write JSONL to S3
5. `job_convert_lyrics_jsonl_to_parquet.py` (Spark): convert JSONL → parquet partitioned by `genre`
6. `job_build_lyrics_enriched_by_genre.py` (Spark): join curated tracks + lyrics
7. `job_eval_audio_lyrics_similarity.py` (Spark): evaluate audio+lyrics similarity (Recall@K, MRR@K)
<img width="1421" height="637" alt="Glue_jobs" src="https://github.com/user-attachments/assets/8fd341c3-9a23-4112-8d28-60f59c5d9b4f" />

---

## Glue crawlers 
This repo documents the crawlers used. If you are recreating from scratch, create crawlers for:
- `raw/tracks/` → `raw_tracks`
- `raw/artists/` → `raw_artists`
- `curated/tracks_by_genre/` → `curated_tracks_by_genre`
- `results/genre_predictors/` → `results_genre_predictors`
- `results/eval_audio_similarity/` → `results_eval_audio_similarity`
- `curated/lyrics_by_track_sample_parquet/` → `curated_lyrics_by_track_sample_parquet`
- `curated/lyrics_enriched_by_genre/` → `curated_lyrics_enriched_by_genre` 
- `results/eval_audio_lyrics_similarity/` → `results_eval_audio_lyrics_similarity`
> Note: The “delta/flagged” tables are created via Athena CTAS in `sql/07_delta_flagged_ctas.sql`, so a crawler is not required.
<img width="1414" height="505" alt="Tables" src="https://github.com/user-attachments/assets/2cd49c45-f830-42f1-9347-b0c48d3eebcc" />

---

## 🔁 Pipeline Flow (End-to-End)

### Phase A — Catalog Raw Data
1. Upload CSVs into S3 `raw/`
2. Run Glue Crawlers:
   - `crawler_raw_tracks` → `raw_tracks`
   - `crawler_raw_artists` → `raw_artists`

### Phase B — Curate Tracks by Genre
3. Glue ETL (PySpark):
   - **Job:** `job_curate_tracks_by_genre`
   - **Output:** `curated/tracks_by_genre/genre=.../` (Parquet)
4. Crawler:
   - `crawler_curated_tracks_by_genre` → `curated_tracks_by_genre`

### Phase C — Top Predictors per Genre
5. Glue job:
   - **Job:** `job_genre_predictors`
   - **Input:** `curated_tracks_by_genre`
   - **Output:** `results/genre_predictors/` (Parquet)
6. Crawler:
   - `crawler_results_genre_predictors` → `results_genre_predictors`

### Phase D — Evaluate Audio Similarity
7. Glue job:
   - **Job:** `job_eval_audio_similarity`
   - **Output:** `results/eval_audio_similarity/` (Parquet)
8. Crawler:
   - `crawler_results_eval_audio_similarity` → `results_eval_audio_similarity`

### Phase E — Lyrics Extension
9. Create a safe input sample for lyrics (Athena UNLOAD → CSV):
   - Output: `curated/lyrics_input_header/lyrics_input.csv`
10. Fetch lyrics (Python Shell):
   - **Job:** `job_fetch_lyrics_sample`
   - **API:** `https://lrclib.net/api/search?q={q}`
   - Output: `curated/lyrics_by_track_sample/lyrics_sample.jsonl`
11. Convert JSONL → Parquet (PySpark):
   - **Job:** `job_convert_lyrics_jsonl_to_parquet`
   - Output: `curated/lyrics_by_track_sample_parquet/genre=.../`
12. Crawler:
   - `crawler_curated_lyrics_sample` → `curated_lyrics_by_track_sample_parquet`
13. Build a clean, joined/enriched dataset (tracks + lyrics):
   - **Job:** `job_build_lyrics_enriched_by_genre`
   - Output: `curated/lyrics_enriched_by_genre/genre=.../`

### Phase F — Evaluate Audio + Lyrics Similarity
14. Glue job:
   - **Job:** `job_eval_audio_lyrics_similarity`
   - Output: `results/eval_audio_lyrics_similarity/` (Parquet)
15. Crawler:
   - `crawler_results_eval_audio_lyrics_similarity` → `results_eval_audio_lyrics_similarity`

### Phase G — Compare (Audio vs Audio+Lyrics)
16. Athena CTAS builds the comparison table:
   - `results_eval_delta_audio_vs_audio_lyrics_flagged`
   - Adds:
     - `baseline_available` (1 if audio baseline exists for that genre)
     - `delta_recall`, `delta_mrr`

---

## 🧠 Similarity + Predictors Method (Concept)

### 1) Predictors (Top features per genre)
For each genre, we compute feature importance across core audio metrics (e.g., `tempo`, `loudness`, `energy`, `acousticness`, etc.) and store:
- `importance_raw`, `importance_abs`, `importance_norm`

### 2) Similarity ranking (Top-K neighbors)
Given a query track, we rank candidate tracks **within the same genre** using a similarity score.

**Audio-only similarity:** distance over standardized audio features  
**Audio+Lyrics similarity:** blended score: score = alpha * audio_similarity + (1 - alpha) * lyrics_similarity

---

## ✅ Evaluation (Effectiveness)

We evaluate “is this working?” with ranking metrics:

- **Recall@K**: Does the Top-K contain expected neighbors?
- **MRR@K**: How high are relevant neighbors ranked?

We compute these for:
- `results_eval_audio_similarity`
- `results_eval_audio_lyrics_similarity`

Then compare deltas:
- `delta_recall = recall_audio_lyrics - recall_audio`
- `delta_mrr   = mrr_audio_lyrics   - mrr_audio`

**Important:** Some genres in the lyrics run may not exist in the audio baseline run; `baseline_available=0` prevents misleading deltas.

---

## 🎯 Sampling Strategy (Default + Alternative)

### ✅ Default (Recommended): Top-N Genres
- Most stable + interpretable
- Ensures enough data per genre
- Reduces noise from tiny genres

### Alternative: “Variety Sampling” Across Genres
If you want broader coverage (closer to your local Python script idea), use a sampling strategy such as:
- **Stratified sample**: take `X` tracks per genre for the top `M` genres
- **Hybrid**: Top-N genres + `Y` long-tail genres (random) to increase diversity

This project includes both patterns as options in the SQL/ETL approach (see `/athena/`).

---

## 📊 QuickSight Dashboard

QuickSight datasets used:
1. `curated_tracks_by_genre` → genre distribution
2. `results_genre_predictors` → top predictors by genre
3. `results_eval_audio_similarity` → audio effectiveness metrics
4. `results_eval_delta_audio_vs_audio_lyrics_flagged` → lyrics impact (with baseline flag)

<img width="1170" height="1042" alt="Screenshot 2026-01-07 at 7 05 34 PM" src="https://github.com/user-attachments/assets/5683ca88-1f4c-46ff-8d06-3c81fe7e798f" />

---

## 📌 Key Outcomes (Suggested Text Box for Dashboard)

**Outcomes Summary**
- Built a serverless pipeline that curates Spotify tracks by genre and computes feature-driven similarity within each genre.
- Identified that top similarity drivers vary by genre (e.g., rhythm-forward genres skew toward tempo/energy while others weight loudness/acousticness).
- Audio-only similarity achieved measurable ranking performance (Recall@K, MRR@K) for several high-volume genres.
- Adding lyrics improved Recall@K for some genres, but reduced it for others—highlighting that lyrics can introduce semantic noise when the sample is sparse or when artist/title text dominates retrieval.
- Introduced `baseline_available` to prevent false conclusions when an “audio baseline” evaluation is missing for a genre in the comparison dataset.

---

## License
MIT
