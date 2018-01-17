Running the example
===================
#1. Generate Data 

Run the following scripts to generate the drivers data in CSV.
./create_random_drivers_data.sh

This will create output file with driver data
drivers_data.csv

#2. Create stream
./create_drivers_stream.sh

#3. Stream Driver data to iguazio and in parallel consume the stream using Spark Streaming and write output to kv
./stream_drivers_data.sh
./spark-submit_cmd.sh

Description
===========
This example demonstrates iguazio streaming by streaming data using iguazio web API into the platform, consuming the stream by using Spark Streaming and writing the output and summary to iguazio kv

The first step of the example is generating the random driver data. The output of this stage is csv file that can be consumed by the system. Note that real life scenarios will probably use more effiecient ways for generating the input data, the example uses file as it is the most straight-forward and easy to implement and demosnstrate.

The second step is creating a stream definition. This is easily done by using the CreateStream Web API iguazio function.

The third step is streaming and consuming the data - this is done in parallel - the stream is written into the platform, and once every 10 seconds a micro-batch is executed to read the data, calcualte summarized status and store both raw data and summary data to KV.

Streaming the data -  input file is read, and the driver details including taxi location and status are usd to create a stream message. The stream message is written using PutRecords web API to the iguazio platform

Consuming the data and inserting into kv - this is done in 2 steps:
1. The raw driver data is added to driver_kv with driver as key
2. The status of the drivers is aggregated based on status. Aggregated data is written to the summary table driver_summary

