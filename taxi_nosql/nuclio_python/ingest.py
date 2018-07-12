import requests
import json
import os
import s2sphere

# Get configuration information from environment variables defined using Nuclio
# Web-APIs (web-gateway) URL
WEBAPI_URL     = str(os.getenv('WEBAPI_URL'))
# Container name
CONTAINER_NAME = str(os.getenv('CONTAINER_NAME'))
# Web-APIs user credentials (used for HTTP authentication)
WEBAPI_USER = os.getenv('WEBAPI_USER')
WEBAPI_PASSWORD = os.getenv('WEBAPI_PASSWORD')
WEBAPI_CRED = os.getenv('WEBAPI_CRED')
# Table paths
DRIVERS_TABLE_PATH = CONTAINER_NAME + str(os.getenv('DRIVERS_TABLE'))
PASSENGERS_TABLE_PATH = CONTAINER_NAME + str(os.getenv('PASSENGERS_TABLE'))
CELLS_TABLE_PATH   = CONTAINER_NAME + str(os.getenv('CELLS_TABLE'))

DRIVER_PREFIX = 'drivers_'
PASSENGER_PREFIX = 'passengers_'

V3IO_HEADER_FUNCTION = 'X-v3io-function'

def handler(context, event):

    # Read the data to be ingested from the input JSON request body
    input_data_json = event.body 
    input_data = json.loads(input_data_json)

    record_type = str(input_data ["RecordType"])

    id = str(input_data ["ID"])
    
    longitude = float (input_data["longitude"])
    latitude = float (input_data["latitude"])

    # Use the Google s2sphere library to calculate a cell from the longitude
    # and latitude degrees
    p1 = s2sphere.LatLng.from_degrees(latitude,longitude)
    cell = s2sphere.CellId.from_lat_lng(p1).parent(15)
    cell_id = str(cell.id())
    
    # Create a session for sending NoSQL Web API requests
    s = requests.Session()

    # Provide webapi user/pass
    if WEBAPI_USER is not None:
        s.auth = (str(WEBAPI_USER), str(WEBAPI_PASSWORD))
    
    # Ingestion of both drivers and passengers are supported
    # Depending on record type, relevant tables will be updated
    if record_type == 'driver':
        ITEM_PREFIX = DRIVER_PREFIX
        ITEM_PATH   = DRIVERS_TABLE_PATH
    else :
        ITEM_PREFIX = PASSENGER_PREFIX
        ITEM_PATH = PASSENGERS_TABLE_PATH

    # Update the driver's current and previous location 
    res = ngx_update_expression_request(s,WEBAPI_URL, ITEM_PATH + ITEM_PREFIX +id, None, None,
                                            None,
                                            "SET previous_cell_id=if_not_exists(current_cell_id,0);current_cell_id=" + cell_id + ";change_cell_id_indicator=(previous_cell_id != current_cell_id);",
                                            None)

    if res.status_code not in (200,204):
            context.logger.error ("Error during update of drivers table. Error code is "+str(res.status_code))
            return context.Response(body='Internal error during ingestion',content_type='text/plain',status_code=500)
    
    # Get the driver's current and previous cell
    response_json = ngx_get_item_request(s,WEBAPI_URL, ITEM_PATH + ITEM_PREFIX +id,None,None,exp_attrs=["change_cell_id_indicator","current_cell_id","previous_cell_id"])

    # Check whether a cell-update is needed
    attrs = response_json["Item"]
    change_cell_id_indicator_val = attrs["change_cell_id_indicator"]["BOOL"]
    current_cell_id_val = attrs["current_cell_id"]["N"]
    previous_cell_id_val = attrs["previous_cell_id"]["N"]

    # If the driver's cell has changed, increase the drivers count for the new
    # cell and decrease the count for the old cell
    if change_cell_id_indicator_val:
            # Increase the count for the driver's new (current) cell
            res=ngx_update_expression_request(s,WEBAPI_URL, CELLS_TABLE_PATH + "cell_"+ current_cell_id_val, None, None,
                                          None,
                                          "SET "+ITEM_PREFIX+"count=if_not_exists("+ITEM_PREFIX+"count,0)+1;",
                                          None)

            if res.status_code not in (200,204):
                context.logger.error ("Error during increment of count in cells table. Error code is "+str(res.status_code))
                return context.Response(body='Internal error during ingestion',content_type='text/plain',status_code=500)


            # Decrease the count for the driver's previous cell
            res = ngx_update_expression_request(s,WEBAPI_URL, CELLS_TABLE_PATH + "cell_" + previous_cell_id_val, None, None,None,
                                          "SET "+ITEM_PREFIX+"count="+ITEM_PREFIX+"count-1;",
                                          None)

            if res.status_code not in (200,204):
                context.logger.error ("Error during decrement of count in cells table. Error code is "+str(res.status_code))
                return context.Response(body='Internal error during ingestion',content_type='text/plain',status_code=500)

    return context.Response(body='Ingestion completed successfully',
                            headers={},
                            content_type='text/plain',
                            status_code=200)

#
# Construct and send a GetItem NoSQL Web API request
#
def ngx_get_item_request(
        s,base_url, path_in_url, table_name=None, key=None, exp_attrs=None, expected_result=requests.codes.ok):
    url = base_url + path_in_url

    # Build a JSON request body
    request_json = {}

    if table_name is not None:
        request_json["TableName"] = table_name

    request_json["AttributesToGet"] = ""

    for attr_name in exp_attrs:
        if request_json["AttributesToGet"] != "":
            request_json["AttributesToGet"] += ","
        request_json["AttributesToGet"] += attr_name

    payload = json.dumps(request_json)
    
    if WEBAPI_CRED is None:
        headers = {V3IO_HEADER_FUNCTION: 'GetItem'}
    else:
        headers = {V3IO_HEADER_FUNCTION: 'GetItem',"Authorization": str(WEBAPI_CRED)}
    
    # Send the request
    res = s.put(url, data=payload, headers=headers)

    assert res.status_code == expected_result
    if expected_result != requests.codes.ok:
        return

    response_json = json.loads(res.content)
    return response_json

#
# Construct and send an UpdateItem NoSQL Web API request
#
def ngx_update_expression_request(
        s,base_url, path_in_url, table_name=None, key=None, mode=None, update_expr=None, text_filter=None, type="UpdateItem",
        expected_result=requests.codes.no_content):
    url = base_url + path_in_url

    # Build a JSON request body
    request_json = {}

    if table_name is not None:
        request_json["TableName"] = table_name

    if mode is not None:
        request_json["UpdateMode"] = mode

    if update_expr is not None:
        request_json["UpdateExpression"] = update_expr

    if text_filter is not None:
        request_json["ConditionExpression"] = text_filter

    payload = json.dumps(request_json)
    
    if WEBAPI_CRED is None:
       headers = {V3IO_HEADER_FUNCTION: type }
    else:
       headers = {V3IO_HEADER_FUNCTION: type ,"Authorization": str(WEBAPI_CRED)}

    # Send the request
    res = s.put(url, data=payload, headers=headers)
    #assert res.status_code == expected_result
    return res
