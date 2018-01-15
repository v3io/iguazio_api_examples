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
NGINX_HOST = "127.0.0.1"
# Port number of the platform's web-gateway service
NGINX_PORT = "8081"
# Stream container-directory path
STREAM_PATH = "taxi_example/driver_stream"

# Stream data-messages batch-job size
BATCH_SIZE = 500

INPUT_FILE = str(sys.argv[1])


# Create the PutRecords request URL with the platform's web-gateway host name
# or IP address and port number, the container ID, and the stream path
def get_stream_url():
    return 'http://{0}:{1}/{2}/{3}/' \
        .format(NGINX_HOST, NGINX_PORT, CONTAINER_ID, STREAM_PATH)


# Create the PutRecords request headers
def get_function_headers(v3io_function):
    return {'Content-Type': 'application/json',
            'Cache-Control': 'no-cache',
            'X-v3io-function': v3io_function
            }


# Encode the stream data as a Base64 string
def encode_data(data):
    return {'Data': base64.b64encode(data)}


# Build a structured message from the stream-record data
def structure_message(msg):
    structured_msg = collections.OrderedDict()
    # Driver ID
    structured_msg['driver'] = msg[0]
    # Data arrival (ingestion) time
    structured_msg['timestamp'] = msg[1]
    # Taxi-location longitude GPS coordinate
    structured_msg['longitude'] = msg[2]
    # Taxi-location latitude GPS coordinate
    structured_msg['latitude'] = msg[3]
    # Driver ride status
    structured_msg['status'] = msg[4]
    return structured_msg


# Add the encoded data to the stream (send the data to the platform) using the
# PutRecords Streaming Web API operation
def send_records(records):
    # print len(records)
    payload = {'Records': records}
    headers = get_function_headers('PutRecords')
    url = get_stream_url()
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=1)
        # print 'status: {0}'.format(response.status_code)
    except Exception, e:
        print "ERROR: {0}".format(str(e))


# Read the raw data from the input file into a drivers-information structure
def get_driver_data():
    drivers = []
    # Open the data input file
    with open(INPUT_FILE) as csvfile:
        readCSV = csv.reader(csvfile, delimiter=',')
        # Skip the header row
        next(readCSV, None)
        # Iterate the CSV rows and add each row to the drivers structure
        for row in readCSV:
            # print(row)
            drivers.append(row)
    return drivers

print "Start - {0}".format(time.ctime())

# Read the input data for the stream into a drivers_data structure
drivers_data = get_driver_data()
# Create a batch job of Base64 encoded stream driver-data messages and add the
# batch data to the stream (i.e., send the data to the platform)
batch = []
for msg in drivers_data:
    # Add each driver-data message to a JSON structure
    jmsg = json.dumps(structure_message(msg))
    # print jmsg
    # Prepare a batch of Base64 encoded driver-data messages
    batch.append(encode_data(jmsg))

    # When the length of the batch string reaches a predefined size, add the
    # data records to the stream (i.e., send the data to the platform)
    if len(batch) == BATCH_SIZE:
        send_records(batch)
        batch = []
# Send any remaining batch data to the platform
send_records(batch)

print "End - {0}".format(time.ctime())

