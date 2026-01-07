import sys
import numpy as np
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql import types as T
from pyspark.sql.window import Window

# -------------------------
# Runtime parameters (Glue job arguments)
# -------------------------
import sys

def _get_cli_arg(name: str, default: str):
    """Read Glue-style args: --NAME value"""
    flag = f"--{name}"
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default

TOP_GENRES = int(_get_cli_arg("TOP_GENRES", "10"))
GENRE_MODE = _get_cli_arg("GENRE_MODE", "top_n")  # top_n | top_n_plus_variety
VARIETY_GENRES = int(_get_cli_arg("VARIETY_GENRES", "10"))
MIN_TRACKS_PER_GENRE = int(_get_cli_arg("MIN_TRACKS_PER_GENRE", "500"))
SEED = int(_get_cli_arg("SEED", "42"))
def _select_genres(df):
    """Return a list of genres based on configured selection mode."""
    gcounts = (df.groupBy("genre").count()
                 .filter(F.col("genre").isNotNull())
                 .filter(F.col("count") >= F.lit(MIN_TRACKS_PER_GENRE))
                 .orderBy(F.col("count").desc()))
    top = gcounts.limit(TOP_GENRES).select("genre")
    if GENRE_MODE == "top_n":
        return [r["genre"] for r in top.collect()]

    if GENRE_MODE == "top_n_plus_variety":
        rest = (gcounts.join(top, on="genre", how="left_anti")
                      .orderBy(F.rand(SEED))
                      .limit(VARIETY_GENRES)
                      .select("genre"))
        final_df = top.unionByName(rest).distinct()
        return [r["genre"] for r in final_df.collect()]

    raise ValueError(f"Unsupported GENRE_MODE={GENRE_MODE}. Use top_n or top_n_plus_variety.")
from pyspark.ml.feature import Tokenizer, HashingTF, IDF
from pyspark.ml.linalg import SparseVector

args = getResolvedOptions(sys.argv, ["JOB_NAME"])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

DB = "spotify_similarity_db"

TRACKS_TABLE = "curated_tracks_by_genre"
LYRICS_TABLE = "curated_lyrics_enriched_by_genre"  # <-- change here only if needed

OUT_S3 = "s3://spotify-genre-similarity-sri/results/eval_audio_lyrics_similarity/"

# Controls
TOP_K = 10
ALPHA = 0.8                 # weight for audio vs lyrics
# TOP_GENRES is set from job args above
MIN_TRACKS_PER_GENRE = 30   # skip genres with fewer tracks
N_QUERIES_PER_GENRE = 100   # queries per genre (sampled)
CANDIDATE_SAMPLE = 400      # candidates per genre (sampled, cheap)

AUDIO_FEATURES = [
    "danceability","energy","loudness","speechiness","acousticness",
    "instrumentalness","liveness","valence","tempo"
]

t = glueContext.create_dynamic_frame.from_catalog(database=DB, table_name=TRACKS_TABLE).toDF()
l = glueContext.create_dynamic_frame.from_catalog(database=DB, table_name=LYRICS_TABLE).toDF()

# Join on (track_id/genre) to ensure we compare within the same genre bucket
df = (
    t.select(F.col("id").alias("track_id"), "genre", "artist_id_primary", *AUDIO_FEATURES)
     .join(l.select("track_id", "genre", "lyrics", "lyrics_found"), on=["track_id","genre"], how="inner")
)

# Keep only rows with lyrics
df = df.filter(F.col("lyrics_found") == True).filter(F.col("lyrics").isNotNull())

# Ensure features not null
for c in AUDIO_FEATURES:
    df = df.filter(F.col(c).isNotNull())

    # Select genres for evaluation
    top_genres = _select_genres(df)
    df = df.filter(F.col("genre").isin(top_genres))
# ---------- Build lyrics TF-IDF vectors (Spark ML) ----------
tok = Tokenizer(inputCol="lyrics", outputCol="words")
htf = HashingTF(inputCol="words", outputCol="tf", numFeatures=4096)
idf = IDF(inputCol="tf", outputCol="lyr_vec")

