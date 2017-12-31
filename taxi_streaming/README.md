#1. Generate Data 

Run the following scripts to generate the data in CSV.
./create_random_driver_data.sh

This will create output file with driver data
drivers_data.csv

#2. Stream Driver data to iguazio
./stream_driver_data.sh

#3. Consume the stream using Spark Streaming and write output to kv
./spark-submit_cmd
