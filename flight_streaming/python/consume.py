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

STREAM_NAME='/training/flight_stream'
OUTPUT_PATH = 'training'

# 
# Write stream data to Parquet
#
def archive(rdd):
    rdd.cache()
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
