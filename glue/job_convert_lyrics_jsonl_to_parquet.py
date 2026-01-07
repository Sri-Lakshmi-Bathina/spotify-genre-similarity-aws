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

IN_S3 = "s3://spotify-genre-similarity-sri/curated/lyrics_by_track_sample/lyrics_sample.jsonl"
OUT_S3 = "s3://spotify-genre-similarity-sri/curated/lyrics_by_track_sample_parquet/"

df = spark.read.json(IN_S3)

df = df.withColumn("genre", F.lower(F.trim(F.col("genre"))))
df = df.withColumn("lyrics_found", F.col("lyrics_found").cast("boolean"))

keep = ["track_id", "track_name", "artist_name_primary", "genre", "lyrics", "lyrics_found"]
df = df.select(*[c for c in keep if c in df.columns])

(
    df.repartition("genre")
      .write
      .mode("overwrite")
      .format("parquet")
      .partitionBy("genre")
      .save(OUT_S3)
)

job.commit()
