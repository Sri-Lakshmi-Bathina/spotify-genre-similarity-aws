# Genre selection options (Glue jobs)

This project defaults to evaluating **TOP_N genres** (highest track counts). This is the recommended mode for:
- Fast runs
- Lower Glue/Athena costs (free-tier friendly)
- Stable genre coverage (no randomness)

If you want broader genre coverage, you can optionally include a *variety* slice.

## Default mode (recommended): `top_n`

All three Spark jobs below use **TOP_N genres** by track count:

- `job_genre_predictors.py`
- `job_eval_audio_similarity.py`
- `job_eval_audio_lyrics_similarity.py`

### Job parameters (can be set in Glue → Job details → Advanced properties → Job parameters)

| Parameter | Default | Meaning |
|---|---:|---|
| `--GENRE_MODE` | `top_n` | `top_n` or `top_n_plus_variety` |
| `--TOP_GENRES` | job-specific | Number of top genres by track count |
| `--MIN_TRACKS_PER_GENRE` | `500` | Excludes very small genres |
| `--SEED` | `42` | Reproducible randomness (only affects variety mode) |
| `--VARIETY_GENRES` | `10` | Extra random genres to add in variety mode |

## Optional mode: `top_n_plus_variety`

This mode selects:
1) The TOP_N genres by track count, **plus**
2) VARIETY_GENRES additional genres sampled randomly from the remaining eligible genres.

Use it when your goal is to demonstrate the model’s behavior beyond the “largest” genres.

### Example configuration
- `--GENRE_MODE top_n_plus_variety`
- `--TOP_GENRES 10`
- `--VARIETY_GENRES 10`
- `--MIN_TRACKS_PER_GENRE 500`
- `--SEED 42`

## Optional Athena helper

If you prefer genre selection to be driven by Athena (and documented as SQL), run:

- `sql/optional/01_genre_list_topn_plus_variety_ctas.sql`

This creates a reusable table of selected genres with a `reason` column (`top_n` vs `variety`).
