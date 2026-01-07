import sys
import random
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql import types as T

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

OUT_S3 = "s3://spotify-genre-similarity-sri/results/genre_predictors/"
RUN_TS = F.current_timestamp()

# Features to consider (must exist in curated table)
FEATURES = [
    "danceability","energy","loudness","speechiness","acousticness",
    "instrumentalness","liveness","valence","tempo"
]

# Cost controls
# TOP_GENRES is set from job args above
MAX_TRACKS_PER_GENRE = 3000 # sample tracks per genre
PAIRS_PER_GENRE = 30000     # sampled pairs for training proxy model

df = glueContext.create_dynamic_frame.from_catalog(database=DB, table_name=TABLE).toDF()

# Ensure required columns exist
needed = ["id","genre","artist_id_primary"] + FEATURES
missing = [c for c in needed if c not in df.columns]
if missing:
    raise Exception(f"Missing required columns in curated table: {missing}. Found: {df.columns}")

# Basic cleanup: drop rows with nulls in key columns / features
for c in ["id","genre","artist_id_primary"]:
    df = df.filter(F.col(c).isNotNull())

for f in FEATURES:
    df = df.filter(F.col(f).isNotNull())

# Pick top genres by row count
top_genres = _select_genres(df)
df = df.filter(F.col("genre").isin(top_genres))
# Sample tracks per genre for cost control
# Use a window + random order
w = F.window  # just to avoid unused warnings in some environments

df = df.withColumn("rand", F.rand())
from pyspark.sql.window import Window
win = Window.partitionBy("genre").orderBy(F.col("rand"))
df = df.withColumn("rn", F.row_number().over(win)).filter(F.col("rn") <= MAX_TRACKS_PER_GENRE).drop("rn","rand")

# Collect per-genre track records (limited) to driver for pair sampling
# This is feasible because we capped tracks/genre.
genre_groups = (
    df.select("genre","id","artist_id_primary", *FEATURES)
      .groupBy("genre")
      .agg(F.collect_list(F.struct("id","artist_id_primary", *FEATURES)).alias("tracks"))
      .collect()
)

rows = []

def vec(t):
    return [float(t[f]) for f in FEATURES]

# Simple pairwise learning proxy:
# Create pairs (a,b), label=1 if same artist else 0
# Use a logistic regression in closed-form-ish way by fitting weights via correlation between delta features and label.
# (Keeps dependencies light; Glue ML libs aren't guaranteed.)
#
# We compute per-feature: weight = (mean(|delta| for negatives) - mean(|delta| for positives))
# Smaller deltas for positives -> larger positive weight (after sign flip).
#
# This yields an interpretable "predictor importance" without heavy ML dependencies.

for g in genre_groups:
    genre = g["genre"]
    tracks = g["tracks"]
    n = len(tracks)
    if n < 50:
        continue

    # Index by artist to help sample positives
    by_artist = {}
    for t in tracks:
        by_artist.setdefault(t["artist_id_primary"], []).append(t)

    artists = list(by_artist.keys())
    if len(artists) < 5:
        continue

    pos_deltas = [0.0]*len(FEATURES)
    neg_deltas = [0.0]*len(FEATURES)
    pos_cnt = 0
    neg_cnt = 0

    # Sample pairs
    for _ in range(PAIRS_PER_GENRE):
        # 50/50 attempt to draw positive vs negative
        if random.random() < 0.5:
            # positive (same artist)
            a_id = random.choice(artists)
            if len(by_artist[a_id]) < 2:
                continue
            t1, t2 = random.sample(by_artist[a_id], 2)
            d = [abs(v1 - v2) for v1, v2 in zip(vec(t1), vec(t2))]
            pos_deltas = [p + x for p, x in zip(pos_deltas, d)]
            pos_cnt += 1
        else:
            # negative (different artist)
            a1, a2 = random.sample(artists, 2)
            t1 = random.choice(by_artist[a1])
            t2 = random.choice(by_artist[a2])
            d = [abs(v1 - v2) for v1, v2 in zip(vec(t1), vec(t2))]
            neg_deltas = [p + x for p, x in zip(neg_deltas, d)]
            neg_cnt += 1

    if pos_cnt == 0 or neg_cnt == 0:
        continue

    pos_mean = [x/pos_cnt for x in pos_deltas]
    neg_mean = [x/neg_cnt for x in neg_deltas]

    # Importance: how much more the feature changes in negatives than positives
    # Larger => better predictor
    importance = [nm - pm for nm, pm in zip(neg_mean, pos_mean)]

    # Normalize to sum to 1 for easy comparison
    s = sum([abs(x) for x in importance]) or 1.0
    norm = [x/s for x in importance]

    for feat, imp, w in zip(FEATURES, importance, norm):
        rows.append((genre, feat, float(imp), float(abs(imp)), float(w)))

schema = T.StructType([
    T.StructField("genre", T.StringType(), False),
    T.StructField("feature", T.StringType(), False),
    T.StructField("importance_raw", T.DoubleType(), False),
    T.StructField("importance_abs", T.DoubleType(), False),
    T.StructField("importance_norm", T.DoubleType(), False),
])

out = spark.createDataFrame(rows, schema=schema).withColumn("run_ts", F.current_timestamp())

# Write Parquet output
(out
 .repartition("genre")
 .write
 .mode("overwrite")
 .format("parquet")
 .partitionBy("genre")
 .save(OUT_S3)
)

job.commit()