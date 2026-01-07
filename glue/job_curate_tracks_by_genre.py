import sys
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql import functions as F

args = getResolvedOptions(sys.argv, ["JOB_NAME"])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

# ---------- INPUTS ----------
DB = "spotify_similarity_db"
TRACKS_TABLE = "raw_tracks"
ARTISTS_TABLE = "raw_artists"

# ---------- OUTPUT ----------
OUT_S3 = "s3://spotify-genre-similarity-sri/curated/tracks_by_genre/"
OUT_DB = "spotify_similarity_db"
OUT_TABLE = "curated_tracks_by_genre"

tracks = glueContext.create_dynamic_frame.from_catalog(database=DB, table_name=TRACKS_TABLE).toDF()
artists = glueContext.create_dynamic_frame.from_catalog(database=DB, table_name=ARTISTS_TABLE).toDF()

# --- Extract primary artist id from stringified list: "['abc']" -> "abc"
# Works for your sample format. If empty list, result will be null.
tracks = tracks.withColumn(
    "artist_id_primary",
    F.regexp_extract(F.col("id_artists"), r"^\['([^']+)'\]", 1)
)

# artists.genres was crawled as STRING like "['genre1', 'genre2']" or "[]"
artists_norm = artists.withColumn("genres_str", F.col("genres").cast("string"))

# Remove [ ] and all single quotes, then split on commas
genres_no_brackets = F.regexp_replace(F.col("genres_str"), r"^\[|\]$", "")
genres_no_quotes = F.regexp_replace(genres_no_brackets, r"'", "")
genres_trimmed = F.trim(genres_no_quotes)

artists_norm = artists_norm.withColumn(
    "artist_genres_arr",
    F.when(F.length(genres_trimmed) == 0, F.array().cast("array<string>"))
     .otherwise(F.split(genres_trimmed, r"\s*,\s*"))
)

artists_sel = artists_norm.select(
    F.col("id").alias("artist_id_primary"),
    F.col("name").alias("artist_name_primary"),
    F.col("artist_genres_arr").alias("artist_genres")
)

joined = tracks.join(artists_sel, on="artist_id_primary", how="left")

# Explode genres to create one row per (track, genre)
# Filter out tracks where genres are missing/empty
joined = joined.withColumn("genre", F.explode_outer(F.col("artist_genres")))
joined = joined.withColumn("genre", F.lower(F.trim(F.col("genre"))))
joined = joined.filter(F.col("genre").isNotNull() & (F.col("genre") != ""))

# Derive release_year
if "release_date" in joined.columns:
    joined = joined.withColumn(
        "release_year",
        F.when(F.length(F.col("release_date")) >= 4, F.col("release_date").substr(1, 4).cast("int")).otherwise(F.lit(None))
    )
else:
    joined = joined.withColumn("release_year", F.lit(None).cast("int"))

# Select columns for curated table
keep_cols = []
for c in [
    "id", "name", "popularity", "duration_ms", "explicit", "artists", "id_artists",
    "artist_id_primary", "artist_name_primary",
    "release_date", "release_year",
    "danceability", "energy", "key", "loudness", "mode", "speechiness",
    "acousticness", "instrumentalness", "liveness", "valence", "tempo",
    "time_signature",
    "genre"
]:
    if c in joined.columns:
        keep_cols.append(c)

curated = joined.select(*keep_cols).dropDuplicates(["id", "genre"])

# Write Parquet partitioned by genre
(
    curated
    .repartition("genre")
    .write
    .mode("overwrite")
    .format("parquet")
    .partitionBy("genre")
    .save(OUT_S3)
)

job.commit()
