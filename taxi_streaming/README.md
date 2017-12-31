Running the example
===================
#1. Generate Data 

Run the following scripts to generate the drivers data in CSV.
./create_random_driver_data.sh

This will create output file with driver data
drivers_data.csv

#2. Create stream
./create_taxi_stream.sh

#3. Stream Driver data to iguazio and in parallel consume the stream using Spark Streaming and write output to kv
./stream_driver_data.sh
./spark-submit_cmd

Description
===========
This example demonstrates iguazio streaming by streaming data using iguazio web API into the platform, consuming the stream by using Spark Streaming and writing the output to iguazio kv

The first step of the example is generating the random driver data. The output of this stage is csv file that can be consumed by the system. Note that real life scenarios will probably use more effiecient ways for generating the input data, the example uses file as it is the most straight-forward and easy to implement and demosnstrate

The second step is streaming the data. The input file is read, and the driver details including taxi location and status are usd to create a stream message. The stream message is written using PutRecords to the iguazio platform

The third step is consuming the data and inserting into kv. This is done in 2 steps:
1. The raw driver data is added to driver_kv with driver as key
2. The status of the drivers is aggregated based on status. Aggregated data is written to the summary table driver_summary

