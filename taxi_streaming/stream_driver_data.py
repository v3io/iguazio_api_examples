import base64
import collections
import json
import csv
import numbers
import requests
import time
import sys

# Data-container ID
CONTAINER_ID = 1  # assumes a default container with ID 1
# IP address of the platform's web-gateway service
NGINX_IP = "127.0.0.1"
# Port number of the platform's web-gateway service
NGINX_PORT = "8081"
# Stream container-directory path
STREAM_PATH = "/taxi_example/driver_stream"

# Stream-records batch size
STREAM_RECORDS_BATCH_SIZE = 500

# A comma-delimited CSV stream-data file is passed as an application argument
INPUT_FILE = str(sys.argv[1])


# Create the PutRecords request URL with the platform's web-gateway host name
# or IP address and port number, the container ID, and the stream path
def get_stream_url():
    return "http://{0}:{1}/{2}{3}/" \
        .format(NGINX_IP, NGINX_PORT, CONTAINER_ID, STREAM_PATH)


# Create the PutRecords request headers
def get_function_headers(v3io_function):
    return {"Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-v3io-function": v3io_function
            }


# Encode the stream data as a Base64 string
def encode_data(data):
    # Return a stream-record JSON object with a string "Data" key that's
    # assigned the Base64 encoding of the provided stream data
    return {"Data": base64.b64encode(data)}


# Build a structured message from the provided stream-record data message
def structure_message(msg):
    structured_msg = collections.OrderedDict()
    # Driver ID
    structured_msg["driver"] = msg[0]
    # Data arrival (ingestion) time
    structured_msg["timestamp"] = msg[1]
    # Taxi-location longitude GPS coordinate
    structured_msg["longitude"] = msg[2]
    # Taxi-location latitude GPS coordinate
    structured_msg["latitude"] = msg[3]
    # Driver ride status
    structured_msg["status"] = msg[4]
    return structured_msg


# Add the encoded data to the stream (send the data to the platform) using the
# PutRecords Streaming Web API operation
def send_records(records):
    # print len(records)
    payload = {"Records": records}
    headers = get_function_headers("PutRecords")
    url = get_stream_url()
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=1)
        # print "status: {0}".format(response.status_code)
    except Exception, e:
        print "ERROR: {0}".format(str(e))


# Read the raw data from the input file into a drivers-data list
def get_driver_data():
    drivers = []
    # Open the data input file
    with open(INPUT_FILE) as csvfile:
        readCSV = csv.reader(csvfile, delimiter=",")
        # Skip the header row
        next(readCSV, None)
        # Iterate the CSV rows and add each row to the drivers-data list
        for row in readCSV:
            # print(row)
            drivers.append(row)
    return drivers

print "Start - {0}".format(time.ctime())

# Read the input data for the stream into a drivers_data list
drivers_data = get_driver_data()
# Create a "batch" list of JSON stream-record objects with Base64 encoded data
# messages, and add the records to the stream (send the data to the platform)
batch = []
for msg in drivers_data:
    # Create a structured data-message JSON object for each stream-data message
    jmsg = json.dumps(structure_message(msg))
    # print jmsg
    # Translate each structured-message JSON object into a stream-record JSON
    # object with a "Data" key that's assigned a Base64 encoded data message
    batch.append(encode_data(jmsg))

    # When the number of record JSON objects in the batch list is reaches the
    # configured batch size, add the records to the stream (send the data)
    if len(batch) == STREAM_RECORDS_BATCH_SIZE:
        send_records(batch)
        batch = []
# Send any remaining batch data to the platform
send_records(batch)

print "End - {0}".format(time.ctime())

