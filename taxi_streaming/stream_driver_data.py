import base64
import collections
import json
import csv
import numbers
import requests
import time
import sys

NGINX_HOST = "127.0.0.1"
NGINX_PORT = "8081"
STREAM_NAME = "taxi_example/driver_stream"
CONTAINER_ID = 1
BATCH_SIZE = 500

INPUT_FILE = str(sys.argv[1])

# define the URL based on host,port,container and stream name
def get_stream_url():
    # assumes default container (id=1)
    return 'http://{0}:{1}/{2}/{3}/'.format(NGINX_HOST, NGINX_PORT, CONTAINER_ID, STREAM_NAME)

# headers for the v3io function
def get_function_headers(v3io_function):
    return {'Content-Type': 'application/json',
            'Cache-Control': 'no-cache',
            'X-v3io-function': v3io_function
            }

# base64encod the stream data
def encode_data(data):
    return {'Data': base64.b64encode(data)}

# build a structured message
def structure_message(msg):
    structured_msg = collections.OrderedDict()
    structured_msg['driver'] = msg[0]
    structured_msg['timestamp'] = msg[1]
    structured_msg['longitude'] = msg[2]
    structured_msg['latitude'] = msg[3]
    structured_msg['status'] = msg[4]
    return structured_msg

# Write the stream to iguazio using PutRecords web API 
def send_records(records):
    #print len(records)
    payload = {'Records': records}
    headers = get_function_headers('PutRecords')
    url = get_stream_url()
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=1)
        #print 'status: {0}'.format(response.status_code)
    except Exception, e:
        print "ERROR: {0}".format(str(e))

# read the input file into drivers structure
def get_driver_data():
    drivers = []
    with open(INPUT_FILE) as csvfile:
        readCSV = csv.reader(csvfile, delimiter=',')
        # Skip the header
        next(readCSV, None)
        # Go over the rows and get the driver id and cell id
        for row in readCSV:
            # print(row)
            drivers.append (row)
    return drivers

print "Start - {0}".format(time.ctime())

drivers_data = get_driver_data ()
batch = []
for msg in drivers_data:
    # add to json structure
    jmsg = json.dumps(structure_message(msg))
    #print jmsg
    # add encoded message to batch
    batch.append(encode_data(jmsg))
    
    # if batch length reached defined size, send records
    if len(batch) == BATCH_SIZE:
       send_records(batch)
       batch = []
send_records(batch)

print "End - {0}".format(time.ctime())

