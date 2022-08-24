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
import requests
import json
import threading
import httplib

V3IO_HEADER_FUNCTION = 'X-v3io-function'


# TODO: error handling
def ngx_put_object(
        s, base_url, path_in_url, file_name, payload):
    obj_url = base_url + path_in_url + file_name
    res = s.put(obj_url, data=payload)
    return res


#
# Construct and send a GetItem web request
#
def ngx_get_item_request(
        s, base_url, path_in_url, table_name=None, key=None, exp_attrs=None, expected_result=requests.codes.ok):
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

    assert res.status_code == expected_result
    if expected_result != requests.codes.ok:
        return

    response_json = json.loads(res.content)
    return response_json

#
# Construct and send a GetItems web request
# Returns an array of objects
#
def ngx_get_items_request(
        s, base_url, path_in_url, table_name=None, key=None, exp_attrs=None, limit_amount=10,
        expected_result=requests.codes.ok):
    url = base_url + path_in_url

    request_json = {}
    responses_json = []

    request_json["limit"] = limit_amount

    if table_name is not None:
        request_json["TableName"] = table_name

    request_json["AttributesToGet"] = ""

    for attr_name in exp_attrs:
        if request_json["AttributesToGet"] != "":
            request_json["AttributesToGet"] += ","
        request_json["AttributesToGet"] += attr_name

    # Break when the reply shows no more items or the limit is reached
    while True:
        payload = json.dumps(request_json)
        headers = {V3IO_HEADER_FUNCTION: 'GetItems'}
        res = s.put(url, data=payload, headers=headers)

        assert res.status_code == expected_result
        if expected_result != requests.codes.ok:
            return

        response_json = json.loads(res.content)

        for i in range(0, response_json["NumItems"]):
            if response_json["Items"][i]["__name"]["S"] != ".#schema":
                responses_json.append(response_json["Items"][i])
                limit_amount -= 1
            else:
                print("Skipping .#schema file")

        if limit_amount > 0:
            request_json["limit"] = limit_amount
        else:
            break

        if response_json["LastItemIncluded"] == "FALSE":
            request_json["Marker"] = response_json["NextMarker"]
        else:
            break

    return responses_json

class __get_items_thread(threading.Thread):
    def __init__(self, s, url, data, headers, threadID, result, index):
        threading.Thread.__init__(self)
        self.s = s
        self.url = url
        self.data = data
        self.headers = headers
        self.threadID = threadID
        self.result = result
        self.index = index

    def run(self):
        try:
            self.result[self.index] = self.s.put(self.url, data=self.data, headers=self.headers)
        except requests.ConnectionError as e:
            print("Error establishing connection: " + str(e))
            self.result[self.index] = None
        except Exception as e:
            print("Error establishing connection: " + str(e))
            self.result[self.index] = None

#
# Construct and send a GetItems web request
# Returns an array of objects
#
def ngx_get_items_request_parallel(
        s, base_url, path_in_url, table_name=None, key=None, exp_attrs=None, limit_amount=10,
        parallelism=36, verbose=0,
        expected_result=requests.codes.ok):
    url = base_url + path_in_url

    request_json = [{} for _ in range(parallelism)]
    response_json = [{} for _ in range(parallelism)]
    responses_json = []
    payload = [{} for _ in range(parallelism)]
    res = [{} for _ in range(parallelism)]
    worker_threads = [{} for _ in range(parallelism)]
    alive = [{} for _ in range(parallelism)]
    done = False
    records_processed = 0

    ignore_limit = False if limit_amount > 0 else True

    for vn in range(parallelism):
        alive[vn] = True

    for vn in range(parallelism):
        if not ignore_limit:
            request_json[vn]["Limit"] = limit_amount
        request_json[vn]["Segment"] = vn
        request_json[vn]["TotalSegment"] = parallelism

        if table_name is not None:
            request_json[vn]["TableName"] = table_name

        request_json[vn]["AttributesToGet"] = ""

        for attr_name in exp_attrs:
            if request_json[vn]["AttributesToGet"] != "":
                request_json[vn]["AttributesToGet"] += ","
            request_json[vn]["AttributesToGet"] += attr_name

    # Break when the reply shows no more items or the limit is reached
    while not done:
        for vn in range(parallelism):
            if alive[vn]:
                payload[vn] = json.dumps(request_json[vn])
                headers = {V3IO_HEADER_FUNCTION: 'GetItems'}
                if verbose >= 3:
                    print("Payload for thread " + str(vn))
                    print(payload[vn])
                worker_threads[vn] = __get_items_thread(s, url = url, data = payload[vn],
                                                        headers = headers,
                                                        threadID = vn, result = res, index = vn)
                worker_threads[vn].start()

        for vn in range(parallelism):
            if alive[vn]:
                worker_threads[vn].join()

        for vn in range(parallelism):
            if alive[vn]:
                if res[vn] is None or res[vn].status_code != expected_result:
                    if res[vn] is None:
                        print("Error encountered on thread " + str(vn))
                    elif res[vn].status_code == requests.codes.not_found:
                        print("Error finding container and/or table (" + str(url) + ") on thread " + str(vn) + ". Code: " +
                              str(res[vn].status_code) + ". Description: " + str(httplib.responses[res[vn].status_code]))
                    else:
                        print("Error encountered on thread " + str(vn) + ". Code: " +
                              str(res[vn].status_code) + ". Description: " + str(httplib.responses[res[vn].status_code]))

                    return None

        for vn in range(parallelism):
            if alive[vn]:
                response_json[vn] = json.loads(res[vn].content)

                if verbose >= 2:
                    print("For thread " + str(vn) + " number of items is " + str(response_json[vn]["NumItems"]))

                for i in range(0, response_json[vn]["NumItems"]):
                    if response_json[vn]["Items"][i]["__name"]["S"] != ".#schema":
                        responses_json.append(response_json[vn]["Items"][i])
                        records_processed += 1
                        if not ignore_limit:
                            limit_amount -= 1
                    else:
                        print("Skipping .#schema file")

                if not ignore_limit:
                    if limit_amount > 0:
                        request_json[vn]["Limit"] = limit_amount
                    else:
                        done = True
                        break

                if response_json[vn]["LastItemIncluded"] == "FALSE":
                    request_json[vn]["Marker"] = response_json[vn]["NextMarker"]
                else:
                    alive[vn] = False
        if verbose >= 2:
            print("Table-items processed = " + str(records_processed))

        if not done:
            done = True
            for vn in range(parallelism):
                if alive[vn]:
                    done = False
                    break

    return responses_json

#
# Construct and send an UpdateItem web request
#
def ngx_update_expression_request(
        s, base_url, path_in_url, table_name=None, key=None, mode=None, update_expr=None, text_filter=None,
        type="UpdateItem",
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
    res = s.put(url, data=payload, headers=headers)
    return res

