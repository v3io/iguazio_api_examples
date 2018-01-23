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
            .save("{0}/{1}".format(NOSQL_TABLES_PATH, "drivers_table/"))

        # Group the driver ride-status data for all drivers, and count the
        # number of drivers in each status
        gdf = df.groupby("status").count()
        # gdf.show()

        # Write the driver ride-status summary to a drivers-status NoSQL table
        gdf.write \
            .format("io.iguaz.v3io.spark.sql.kv") \
            .mode("overwrite") \
            .option("Key", "status") \
            .save("{0}/{1}".format(NOSQL_TABLES_PATH, "driver_status_summary_table/"))

# Create a Spark session
spark = SparkSession.builder \
    .appName("taxi_streaming example - consume stream data") \
    .getOrCreate()

# Create a Spark streaming context with a 10-seconds micro-batch interval
ssc = StreamingContext(spark.sparkContext, 10)
# Configure the platform stream's parent data container
v3ioConfig = {"container-alias": CONTAINER_NAME}
# Map the platform stream to a Spark input stream using the platform's
# Spark-Streaming Integration API
stream = V3IOUtils.createDirectStream(ssc, [STREAM_PATH], v3ioConfig)

# Assign the archive stream-data consumption function as the stream's
# Resilient Distributed Dataset (RDD) handler
stream.foreachRDD(archive)

# Start consuming data from the stream
ssc.start()
ssc.awaitTermination()

