# Copyright 2017 Iguazio
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import base64
import collections
import json
import numbers
import requests
import time

NGINX_HOST = '10.90.1.101'
NGINX_PORT = '8081'
STREAM_NAME = 'training/flight_stream'
CONTAINER_ID = 1
INTERVAL = 120
FLIGHT_DATA_URL = 'https://opensky-network.org/api/states/all'
BATCH_SIZE = 500



def get_stream_url():
    # assumes default container (id=1)
    return 'http://{0}:{1}/{2}/{3}/'.format(NGINX_HOST, NGINX_PORT, CONTAINER_ID, STREAM_NAME)


def get_function_headers(v3io_function):
    return {'Content-Type': 'application/json',
            'Cache-Control': 'no-cache',
            'X-v3io-function': v3io_function
            }


def encode_data(data):
    return {'Data': base64.b64encode(data)}


def validate_string(val):
    if val == 'null':
        return None
    return val.encode('utf-8').strip()


def validate_numeric(val):
    if not val:
        return None
    if not isinstance(val, numbers.Number):
        return None
    return val


def structure_message(msg):
    structured_msg = collections.OrderedDict()
    structured_msg['ts'] = msg[0]
    structured_msg['id'] = msg[1]
    structured_msg['call_sign'] = validate_string(msg[2])
    structured_msg['origin_country'] = validate_string(msg[3])
    structured_msg['time_position'] = validate_numeric(msg[4])
    structured_msg['time_velocity'] = validate_numeric(msg[5])
    structured_msg['lon'] = validate_numeric(msg[6])
    structured_msg['lat'] = validate_numeric(msg[7])
    structured_msg['altitude'] = validate_numeric(msg[8])
    structured_msg['on_ground'] = msg[9]
    structured_msg['velocity'] = validate_numeric(msg[10])
    structured_msg['heading'] = validate_numeric(msg[11])
    structured_msg['vertical_rate'] = validate_numeric(msg[12])
    return structured_msg


def send_records(records):
    print len(records)
    payload = {'Records': records}
    headers = get_function_headers('PutRecords')
    url = get_stream_url()
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=1)
        print 'status: {0}'.format(response.status_code)
        print response.json()
    except Exception, e:
        print "ERROR: {0}".format(str(e))


def get_flight_data():
    try:
        response = requests.get(FLIGHT_DATA_URL)
        return response.json()

    except Exception, e:
        print "ERROR: {0}".format(str(e))
    return None


start_time = time.time()
while True:
    print "request at - {0}".format(time.ctime())
    flight_data = get_flight_data()
    states = flight_data['states']
    flt_time = flight_data['time']
    batch = []
    for msg in states:
        # adding timestamp
        msg.insert(0, flt_time)
        jmsg = json.dumps(structure_message(msg))
        print jmsg
        batch.append(encode_data(jmsg))
        if len(batch) == BATCH_SIZE:
            send_records(batch)
            batch = []
    send_records(batch)
    time.sleep(INTERVAL - ((time.time() - start_time) % INTERVAL))
