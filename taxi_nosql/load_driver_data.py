import sys
import requests
import csv
import time
import s2sphere
import igz_nosql_web

BASE_URL = 'http://127.0.0.1:8081'

DRIVERS_PATH_IN_URL = '/1/taxi_example/drivers/'
CELLS_PATH_IN_URL   = '/1/taxi_example/cells/'

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
        #print(row)
        driver_id = row[0]
        time_stamp = row[1]
	long = float(row[2])
        lat  = float(row[3])

	# Use google s2Sphere library to calculate Cell 
        p1 = s2sphere.LatLng.from_degrees(lat,long)
        cell = s2sphere.CellId.from_lat_lng(p1).parent(15)
        cell_id = str(cell.id())
        #print (cell_id)

        # update driver current and previous location 
        res = igz_nosql_web.ngx_update_expression_request(s,BASE_URL, DRIVERS_PATH_IN_URL + "driver_" + driver_id, None, None,
                                            "CreateOrReplaceAttributes",
                                            "previous_cell_id=current_cell_id;current_cell_id=" + cell_id + ";change_cell_id_indicator=(previous_cell_id != current_cell_id);",
                                            "exists(current_cell_id)")
	
        # if driver does not exist, add driver
	if res.status_code == requests.codes.bad_request:
            igz_nosql_web.ngx_update_expression_request(s,BASE_URL, DRIVERS_PATH_IN_URL + "driver_" + driver_id, None, None,
                                          "CreateOrReplaceAttributes",
                                          "current_cell_id=" + cell_id + ";previous_cell_id=0;change_cell_id_indicator=(1==1);",
                                          "(1==1)")

        # Get current and previous cell for driver 
        response_json = igz_nosql_web.ngx_get_item_request(s,BASE_URL, DRIVERS_PATH_IN_URL+"driver_"+driver_id,None,None,exp_attrs=["change_cell_id_indicator","current_cell_id","previous_cell_id"])

        # Check if a cell update is needed
        attrs = response_json["Item"]
        change_cell_id_indicator_val = attrs["change_cell_id_indicator"]["BOOL"]
        current_cell_id_val = attrs["current_cell_id"]["N"]
        previous_cell_id_val = attrs["previous_cell_id"]["N"]
        #for key, value in attrs.items():
        #     print("attr: {}, value: {}".format(key, value["N"]))

        # Try to increase the count on the cell the driver moved to
        if change_cell_id_indicator_val:
            res=igz_nosql_web.ngx_update_expression_request(s,BASE_URL, CELLS_PATH_IN_URL + "cell_"+ current_cell_id_val, None, None,
                                          "CreateOrReplaceAttributes",
                                          "count=count+1;",
                                          "exists(count)")
            # If the cell doesn't exists create a new one
            if res.status_code == requests.codes.bad_request:
                igz_nosql_web.ngx_update_expression_request(s,BASE_URL, CELLS_PATH_IN_URL + "cell_" + current_cell_id_val, None, None,
                                              "CreateOrReplaceAttributes",
                                              "count=1;",
                                              None)
            # Decrease the count on the cell the driver moved from
            igz_nosql_web.ngx_update_expression_request(s,BASE_URL, CELLS_PATH_IN_URL + "cell_" + previous_cell_id_val, None, None,
                                          "CreateOrReplaceAttributes",
                                          "count=count-1;;",
                                          None)
        counter = counter + 1
        if counter % 1000 == 0:
            end = time.time()
            print("File: {}, timing: {}, Counter: {}".format(INPUT_FILE, end - start, counter))
end = time.time()
print("Total File: {}, timing: {}, Counter: {}".format(INPUT_FILE, end - start, counter))
