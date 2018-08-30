from pyspark.sql import SparkSession
from pyspark.streaming import StreamingContext
from v3io.spark.streaming import *

# Data-container name
CONTAINER_NAME = "bigdata"

# Path to the taxi_streaming example directory within the container
EXAMPLE_PATH = "/taxi_streaming_example/"
# NoSQL tables Path
NOSQL_TABLES_PATH = "v3io://" + CONTAINER_NAME + EXAMPLE_PATH
# Stream container-directory path
STREAM_PATH = EXAMPLE_PATH + "drivers_stream"
# NoSQL drivers-Data table path
DRIVERS_TABLE_PATH = NOSQL_TABLES_PATH + "/drivers_table/" 
# NoSQL drivers Ride-Status Summary Table Path
DRIVERS_STATUS_SUMMARY_TABLE_PATH = NOSQL_TABLES_PATH + "/driver_status_summary_table/" 

# Consume the stream data: read the data and save it to NoSQL tables
def archive(rdd):
    rdd.cache()
    if not rdd.isEmpty():
        # Read the raw drivers data from the stream into a Spark DataFrame
        # using the Spark Streaming API
        df = spark.read.json(rdd)
        # df.show()

        # Write the drivers data to a drivers NoSQL table
        df.write \
            .format("io.iguaz.v3io.spark.sql.kv") \
            .mode("overwrite") \
            .option("Key", "driver") \
	    .save(DRIVERS_TABLE_PATH)

        gdf = df.groupby("status").count()
        # gdf.show()

        # Write the driver ride-status summary to a drivers-status NoSQL table
        gdf.write \
            .format("io.iguaz.v3io.spark.sql.kv") \
            .mode("overwrite") \
            .option("Key", "status") \
	    .save(DRIVERS_STATUS_SUMMARY_TABLE_PATH)

# Create a Spark session
spark = SparkSession.builder \
    .appName("taxi_streaming example - consume stream data") \
    .getOrCreate()

# Create a Spark streaming context with a 10-seconds micro-batch interval
ssc = StreamingContext(spark.sparkContext, 10)

# Do not set any configuration properties for the stream
v3ioConfig = {"container-id": CONTAINER_NAME}

# Map the platform stream to a Spark input stream using the platform's
# Spark-Streaming Integration API
stream = V3IOUtils.createDirectStream(ssc, v3ioConfig, [STREAM_PATH])

# Assign the archive stream-data consumption function as the stream's
# Resilient Distributed Dataset (RDD) handler
stream.foreachRDD(archive)

# Start consuming data from the stream
ssc.start()
ssc.awaitTermination()

