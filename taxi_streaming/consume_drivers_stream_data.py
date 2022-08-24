# Copyright 2017 Iguazio
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from pyspark.sql import SparkSession
from pyspark.streaming import StreamingContext
from v3io.spark.streaming import *

# Data-container name
CONTAINER_NAME = "bigdata"

# Configure paths within the target-container directory:
# Parent example directory
EXAMPLE_PATH = "/taxi_streaming_example/"
# Parent tables directory
NOSQL_TABLES_PATH = "v3io://" + CONTAINER_NAME + EXAMPLE_PATH
# Stream path within the parent container directory
STREAM_PATH = EXAMPLE_PATH + "drivers_stream"
# Fully qualified v3io stream path
V3IO_STREAM_PATH = "v3io://" + CONTAINER_NAME + STREAM_PATH
# NoSQL drivers-data table
DRIVERS_TABLE_PATH = NOSQL_TABLES_PATH + "/drivers_table/" 
# NoSQL drivers ride-status summary table
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
v3ioConfig = {}
# Map the platform stream to a Spark input stream using the platform's
# Spark-Streaming Integration API
stream = V3IOUtils.createDirectStream(ssc, v3ioConfig, [V3IO_STREAM_PATH])

# Assign the archive stream-data consumption function as the stream's
# Resilient Distributed Dataset (RDD) handler
stream.foreachRDD(archive)

# Start consuming data from the stream
ssc.start()
ssc.awaitTermination()

