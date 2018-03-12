# iguazio-api-java-examples
this repository contains example spark java programs to integrate various Iguazio API's

kafka stream producer driver
--------------------------------
spark-submit --jars spark-streaming-kafka-0-10-assembly_2.11-2.2.0.jar --class com.iguazio.drivers.KafkaStreamProducerDriver data-ingestor-0.0.1-SNAPSHOT.jar


KafkaStreamProducerDriver program will produce a random kafka stream in cars topic in the following comma separated string format
(driverid,timestamp,longitude,latitude,status)

kafka to iguazio stream
--------------------------------
spark-submit --jars spark-streaming-kafka-0-10-assembly_2.11-2.2.0.jar,/home/iguazio/hadoop/share/hadoop/hdfs/lib/v3io-hcfs.jar,/home/iguazio/spark2/lib/v3io-spark-streaming.jar  --class com.iguazio.drivers.KafkaToIguazioStreamIngestionDriver data-ingestor-0.0.1-SNAPSHOT.jar

KafkaToIguazioStreamIngestionDriver program can be used to consume from kafka "cars" topic and it writes to "cars-stream" stream inside iguazio unified data platform in append mode.


iguazio stream consumer
--------------------------------
spark-submit --jars /home/iguazio/hadoop/share/hadoop/hdfs/lib/v3io-hcfs.jar,/home/iguazio/spark2/lib/v3io-spark-streaming.jar  --class com.iguazio.drivers.IguazioStreamConsumerDriver data-ingestor-0.0.1-SNAPSHOT.jar

IguazioStreamConsumerDriver program can be used to consume from  stream topic "cars-stream" inside iguazio unified data platform.

kafka to kv
--------------------------------
spark-submit --jars spark-streaming-kafka-0-10-assembly_2.11-2.2.0.jar,/home/iguazio/hadoop/share/hadoop/hdfs/lib/v3io-hcfs.jar,/home/iguazio/spark2/lib/v3io-spark-object-dataframe.jar   --class com.iguazio.drivers.KafkaToKvIngestionDriver data-ingestor-0.0.1-SNAPSHOT.jar

KafkaToKvIngestionDriver program is used to consume from kafka "cars" topic and it writes to iguazio kv "cars-test-kv"


iguazio kv reader
-----------------------
spark-submit --jars spark-streaming-kafka-0-10-assembly_2.11-2.2.0.jar,/home/iguazio/hadoop/share/hadoop/hdfs/lib/v3io-hcfs.jar,/home/iguazio/spark2/lib/v3io-spark-object-dataframe.jar   --class com.iguazio.drivers.IguazioKvReaderDriver data-ingestor-0.0.1-SNAPSHOT.jar

IguazioKvReaderDriver program can be used to read from iguazio kv.

