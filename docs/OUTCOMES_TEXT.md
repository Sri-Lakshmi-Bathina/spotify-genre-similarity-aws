# Outcomes (Text Box for the Dashboard)

**Objective:** Evaluate a genre-aware song similarity approach using audio features, and measure whether adding lyrics improves ranking quality.

- **Genre segmentation matters:** We first partitioned the dataset by genre to reduce “apples vs oranges” comparisons and make similarity scoring more musically coherent within each genre.
- **Key audio predictors are genre-dependent:** Feature importance varies by genre, but tempo and loudness frequently emerge as strong drivers of similarity (with secondary contributions from energy, acousticness, and valence).
- **Audio-only baseline is measurable:** Using per-genre evaluation, we quantified ranking quality with **Recall@10** (coverage of true neighbors) and **MRR@10** (how early the best matches appear).
- **Lyrics extension has mixed impact:** On the tested sample, adding lyrics improved Recall@10 for some genres but reduced it for others, indicating that lyric similarity can introduce noise when the API returns incomplete or inconsistent text.
- **Interpretation:** Lyrics can help when lyrical themes align with genre and artist style, but it can hurt when lyrics are missing, truncated, or overly generic (e.g., repeated choruses), shifting similarity away from audio structure.
- **Practical takeaway:** Lyrics should be treated as an optional signal with **quality gates** (minimum lyric length, language detection, deduplication) and **tunable weighting** between audio and lyrics.
- **Next steps:** Expand genre coverage beyond “top N” by running stratified sampling across more genres, increase evaluation queries per genre, and test multiple weights (alpha) to identify where lyrics consistently adds value.
