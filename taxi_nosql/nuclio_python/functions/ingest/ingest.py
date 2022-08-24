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
import os
import s2sphere

# Get configuration information from Nuclio function environment variables
# Web-APIs (web-gateway service) URL
WEBAPI_URL = str(os.getenv('WEBAPI_URL'))
# Base64 encoded web-APIs user credentials for HTTP authentication
WEBAPI_CRED = os.getenv('WEBAPI_CRED')
# Container name - for storing the ingested data
CONTAINER_NAME = str(os.getenv('CONTAINER_NAME'))
# Table paths
DRIVERS_TABLE_PATH = CONTAINER_NAME + str(os.getenv('DRIVERS_TABLE'))
PASSENGERS_TABLE_PATH = CONTAINER_NAME + str(os.getenv('PASSENGERS_TABLE'))
CELLS_TABLE_PATH = CONTAINER_NAME + str(os.getenv('CELLS_TABLE'))

# Define record-type-dependent (driver/passenger) attribute-name prefixes
DRIVER_PREFIX = 'drivers_'
PASSENGER_PREFIX = 'passengers_'

# Web-API header for defining the operation (function) to execute
V3IO_HEADER_FUNCTION = 'X-v3io-function'


# Function handler - retrieve and analyze driver/passenger location data and
# ingest it into drivers/passengers and cells tables
def handler(context, event):

    # Generate ingestion data from the input received in the event body:
    # - Path to the drivers/passengers table
    # - Value of the item's primary-key attribute = the item's name
    # - Current-location cell ID
    # - Record-type-dependent (driver/passenger) attribute-name prefix
    table_path, key_value, cell_id, item_prefix = \
        _generate_data_from_input(event.body)
    # Set the path to the table item
    item_path = table_path + key_value
    # Set the primary-key attribute's name (= the item's name) and type
    key_name = "id"
    key_type = "N"

    # Update the current and previous driver/passenger location information;
    # if the item doesn't already exist in the table, it will be created:
    # - Set the item's primary key (name)
    # - Set the previous_cell_id attribute (column) to the value of the
    #   current_cell_id attribute or to zero for a new driver or passenger ID.
    # - Set the current_cell_id attribute (column) to the driver's/passenger's
    #   current cell ID.
    # - Set the change_cell_id_indicator attribute (column) to a Boolean value
    #   that indicates whether the driver's/passenger's cell has changed.
    res = _webapi_updateitem(
        WEBAPI_URL,
        table_path,
        key_value,
        key_name,
        key_type,
        f'''{key_name} = {key_value};
            previous_cell_id = if_not_exists(current_cell_id, "0");
            current_cell_id = "{cell_id}";
            change_cell_id_indicator = (previous_cell_id != current_cell_id);
        ''')

    if res.status_code != requests.codes.no_content:
        context.logger.error(f'''Error during update of {WEBAPI_URL}{item_path}.
            Error code is {res.status_code}''')
        return context.Response(status_code=500)

    # Update the cells table based on the driver's or passenger's current and
    # previous locations
    res = _update_cells_table(context, item_path, item_prefix)
    if res.status_code != requests.codes.no_content:
        context.logger.error(f'''Error during update of cells table.
            Error code is {res.status_code}''')
        return context.Response(status_code=500)

    # Return status code 200 - completed successfully
    return context.Response(status_code=200)


# Generate data from input - parse the input JSON object and analyze the data
def _generate_data_from_input(input_data_json):

    # Read the data to be ingested from the input JSON object
    input_data = json.loads(input_data_json)

    # Extract the record type (driver/passenger), the related ID, and the GPS
    # coordinates of the driver's/passenger's location from the input data
    record_type = str(input_data["RecordType"])
    input_id = str(input_data["ID"])
    longitude = float(input_data["Longitude"])
    latitude = float(input_data["Latitude"])

    # Use the s2Sphere library to determine the Google S2 cell for the
    # longitude and latitude GPS coordinates and retrieve the cell ID
    p1 = s2sphere.LatLng.from_degrees(latitude, longitude)
    cell = s2sphere.CellId.from_lat_lng(p1).parent(15)
    cell_id = str(cell.id())

    # Set the record-type-dependent attribute-name prefix and table path
    if record_type == 'driver':
        item_prefix = DRIVER_PREFIX
        table_path = DRIVERS_TABLE_PATH
    else:
        item_prefix = PASSENGER_PREFIX
        table_path = PASSENGERS_TABLE_PATH

    # Set the value of the item's primary-key attribute (= the item's name)
    key_value = input_id

    # Return the generated data:
    # - Path to the drivers/passengers table
    # - Value of the item's primary-key attribute = the item's name
    # - Current-location cell ID
    # - Record-type-dependent (driver/passenger) attribute-name prefix
    return table_path, key_value, cell_id, item_prefix


