import requests
import json
import os
import s2sphere

# Get configuration information from environment variables defined using Nuclio
WEBAPI_URL = str(os.getenv('WEBAPI_URL'))
CONTAINER_NAME = str(os.getenv('CONTAINER_NAME'))

WEBAPI_CRED = os.getenv('WEBAPI_CRED')

# Get table locations from environment variables defined using Nuclio
DRIVERS_TABLE_PATH = CONTAINER_NAME + str(os.getenv('DRIVERS_TABLE'))
PASSENGERS_TABLE_PATH = CONTAINER_NAME + str(os.getenv('PASSENGERS_TABLE'))
CELLS_TABLE_PATH = CONTAINER_NAME + str(os.getenv('CELLS_TABLE'))

DRIVER_PREFIX = 'drivers_'
PASSENGER_PREFIX = 'passengers_'

V3IO_HEADER_FUNCTION = 'X-v3io-function'


#
# Ingest data into driver/passenger and cells tables
# 
def handler(context, event):

    # Generate the input data based on input from event.body
    id, cell_id, item_prefix = _generate_data_from_input(event.body)

    # Update driver/passenger current and previous location
    res = _webapi_updateitem(WEBAPI_URL,
                             id,
                             f'SET previous_cell_id=if_not_exists(current_cell_id,0);current_cell_id={cell_id};change_cell_id_indicator=(previous_cell_id != current_cell_id);')
    context.logger.error(f'Error during update of {WEBAPI_URL}{id}. Error code is {res.status_code}')

    if res.status_code != requests.codes.no_content:
            context.logger.error(f'Error during update of {WEBAPI_URL}{id}. Error code is {res.status_code}')
            return context.Response(body='Internal error during ingestion', content_type='text/plain', status_code=500)

    # Update cells table according to driver/passenger current and previous location
    res = _update_cells_table(context, id, item_prefix)
    if res.status_code != requests.codes.no_content:
            context.logger.error(f'Error during update of cells table. Error code is {res.status_code}')
            return context.Response(body='Internal error during ingestion', content_type='text/plain', status_code=500)

    # return 200 - completed successfuly
    return context.Response(status_code=200)


#
# Generate data from input - parse the json and analyze
#
def _generate_data_from_input(input_data_json):

    # Read the data to be ingested from the input json
    input_data = json.loads(input_data_json)

    record_type = str(input_data["RecordType"])

    input_id = str(input_data["ID"])

    longitude = float(input_data["Longitude"])
    latitude = float(input_data["Latitude"])

    # Use google s2Sphere library to calculate Cell from longitude and latitude
    p1 = s2sphere.LatLng.from_degrees(latitude, longitude)
    cell = s2sphere.CellId.from_lat_lng(p1).parent(15)
    cell_id = str(cell.id())

    # Ingestion of both drivers and passengers are supported
    # Depening on record type, releavant tables will be updated
    if record_type == 'driver':
        item_prefix = DRIVER_PREFIX
        item_path = DRIVERS_TABLE_PATH
    else:
        item_prefix = PASSENGER_PREFIX
        item_path = PASSENGERS_TABLE_PATH

    id = item_path + item_prefix + input_id

    return id, cell_id, item_prefix


#
# If Cell(location) was changed, update cells table based on new location
# Increase the count on the new cell, decrease the count on the old cell if needed
#
def _update_cells_table(context, id, item_prefix):

    # Get current and previous cell for driver
    response_json = _webapi_getitem(WEBAPI_URL, id, exp_attrs=["change_cell_id_indicator", "current_cell_id", "previous_cell_id"])

    # Check if a cell update is needed
    attrs = response_json["Item"]
    change_cell_id_indicator_val = attrs["change_cell_id_indicator"]["BOOL"]
    current_cell_id_val = attrs["current_cell_id"]["N"]
    previous_cell_id_val = attrs["previous_cell_id"]["N"]

    # if cell was changed, increase the count on the new cell and descrease from the old cell
    if change_cell_id_indicator_val:

            count_attribute = item_prefix+'count'

            # Increase the count on the currnet cell
            res = _webapi_updateitem(WEBAPI_URL,
                                     CELLS_TABLE_PATH + "cell_" + current_cell_id_val,
                                     f'SET {count_attribute}=if_not_exists({count_attribute},0)+1;')

            if res.status_code != requests.codes.no_content:
                context.logger.error(f'Error during increment of count in cells table. Error code is {res.status_code}')
                return context.Response(body='Internal error during ingestion', content_type='text/plain', status_code=500)

            # Decrease the count on the previous cell
            if int(previous_cell_id_val) > 0:
                res = _webapi_updateitem(WEBAPI_URL,
                                         CELLS_TABLE_PATH + "cell_" + previous_cell_id_val,
                                         f'SET {count_attribute}={count_attribute}-1;')

            if res.status_code != requests.codes.no_content:
                    context.logger.error(f'Error during decrement of count in cells table. Error code is {res.status_code}')
                    return context.Response(body='Internal error during ingestion', content_type='text/plain', status_code=500)

    return context.Response(status_code=requests.codes.no_content)


#
# Construct and send GetItem NoSQL Web API reuest
#
def _webapi_getitem(base_url, path_in_url, exp_attrs):

    url = base_url + path_in_url

    #
    # Construct the request json
    #
    request_json = {}

    request_json["AttributesToGet"] = ""

    for attr_name in exp_attrs:
        if request_json["AttributesToGet"] != "":
            request_json["AttributesToGet"] += ","
        request_json["AttributesToGet"] += attr_name

    payload = json.dumps(request_json)

    headers = {V3IO_HEADER_FUNCTION: "GetItem"}

    if WEBAPI_CRED is not None:
        headers["Authorization"] = str(WEBAPI_CRED)

    # send the request
    res = requests.put(url, data=payload, headers=headers)

    if res.status_code != requests.codes.ok:
        return

    response_json = json.loads(res.content)
    return response_json


#
# Construct and send UpdateItem NoSQL Web API reuest
#
def _webapi_updateitem(base_url, path_in_url, update_expr):

    url = base_url + path_in_url

    #
    # Construct the request json
    #
    request_json = {}

    request_json["UpdateExpression"] = update_expr

    payload = json.dumps(request_json)

    headers = {V3IO_HEADER_FUNCTION: "UpdateItem"}

    if WEBAPI_CRED is not None:
        headers["Authorization"] = str(WEBAPI_CRED)

    # send the request
    res = requests.put(url, data=payload, headers=headers)
    return res
