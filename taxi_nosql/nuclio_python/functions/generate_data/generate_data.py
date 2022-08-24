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
import os
import json
import random
from decimal import *

# Get the ingestion-function URL from the Nuclio function environment variables
INGEST_URL = os.getenv("INGEST_URL")

# List of GPS coordinates for randomly selected locations
locations = {
    'downtown_london': {'long': -0.1195, 'lat': 51.5033},
    'westminster': {'long': -0.1357, 'lat': 51.4975},
    'oxford_st': {'long': -0.1410, 'lat': 51.5154},
    'heathrow': {'long': -0.4543, 'lat': 51.4700},
    'heathrow_parking': {'long': -0.4473, 'lat': 51.4599},
    'gatwick': {'long': 0.1821, 'lat': 51.1537},
    'canary_wharf': {'long': -0.0235, 'lat': 51.5054}
}

# Most drivers are in downtown - provide more weight to downtown.
# Note that this is just an example.
drivers_weighted_locations = {'downtown_london': 4, 'westminster': 3}

# Most passengers are in airports - provide more weight to airports.
# Note that this is just an example.
passengers_weighted_locations = \
    {'heathrow': 4, 'heathrow_parking': 3, 'gatwick': 4}

# Set the number of drivers and passengers to ingest
num_drivers_to_ingest = 1000
num_passengers_to_ingest = 500

# Set the maximum valid driver and passenger ID values
max_driver_id = 5000
max_passenger_id = 5000


# Function handler - generate random drivers, passengers, and locations data
# and send it to the configured ingestion URL (INGEST_URL)
def handler(context, event):

    # Ingest current driver locations
    _ingest_locations(context, num_drivers_to_ingest, max_driver_id, 'driver',
                      drivers_weighted_locations)

    # Ingest current passenger locations
    _ingest_locations(context, num_passengers_to_ingest, max_passenger_id,
                      'passenger', passengers_weighted_locations)

    return context.Response(status_code=204)


# Ingest driver and passenger locations information
def _ingest_locations(context, num_records, max_record_id, record_type,
                      weighted_locations):

    # Get random driver/passenger locations and send the data for ingestion
    for x in range(1, num_records):

        # Get a weighted random location
        random_location = _get_random_location(_weighted_keys(locations,
                                               weighted_locations))

        # Construct the request's JSON body. The body includes the record type
        # (driver/passenger), the respective ID, and the GPS coordinates of the
        # current driver or passenger location.
        # For demo purposes, the location coordinates are generated as a random
        # offset of the current random weighted location.
        request_json = {
            'RecordType': record_type,
            'ID': random.randint(1, max_record_id),
            'Longitude':
                _get_random_offset(locations[random_location]['long']),
            'Latitude': _get_random_offset(locations[random_location]['lat'])
        }

        # Ingest the location data by sending an HTTP request to the configured
        # ingestion URL
        response = requests.put(INGEST_URL, data=json.dumps(request_json))

        if response.status_code != requests.codes.ok:
            message = f'''Ingestion of {record_type}s failed with error code
               {response.status_code}'''
            context.logger.error(message)
            return context.Response(body={'error': message}, status_code=500)


# Get a random location from the available locations
def _get_random_location(locations):

    random_location_name = random.choice(locations)

    return random_location_name


# Generate a close random offset of the given location - for demo purposes only
def _get_random_offset(location):

    rnd_radius = random.randint(0, 8)
    rnd_offset = random.randint(-rnd_radius, rnd_radius)
    new_location = Decimal(location) + (Decimal(rnd_offset) / Decimal(300))

    return str(new_location)


# Get weighted keys: given dictionary "d", return the dictionary keys weighted
# by weight "weights". For example:
#  input: d = {'a': 1, 'b': 2, 'c': 3}, weights = {'b': 3, 'c': 2}
#  output: ['a', 'b', 'b', 'b', 'c', 'c']
def _weighted_keys(d, weights):
    result = []

    for key in d.keys():
        result.extend([key] * weights.get(key, 1))

    return result

