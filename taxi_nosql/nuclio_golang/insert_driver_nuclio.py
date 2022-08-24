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
import sys
import requests
import json
import csv
import time

#------------
BASE_URL = 'http://127.0.0.1:31223'

# read CSV
INPUT_FILE = str(sys.argv[1])

start = time.time()
counter = 0
s = requests.Session()
with open(INPUT_FILE) as csvfile:
    readCSV = csv.reader(csvfile, delimiter=',')
    # Skip the header
    next(readCSV, None)
    # Go over the rows and get the driver id and cell id
    for row in readCSV:
        driver_id = row[0]
        time_stamp = row[1]
        lat = row[2]
        long = row[3]
        status = row[4]
        body = driver_id + ',' + time_stamp + ',' + lat + ',' + long + ',' + status
        #print(body)

        # call the update request
        res = s.put(BASE_URL, data=body, headers=None)
        if res.status_code == requests.codes.bad_request:
            print(res.content)
            print(res.status_code)

        counter = counter + 1
        if counter % 1000 == 0:
            end = time.time()
            print("File: {}, timing: {}, Counter: {}".format(INPUT_FILE, end - start, counter))
end = time.time()
print("Total File: {}, timing: {}, Counter: {}".format(INPUT_FILE, end - start, counter))
