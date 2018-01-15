from pyspark.sql import SparkSession
from pyspark.streaming import StreamingContext
from v3io.spark.streaming import *

STREAM_NAME='/taxi_example/driver_stream'
OUTPUT_PATH = '/taxi_example/'

# 
# Write stream data and summary to iguazio platform
#
def archive(rdd):
    rdd.cache ()
    if not rdd.isEmpty():
	# read the stream
        df = spark.read.json(rdd)
	# df.show()	

	# Write drivers location to driver KV
	df.write\
            .format('io.iguaz.v3io.spark.sql.kv')\
            .mode("overwrite")\
	    .option ("Key","driver")\
	    .option ("container-id",1)\
            .save('{0}/{1}'.format(OUTPUT_PATH, 'driver_kv/'))
	
	# Group current status for all drivers
	gdf = df.groupby("status").count()
	#gdf.show()

	# Write driver status summary
	gdf.write\
            .format('io.iguaz.v3io.spark.sql.kv')\
            .mode("overwrite")\
	    .option ("Key","status")\
            .option ("container-id",1)\
            .save('{0}/{1}'.format(OUTPUT_PATH, 'driver_summary/'))


spark = SparkSession.builder\
    .appName('ingest to nosql')\
    .getOrCreate()

# Define Streaming Context with 10 second micro-batch
ssc = StreamingContext(spark.sparkContext, 10)

v3ioConfig = {"container-id": 1}
# Map V3io platform stream to Spark input stream
stream = V3IOUtils.createDirectStream(ssc, [STREAM_NAME], v3ioConfig)
stream.foreachRDD(archive)

# Start the job
ssc.start()
ssc.awaitTermination()

