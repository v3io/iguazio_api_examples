import sys
import requests
import csv
import time
import s2sphere
import igz_nosql_web
import os


WEBAPI_URL = os.getenv ("WEBAPI_URL")
CONTAINER_NANE = os.getenv ("CONTAINER_NAME")

PASSENGERS_TABLE_PATH = CONTAINER_NANE + os.getenv ("PASSENGERS_TABLE")
CELLS_TABLE_PATH   = CONTAINER_NANE + os.getenv ("CELLS_TABLE")


# read CSV
INPUT_FILE = str(sys.argv[1])

start = time.time()
counter = 0
s = requests.Session()
#r = s2sphere.RegionCoverer()
with open(INPUT_FILE) as csvfile:
    readCSV = csv.reader(csvfile, delimiter=',')
    # Skip the header
    next(readCSV, None)
    # Go over the rows and get the driver id and cell id
    for row in readCSV:
        #print(row)
        passenger_id = row[0]
        time_stamp = row[1]
	long = float(row[2])
        lat  = float(row[3])

	# Use google s2Sphere library to calculate Cell 
        p1 = s2sphere.LatLng.from_degrees(lat,long)
        cell = s2sphere.CellId.from_lat_lng(p1).parent(15)
        cell_id = str(cell.id())
        #print (cell_id)

        # update passenger current and previous location 
        res = igz_nosql_web.ngx_update_expression_request(s,WEBAPI_URL, PASSENGERS_TABLE_PATH + "passenger_" + passenger_id, None, None,
                                            None,
                                            "SET previous_cell_id=if_not_exists(current_cell_id,0);current_cell_id=" + cell_id + ";change_cell_id_indicator=(previous_cell_id != current_cell_id);",
                                            None)


        if res.status_code not in (200,204):
                print ("Error during update of passengers table. Error code is "+str(res.status_code))

	# Get current and previous cell for passenger 
        response_json = igz_nosql_web.ngx_get_item_request(s,WEBAPI_URL, PASSENGERS_TABLE_PATH + "passenger_"+passenger_id,None,None,exp_attrs=["change_cell_id_indicator","current_cell_id","previous_cell_id"])

        # Check if a cell update is needed
        attrs = response_json["Item"]
        change_cell_id_indicator_val = attrs["change_cell_id_indicator"]["BOOL"]
        current_cell_id_val = attrs["current_cell_id"]["N"]
        previous_cell_id_val = attrs["previous_cell_id"]["N"]
        #for key, value in attrs.items():
        #     print("attr: {}, value: {}".format(key, value["N"]))

        # Try to increase the count on the cell the driver moved to
        if change_cell_id_indicator_val:
           
            res = igz_nosql_web.ngx_update_expression_request(s,WEBAPI_URL, CELLS_TABLE_PATH + "cell_"+ current_cell_id_val, None, None,
                                          None,
                                          "SET passenger_count=if_not_exists(passenger_count,0)+1;",
                                          None)
            
            if res.status_code not in (200,204):
                print ("Error during increment of count in cells table. Error code is "+str(res.status_code))

	    # Decrease the count on the cell the driver moved from
            res = igz_nosql_web.ngx_update_expression_request(s,WEBAPI_URL, CELLS_TABLE_PATH + "cell_" + previous_cell_id_val, None, None,
                                          None,
                                          "passenger_count=passenger_count-1;;",
                                          None)

            if res.status_code not in (200,204):
                print ("Error during decrement of count in cells table. Error code is "+str(res.status_code))

        counter = counter + 1
        if counter % 1000 == 0:
            end = time.time()
            print("File: {}, timing: {}, Counter: {}".format(INPUT_FILE, end - start, counter))
end = time.time()
print("Total File: {}, timing: {}, Counter: {}".format(INPUT_FILE, end - start, counter))

