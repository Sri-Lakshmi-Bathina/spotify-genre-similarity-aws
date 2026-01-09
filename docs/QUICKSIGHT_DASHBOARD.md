# QuickSight — Build the Final Dashboard (Analysis → Dashboard)

## Prerequisites (one-time)
1. **QuickSight account (us-east-1)** 
2. **Enable Athena access** in QuickSight:
   - QuickSight → *Manage QuickSight* → **Security & permissions**
   - Under **AWS services**, enable **Amazon Athena** and **AWS Glue**
   - Under **S3**, grant access to:
     - `s3://spotify-genre-similarity-sri/athena-query-results/`
     - `s3://spotify-genre-similarity-sri/results/`
     - `s3://spotify-genre-similarity-sri/curated/`
3. In Athena, confirm these tables return rows (database `spotify_similarity_db`):
   - `curated_tracks_by_genre`
   - `results_genre_predictors`
   - `results_eval_audio_similarity`
   - `results_eval_delta_audio_vs_audio_lyrics_flagged`

## A. Create datasets (QuickSight → Datasets)
For each table:
1. QuickSight → **Datasets** → **New dataset**
2. Choose **Athena**
3. Data source name (example): `athena_spotify_similarity`
4. Select:
   - Database: `spotify_similarity_db`
   - Table: pick one of the tables above
5. **Direct query** 
6. Click **Visualize**

Repeat until you have 4 datasets. You can build visuals across datasets in the same Analysis.

## B. Create an Analysis 
1. QuickSight → **Analyses** → **New analysis**
2. Add datasets:
   - `curated_tracks_by_genre` (genre distribution)
   - `results_genre_predictors` (predictor importance)
   - `results_eval_audio_similarity` (audio-only evaluation)
   - `results_eval_delta_audio_vs_audio_lyrics_flagged` (lyrics impact)

### Sheet layout recommendation 

#### Block 1 — Genre coverage (what data exists per genre)
Visual 1 (bar chart): **Tracks per genre**
- Dataset: `curated_tracks_by_genre`
- X: `genre`
- Y: `countDistinct(track_id)` 
- Sort: **Descending by countDistinct(track_id)**

#### Block 2 — Top predictors per genre (feature importance)
Visual 2 (horizontal bar chart): **Importance (Normalized)**
- Dataset: `results_genre_predictors`
- Y: `feature`
- X: `importance_norm` (aggregation: Sum)
- Add a **Genre filter control** (dropdown) to pick a genre
- Sort: **Descending by importance_norm**

#### Block 3 — Audio-only effectiveness (baseline)
Visual 3 (table): **Recall@10 and MRR@10 by genre**
- Dataset: `results_eval_audio_similarity`
- Columns: `genre`, `recall_at_k`, `mrr_at_k`, `n_queries`, `k`
- Sort: **Descending by recall_at_k**
- Optional conditional formatting: highlight low-performing genres

#### Block 4 — Lyrics impact (Audio+Lyrics − Audio)
Visual 4 (clustered bar or two visuals):
- Dataset: `results_eval_delta_audio_vs_audio_lyrics_flagged`
- Visual 4a: **ΔRecall@10 by genre** (bar)
- Visual 4b: **ΔMRR@10 by genre** (bar)
- X: `genre`
- Y: `delta_recall` or `delta_mrr`
- Color (optional): `baseline_available` (0/1)

**Add a Zero Reference Line** (for both delta charts):
- Select the visual → **Format visual**
- **Reference lines** → Add reference line at **0**
- Label: “No change (0)”
- This makes “improvement vs regression” immediately visible.

## C. Create a Genre dropdown control (correct way)
QuickSight requires a filter first, then you can add it as a control.

1. In the Analysis, choose **Filter** (left panel) → **Add filter**
2. Field: `genre` (from the dataset you want to filter, typically `results_genre_predictors`)
3. Filter type: **Filter list** (or “Custom filter” → “Equals”)
4. Apply to: choose **All visuals** on the sheet *or* select the visuals you want
5. After creating the filter:
   - Click the filter’s **…** menu → **Add to sheet**
   - Choose **Dropdown** (single select) and place it at the top
6. Rename the control label to: `Genre`

## D. Sorting and “Top N” behavior
- For bar charts:
  - Field well → click **genre** → **Sort** → Descending by your metric (count, delta, etc.)
- For tables:
  - Click the column header to sort; then “Freeze” in formatting if needed.

## E. Add an Outcomes text box (data science narrative)
1. Choose **Add** → **Text box**
2. Paste the “Outcomes” text from `docs/OUTCOMES_TEXT.md`
3. Keep it short: 5–8 bullets max, focused on measurable findings and limitations.

## F. Publish as a Dashboard
1. In the Analysis, click **Share** → **Publish dashboard**
2. Name: `Spotify Similarity — Genre Split, Predictors, Evaluation, Lyrics`
3. After publishing:
   - Dashboard → **Export** → **PDF** 
