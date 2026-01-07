import sys
import random
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
args = getResolvedOptions(sys.argv, ["JOB_NAME"])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

DB = "spotify_similarity_db"
TABLE = "curated_tracks_by_genre"

OUT_S3 = "s3://spotify-genre-similarity-sri/results/eval_audio_similarity/"

FEATURES = [
    "danceability","energy","loudness","speechiness","acousticness",
    "instrumentalness","liveness","valence","tempo"
]

# Cost controls
# TOP_GENRES is set from job args above
MAX_TRACKS_PER_GENRE = 4000
N_QUERIES_PER_GENRE = 150   # number of query songs per genre
CANDIDATE_SAMPLE = 2500     # candidate pool sampled per genre for KNN (keeps it cheap)
TOP_K = 10

df = glueContext.create_dynamic_frame.from_catalog(database=DB, table_name=TABLE).toDF()

needed = ["id","genre","artist_id_primary"] + FEATURES
missing = [c for c in needed if c not in df.columns]
if missing:
    raise Exception(f"Missing required columns: {missing}")

# Clean rows
df = df.filter(F.col("id").isNotNull() & F.col("genre").isNotNull() & F.col("artist_id_primary").isNotNull())
for f in FEATURES:
    df = df.filter(F.col(f).isNotNull())

# Top genres
top_genres = _select_genres(df)
df = df.filter(F.col("genre").isin(top_genres))
# Sample tracks per genre
df = df.withColumn("rand", F.rand())
win = Window.partitionBy("genre").orderBy(F.col("rand"))
df = df.withColumn("rn", F.row_number().over(win)).filter(F.col("rn") <= MAX_TRACKS_PER_GENRE).drop("rn","rand")

# Collect per-genre data to driver (bounded by our sampling)
genre_groups = (
    df.select("genre","id","artist_id_primary", *FEATURES)
      .groupBy("genre")
      .agg(F.collect_list(F.struct("id","artist_id_primary", *FEATURES)).alias("tracks"))
      .collect()
)

rows = []

def vec(t):
    return np.array([float(t[f]) for f in FEATURES], dtype=np.float32)

for g in genre_groups:
    genre = g["genre"]
    tracks = g["tracks"]
    n = len(tracks)
    if n < (N_QUERIES_PER_GENRE + 50):
        continue

    # Candidate pool for neighbor search
    candidates = random.sample(tracks, min(CANDIDATE_SAMPLE, n))
    cand_ids = [t["id"] for t in candidates]
    cand_artist = {t["id"]: t["artist_id_primary"] for t in candidates}
    cand_mat = np.stack([vec(t) for t in candidates], axis=0)

    # Queries
    queries = random.sample(tracks, min(N_QUERIES_PER_GENRE, n))
    recall_hits = 0
    mrr_sum = 0.0
    q_count = 0

    for q in queries:
        qid = q["id"]
        q_artist = q["artist_id_primary"]
        qv = vec(q)

        # Compute Euclidean distance (cheap) and take TOP_K nearest excluding self if present
        dists = np.sqrt(((cand_mat - qv) ** 2).sum(axis=1))
        order = np.argsort(dists)

        # Build ranked neighbor list
        ranks_checked = 0
        first_hit_rank = None

        for idx in order:
            nid = cand_ids[int(idx)]
            if nid == qid:
                continue
            ranks_checked += 1
            if cand_artist[nid] == q_artist:
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

    recall_at_k = recall_hits / q_count
    mrr_at_k = mrr_sum / q_count

    rows.append((genre, int(q_count), int(TOP_K), float(recall_at_k), float(mrr_at_k)))

schema = T.StructType([
    T.StructField("genre", T.StringType(), False),
    T.StructField("n_queries", T.IntegerType(), False),
    T.StructField("k", T.IntegerType(), False),
    T.StructField("recall_at_k", T.DoubleType(), False),
    T.StructField("mrr_at_k", T.DoubleType(), False),
])

out = spark.createDataFrame(rows, schema=schema).withColumn("run_ts", F.current_timestamp())

(out.write.mode("overwrite").format("parquet").partitionBy("genre").save(OUT_S3))

job.commit()