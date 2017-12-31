#1. Generate Data 

Run the following scripts to generate the data in CSV.
./create_random_driver_data.sh

This will create output file with driver data
drivers_data.csv

#2. Create stream
./create_taxi_stream.sh

#3. Stream Driver data to iguazio and in parallel consume the stream using Spark Streaming and write output to kv
./stream_driver_data.sh
./spark-submit_cmd