tmp = tok.transform(df)
tmp = htf.transform(tmp)
idf_model = idf.fit(tmp)
tmp = idf_model.transform(tmp)

# We only need: track_id, genre, artist_id_primary, audio features, lyrics vector
tmp = tmp.select("track_id","genre","artist_id_primary", *AUDIO_FEATURES, "lyr_vec")

# ---------- Collect per-genre into driver (small by design) ----------
genre_groups = (
    tmp.groupBy("genre")
       .agg(F.collect_list(F.struct("track_id","artist_id_primary", *AUDIO_FEATURES, "lyr_vec")).alias("rows"))
       .collect()
)

def sparse_to_unit_dense(v: SparseVector):
    # Convert to dense unit vector (cosine); safe for small evaluation sizes
    arr = np.zeros(v.size, dtype=np.float32)
    if v.numNonzeros() > 0:
        arr[v.indices] = v.values
        n = np.linalg.norm(arr)
        if n > 0:
            arr = arr / n
    return arr

def zscore(mat: np.ndarray):
    mu = mat.mean(axis=0)
    sd = mat.std(axis=0)
    sd[sd == 0] = 1.0
    return (mat - mu) / sd

rows_out = []

for g in genre_groups:
    genre = g["genre"]
    rows = g["rows"]
    n = len(rows)
    if n < MIN_TRACKS_PER_GENRE:
        continue

    # Build arrays
    ids = [r["track_id"] for r in rows]
    artists = [r["artist_id_primary"] for r in rows]
    audio = np.array([[float(r[f]) for f in AUDIO_FEATURES] for r in rows], dtype=np.float32)
    audio = zscore(audio)
    # unit-normalize audio for cosine
    an = np.linalg.norm(audio, axis=1, keepdims=True)
    an[an == 0] = 1.0
    audio_u = audio / an

    lyr_u = np.stack([sparse_to_unit_dense(r["lyr_vec"]) for r in rows], axis=0)

    # Candidate sampling (cheap)
    rng = np.random.default_rng(42)
    cand_idx = rng.choice(n, size=min(CANDIDATE_SAMPLE, n), replace=False)

    # Query sampling
    q_idx = rng.choice(n, size=min(N_QUERIES_PER_GENRE, n), replace=False)

    recall_hits = 0
    mrr_sum = 0.0
    q_count = 0

    for qi in q_idx:
        q_artist = artists[qi]

        # Cosine similarities against candidates
        a_sim = (audio_u[cand_idx] @ audio_u[qi])
        l_sim = (lyr_u[cand_idx] @ lyr_u[qi])
        score = ALPHA * a_sim + (1.0 - ALPHA) * l_sim

        order = np.argsort(-score)  # descending
        ranks_checked = 0
        first_hit_rank = None

        for oi in order:
            ci = int(cand_idx[int(oi)])
            if ids[ci] == ids[qi]:
                continue
            ranks_checked += 1
            if artists[ci] == q_artist:
                first_hit_rank = ranks_checked
                break
            if ranks_checked >= TOP_K:
                break

        if first_hit_rank is not None:
            recall_hits += 1
            mrr_sum += 1.0 / float(first_hit_rank)

        q_count += 1

    if q_count == 0:
        continue

    rows_out.append((
        genre,
        int(n),
        int(q_count),
        int(TOP_K),
        float(ALPHA),
        float(recall_hits / q_count),
        float(mrr_sum / q_count)
    ))

schema = T.StructType([
    T.StructField("genre", T.StringType(), False),
    T.StructField("n_tracks_in_genre", T.IntegerType(), False),
    T.StructField("n_queries", T.IntegerType(), False),
    T.StructField("k", T.IntegerType(), False),
    T.StructField("alpha_audio_weight", T.DoubleType(), False),
    T.StructField("recall_at_k", T.DoubleType(), False),
    T.StructField("mrr_at_k", T.DoubleType(), False),
])

outdf = spark.createDataFrame(rows_out, schema=schema).withColumn("run_ts", F.current_timestamp())

(outdf.write.mode("overwrite").format("parquet").partitionBy("genre").save(OUT_S3))

job.commit()