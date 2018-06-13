#1. Generate Data
run the following scripts on the server on which the Web API server is hosted to generate the data in CSV. 

```
./create_random_passenger_data.sh 
./create_random_driver_data.sh
```

This will create two files
```
drivers_data.csv
passengers_data.csv
```

#2. Simulate Data Ingestion
Now these two data files can be used to simulate live taxi and passanger traffic. 
Both the files need to be ingested simaltaneously 

```
./load_driver_data.sh & ./load_passenger_data.sh &
```
