import requests
import json

V3IO_HEADER_FUNCTION = 'X-v3io-function'

#
# Construct and send a GetItem NoSQL Web API request
#
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
# Construct and send an UpdateItem NoSQL Web API request
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

