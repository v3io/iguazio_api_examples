import requests
import json
import os
import s2sphere

WEBAPI_URL = os.getenv('WEBAPI_URL')

DRIVERS_PATH_IN_URL = os.getenv('DRIVERS_TABLE')
CELLS_PATH_IN_URL   = os.getenv('CELLS_TABLE')

V3IO_HEADER_FUNCTION = 'X-v3io-function'

def handler(context, event):

    input_data_json = event.body 

    input_data = json.loads(input_data_json)

    driver_id = str(input_data ["driverID"])

    longitude = float (input_data["longitude"])
    latitude = float (input_data["latitude"])

    # Use google s2Sphere library to calculate Cell 
    p1 = s2sphere.LatLng.from_degrees(latitude,longitude)
    cell = s2sphere.CellId.from_lat_lng(p1).parent(15)
    cell_id = str(cell.id())
    
    s = requests.Session()

    # update driver current and previous location 
    res = ngx_update_expression_request(s,WEBAPI_URL, DRIVERS_PATH_IN_URL + "driver_" + driver_id, None, None,
                                        "CreateOrReplaceAttributes",
                                        "previous_cell_id=current_cell_id;current_cell_id=" + cell_id + ";change_cell_id_indicator=(previous_cell_id != current_cell_id);",
                                        "exists(current_cell_id)")
    
    if res.status_code == requests.codes.bad_request:
            ngx_update_expression_request(s,WEBAPI_URL, DRIVERS_PATH_IN_URL + "driver_" + driver_id, None, None,
                                          "CreateOrReplaceAttributes",
                                          "current_cell_id=" + cell_id + ";previous_cell_id=0;change_cell_id_indicator=(1==1);",
                                          "(1==1)")

    # Get current and previous cell for driver 
    response_json = ngx_get_item_request(s,WEBAPI_URL, DRIVERS_PATH_IN_URL+"driver_"+driver_id,None,None,exp_attrs=["change_cell_id_indicator","current_cell_id","previous_cell_id"])

    # Check if a cell update is needed
    attrs = response_json["Item"]
    change_cell_id_indicator_val = attrs["change_cell_id_indicator"]["BOOL"]
    current_cell_id_val = attrs["current_cell_id"]["N"]
    previous_cell_id_val = attrs["previous_cell_id"]["N"]
    #for key, value in attrs.items():
    #     print("attr: {}, value: {}".format(key, value["N"]))

    # Try to increase the count on the cell the driver moved to
    if change_cell_id_indicator_val:
        res= ngx_update_expression_request(s,WEBAPI_URL, CELLS_PATH_IN_URL + "cell_"+ current_cell_id_val, None, None,
                                          "CreateOrReplaceAttributes",
                                          "count=count+1;",
                                          "exists(count)")
        # If the cell doesn't exists create a new one
        if res.status_code == requests.codes.bad_request:
                ngx_update_expression_request(s,WEBAPI_URL, CELLS_PATH_IN_URL + "cell_" + current_cell_id_val, None, None,
                                              "CreateOrReplaceAttributes",
                                              "count=1;",
                                              None)
        # Decrease the count on the cell the driver moved from
        ngx_update_expression_request(s,WEBAPI_URL, CELLS_PATH_IN_URL + "cell_" + previous_cell_id_val, None, None,
                                          "CreateOrReplaceAttributes",
                                          "count=count-1;;",
                                          None)

    return context.Response(body='Ingestion completed successfully',
                            headers={},
                            content_type='text/plain',
                            status_code=200)

def ngx_get_item_request(
        s,base_url, path_in_url, table_name=None, key=None, exp_attrs=None, expected_result=requests.codes.ok):
    url = base_url + path_in_url

    request_json = {}

    if table_name is not None:
        request_json["TableName"] = table_name

    request_json["AttributesToGet"] = ""

    for attr_name in exp_attrs:
        if request_json["AttributesToGet"] != "":
            request_json["AttributesToGet"] += ","
        request_json["AttributesToGet"] += attr_name

    payload = json.dumps(request_json)
    headers = {V3IO_HEADER_FUNCTION: 'GetItem'}
    res = s.put(url, data=payload, headers=headers)

    #print(res.content)
    assert res.status_code == expected_result
    if expected_result != requests.codes.ok:
        return

    response_json = json.loads(res.content)
    return response_json

#
# Construct and send UpdateItem web reuest
#
def ngx_update_expression_request(
        s,base_url, path_in_url, table_name=None, key=None, mode=None, update_expr=None, text_filter=None, type="UpdateItem",
        expected_result=requests.codes.no_content):
    url = base_url + path_in_url

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
    headers = {V3IO_HEADER_FUNCTION: type}
    #print(payload)
    res = s.put(url, data=payload, headers=headers)
    #print(res)
    #assert res.status_code == expected_result
    return res

