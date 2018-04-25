from pyspark.sql import SparkSession
from pyspark.sql.types import *
import datetime
import time

spark = SparkSession.builder.appName("CSVToParquet").getOrCreate()

CSVTableLoc = "v3io://cont-name/archive/csv/20180208.csv"
parquetLoc = "v3io://cont-name/archive/parquet/20180208/"

schema = StructType([
    StructField("driverId", LongType(), True),
    StructField("latitude", DoubleType(), True),
    StructField("longitude", DoubleType(), True),
    StructField("speed", DoubleType(), True),
    StructField("timestamp", LongType(), True),
    StructField("tripId", LongType(), True)
    ])

csv_data_df = spark.read.format("csv").schema(schema).option("header", "true").load(CSVTtableLoc)
csv_data_df.write.format("parquet").mode("append").save(parquetLoc)
spark.stop()

#spark-submit --master yarn --deploy-mode client --driver-memory 1g --executor-memory 2g --executor-cores 1 --num-executors 6 csv_to_parquet.p
