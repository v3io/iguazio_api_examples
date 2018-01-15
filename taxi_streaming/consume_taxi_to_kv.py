from pyspark.sql import SparkSession
from pyspark.streaming import StreamingContext
from v3io.spark.streaming import *

# Data-container ID
CONTAINER_ID = 1  # assumes a default container with ID 1
# Output container-directory path for generated files and directories
OUTPUT_PATH = "/taxi_example/"
# Stream container-directory path
STREAM_PATH = OUTPUT_PATH/driver_stream


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
        .format('io.iguaz.v3io.spark.sql.kv') \
        .mode("overwrite") \
        .option("Key", "driver") \
        .option("container-id", CONTAINER_ID) \
        .save('{0}/{1}'.format(OUTPUT_PATH, 'driver_kv/'))

    # Group the driver ride-status data for all drivers, and count the number
    # of drivers in each status
    gdf = df.groupby("status").count()
    # gdf.show()

    # Write the driver ride-status summary to a drivers-status NoSQL table
    gdf.write \
        .format('io.iguaz.v3io.spark.sql.kv') \
        .mode("overwrite") \
        .option("Key", "status") \
        .option("container-id", CONTAINER_ID) \
        .save('{0}/{1}'.format(OUTPUT_PATH, 'driver_summary/'))

# Create a Spark session
spark = SparkSession.builder \
    .appName("taxi_streaming example - consume stream data") \
    .getOrCreate()

# Define a Spark streaming context with a 10-seconds micro-batch
ssc = StreamingContext(spark.sparkContext, 10)

v3ioConfig = {"container-id": CONTAINER_ID}
# Map the platform stream to a Spark input stream using the platform's
# Spark-Streaming Integration API
stream = V3IOUtils.createDirectStream(ssc, [OUTPUT_PATH/STREAM_NAME],
                                      v3ioConfig)
# Consume the stream data using Spark
stream.foreachRDD(archive)

# Start the Spark job
ssc.start()
ssc.awaitTermination()

