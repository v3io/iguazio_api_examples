from pyspark.sql import SparkSession
from pyspark.streaming import StreamingContext
from v3io.spark.streaming import *

STREAM_NAME='training/flight_stream'
OUTPUT_PATH = 'training'

# 
# Write stream data to Parquet
#
def archive(rdd):
    if not rdd.isEmpty():
        df = spark.read.json(rdd)
        df.write\
            .format('parquet')\
            .mode('overwrite') \
            .save('{0}/{1}'.format(OUTPUT_PATH, 'flight_pq'))


spark = SparkSession.builder\
    .appName('ingest to pq')\
    .getOrCreate()
ssc = StreamingContext(spark.sparkContext, 15)
v3ioConfig = {"container-id": 1}
stream = V3IOUtils.createDirectStream(ssc, [STREAM_NAME], v3ioConfig)
stream.foreachRDD(archive)
ssc.start()
ssc.awaitTermination()