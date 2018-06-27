# 1. Generate Data

To generate the data in CSV format, run the following scripts on the server on which the Iguazio Continuous Data Platform web-gateway service is hosted:

```sh
./create_random_passenger_data.sh 
./create_random_driver_data.sh
```

This will create two files:

- **drivers_data.csv**
- **passengers_data.csv**

# 2. Simulate Data Ingestion

Now, these two data files can be used to simulate live taxi and passenger traffic. 
Both the files need to be ingested simultaneously .

```sh
./load_driver_data.sh & ./load_passenger_data.sh &
```

