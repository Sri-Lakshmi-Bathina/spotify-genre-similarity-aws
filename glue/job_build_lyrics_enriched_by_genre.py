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

DB = "spotify_similarity_db"

TRACKS_TABLE = "curated_tracks_by_genre"
LYRICS_TABLE = "curated_lyrics_by_track_sample_parquet"

OUT_S3 = "s3://spotify-genre-similarity-sri/curated/lyrics_enriched_by_genre/"

t = glueContext.create_dynamic_frame.from_catalog(database=DB, table_name=TRACKS_TABLE).toDF()
l = glueContext.create_dynamic_frame.from_catalog(database=DB, table_name=LYRICS_TABLE).toDF()

# Keep only what we need from lyrics and de-dup by track_id
l = (l.select("track_id", "lyrics", "lyrics_found")
       .dropDuplicates(["track_id"]))

# Join: authoritative genre comes from curated_tracks_by_genre
j = (t.select(F.col("id").alias("track_id"), "genre", "artist_id_primary", "artist_name_primary")
       .join(l, on="track_id", how="inner"))

j = j.withColumn("genre", F.lower(F.trim(F.col("genre"))))

# Write clean parquet partitioned by genre
(
    j.repartition("genre")
     .write
     .mode("overwrite")
     .format("parquet")
     .partitionBy("genre")
     .save(OUT_S3)
)

job.commit()
