import sys
import requests
import json
import csv
import time
import igz_nosql_web

#PATH_IN_URL = '/1/drivers/'
DRIVERS_PATH_IN_URL = '/1/drivers/'
CELLS_PATH_IN_URL   = '/1/cells/'

#------------
BASE_URL = 'http://192.168.218.25:32418'

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
        lat = row[1]
        long = row[2]
        speed = row[3]
        accurancy = row[4]
        time_stamp = row[5]
        trip_id = row[6]
        status = row[7]
        cell_id = row[8]
        dsd_id = row[9]
        region_name = row[10]
        event_date = row[11]
        body = driver_id + ',' + lat + ',' + long + ',' + speed + ',' + time_stamp + ',' + cell_id
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
