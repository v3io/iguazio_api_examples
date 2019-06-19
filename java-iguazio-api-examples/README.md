# iguazio-api-java-examples

This repository contains example Spark Java programs to integrate various Iguazio Data Science Platform APIs.
All of the following drivers can run in parallel to simulate an end-to-end flow of consuming data from Kafka, ingesting as NoSQL ("KV") or stream data, and reading from NoSQL ("KV") table or from the stream in real time.

## Kafka Stream-Producer Driver

```sh
spark-submit --jars spark-streaming-kafka-0-10-assembly_2.11-2.2.0.jar --class com.iguazio.drivers.KafkaStreamProducerDriver data-ingestor-0.0.1-SNAPSHOT.jar
```

The **KafkaStreamProducerDriver** program will produce a random Kafka stream in the "cars" Kafka stream (topic), in the following comma separated string format:
`(driverid,timestamp,longitude,latitude,status)`

## Kafka to Iguazio Stream

```sh
spark-submit --jars spark-streaming-kafka-0-10-assembly_2.11-2.2.0.jar,/home/iguazio/hadoop/share/hadoop/hdfs/lib/v3io-hcfs.jar,/home/iguazio/spark2/lib/v3io-spark-streaming.jar  --class com.iguazio.drivers.KafkaToIguazioStreamIngestionDriver data-ingestor-0.0.1-SNAPSHOT.jar
```

The **KafkaToIguazioStreamIngestionDriver** program can be used to consume records from the "cars" Kafka stream (topic) and write it to a "cars-stream" stream in the Iguazio Data Science Platform, in append mode.


## Iguazio Stream Consumer

```sh
spark-submit --jars /home/iguazio/hadoop/share/hadoop/hdfs/lib/v3io-hcfs.jar,/home/iguazio/spark2/lib/v3io-spark-streaming.jar  --class com.iguazio.drivers.IguazioStreamConsumerDriver data-ingestor-0.0.1-SNAPSHOT.jar
```

The **IguazioStreamConsumerDriver** program can be used to consume records from the "cars-stream" stream in the Iguazio Data Science Platform.

## Kafka to NoSQL ("KV")

```sh
spark-submit --jars spark-streaming-kafka-0-10-assembly_2.11-2.2.0.jar,/home/iguazio/hadoop/share/hadoop/hdfs/lib/v3io-hcfs.jar,/home/iguazio/spark2/lib/v3io-spark-object-dataframe.jar   --class com.iguazio.drivers.KafkaToKvIngestionDriver data-ingestor-0.0.1-SNAPSHOT.jar
```

The **KafkaToKvIngestionDriver** program is used to consume records from the "cars" Kafka stream (topic) and write the data to the "cars-test-kv" Iguazio Data Science Platform NoSQL ("KV") table.

##  Iguazio NoSQL ("KV") Reader

```sh
spark-submit --jars spark-streaming-kafka-0-10-assembly_2.11-2.2.0.jar,/home/iguazio/hadoop/share/hadoop/hdfs/lib/v3io-hcfs.jar,/home/iguazio/spark2/lib/v3io-spark-object-dataframe.jar   --class com.iguazio.drivers.IguazioKvReaderDriver data-ingestor-0.0.1-SNAPSHOT.jar
```

The **IguazioKvReaderDriver** program can be used to read from the Iguazio NoSQL ("KV") data store.