# Update the cells table: if a driver's/passenger's location cell has changed,
# update the driver/passenger count of the previous and new cell in the table
def _update_cells_table(context, item_path, item_prefix):

    # Get the driver's/passenger's Boolean cell-change indicator and current
    # and previous cell locations
    response_json = _webapi_getitem(
        WEBAPI_URL, item_path,
        exp_attrs=["change_cell_id_indicator",
                   "current_cell_id",
                   "previous_cell_id"])

    # Extract the values of the cell-change indicator and current and previous
    # cell ID attributes from the retrieved driver/passenger table item
    attrs = response_json["Item"]
    change_cell_id_indicator_val = attrs["change_cell_id_indicator"]["BOOL"]
    current_cell_id_val = attrs["current_cell_id"]["S"]
    previous_cell_id_val = attrs["previous_cell_id"]["S"]

    # Check whether a cell update is needed: if the driver's or passenger's
    # cell has changed (as indicated by the value of the
    # change_cell_id_indicator attribute), increase the new-cell
    # drivers/passengers count and decrease the equivalent old-cell count
    if change_cell_id_indicator_val:
            # Set the name of the cells-table count attribute to update, based
            # on the record type (driver/passenger)
            count_attribute = item_prefix + 'count'
            # Set the name, value, and type of the item's primary-key attribute
            key_name = "cell_id"
            key_value = current_cell_id_val
            key_type = "S"

            # Increase the driver/passenger count for the current cell:
            # - Set the new-location cell item's primary key (name)
            # - If the driver/passenger cells-table count attribute (column)
            #   doesn't yet exist, add it and initialize its value to zero.
            # - Increase the value of the count attribute by one.
            res = _webapi_updateitem(
                WEBAPI_URL,
                CELLS_TABLE_PATH,
                key_value,
                key_name,
                key_type,
                f'''{key_name} = "{key_value}";
                    {count_attribute}=if_not_exists({count_attribute},0)+1;
                ''')

            if res.status_code != requests.codes.no_content:
                context.logger.error(f'''Error during increment of count in
                    cells table. Error code is {res.status_code}''')
                return context.Response(body='Internal error during ingestion',
                                        content_type='text/plain',
                                        status_code=500)

            # Decrease the driver/passenger count for the previous cell: if the
            # previous count is greater than zero, subtract one from this count
            if int(previous_cell_id_val) > 0:
                # Set the name and value of the item's primary-key attribute
                key_value = previous_cell_id_val

                # Update the item
                res = _webapi_updateitem(
                    WEBAPI_URL,
                    CELLS_TABLE_PATH,
                    key_value,
                    key_name,
                    f'SET {count_attribute}={count_attribute}-1;')

            if res.status_code != requests.codes.no_content:
                    context.logger.error(f'''Error during decrement of count in
                        cells table. Error code is {res.status_code}''')
                    return context.Response(body='Internal ingestion error',
                                            content_type='text/plain',
                                            status_code=500)

    return context.Response(status_code=requests.codes.no_content)


# Prepare and send a GetItem NoSQL Web API request
def _webapi_getitem(base_url, path_in_url, exp_attrs):

    # Set the request URL
    url = os.path.join(base_url, path_in_url)

    # Construct the request's JSON body
    request_json = {}

    # Define the item attributes to retrieve in the request
    request_json["AttributesToGet"] = ""
    # Extract the attribute names from the exp_attrs parameter and add each
    # attribute to the request
    for attr_name in exp_attrs:
        if request_json["AttributesToGet"] != "":
            request_json["AttributesToGet"] += ","
        request_json["AttributesToGet"] += attr_name

    # Set the request payload
    payload = json.dumps(request_json)

    # Set the request headers
    headers = {V3IO_HEADER_FUNCTION: "GetItem"}

    if WEBAPI_CRED is not None:
        # Add a Basic HTTP authentication header to authenticate the user
        headers["Authorization"] = str(WEBAPI_CRED)

    # Send the request
    res = requests.put(url, data=payload, headers=headers)

    if res.status_code != requests.codes.ok:
        return

    response_json = json.loads(res.content)
    return response_json


# Prepare and send an UpdateItem NoSQL Web API request
def _webapi_updateitem(base_url, table_path, key_value, key_name, key_type, update_expr):

    # Set the request URL
    url = os.path.join(base_url, table_path)

    # Construct the request's JSON body:
    # - "Key" identifies is the item's primary-key attribute, which identifies
    #   the item to update. The name of this attribute is also the item name,
    #   which is automatically assigned to the __name system attribute.
    # - "UpdateExpression" is an update-expression string that defines the
    #   item-attributes update logic.
    request_json = {
        "Key": {key_name: {key_type: key_value}},
        "UpdateExpression": update_expr
    }

    # Set the request payload
    payload = json.dumps(request_json)

    # Set the request headers
    headers = {V3IO_HEADER_FUNCTION: "UpdateItem"}

    if WEBAPI_CRED is not None:
        # Add a Basic HTTP authentication header to authenticate the user
        headers["Authorization"] = str(WEBAPI_CRED)

    # Send the request
    response = requests.put(url, data=payload, headers=headers)
    return response

