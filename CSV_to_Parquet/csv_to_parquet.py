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
