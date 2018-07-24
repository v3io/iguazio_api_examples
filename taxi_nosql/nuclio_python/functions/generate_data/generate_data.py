import requests
import os
import json
import random
from decimal import *

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

# Get the ingestion-function URL from the Nuclio function environment variables
ingest_url = os.getenv("INGEST_URL")

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
    _ingest_locations(context, ingest_url, num_drivers_to_ingest,
                      max_driver_id, 'driver', drivers_weighted_locations)

    # Ingest current passenger locations
    _ingest_locations(context, ingest_url, num_passengers_to_ingest,
                      max_passenger_id, 'passenger',
                      passengers_weighted_locations)

    return context.Response(status_code=204)


# Ingest driver and passenger locations information
def _ingest_locations(context, ingest_url, num_records, max_record_id,
                      record_type, weighted_locations):

    # Get random driver/passenger locations and send the data for ingestion
    for x in range(1, num_records):

        # Get a weighted random location
        random_location = _get_random_location(_weighted_keys(locations,
                                               weighted_locations))

        # Build a JSON request body with the record type (driver/passenger),
        # the respective ID, and the GPS coordinates of the current driver or
        # passenger location. For demo purposes, the location coordinates are
        # generated as a random offset of the current random weighted location.
        request = {
            'RecordType': record_type,
            'ID': random.randint(1, max_record_id),
            'Longitude':
                _get_random_offset(locations[random_location]['long']),
            'Latitude': _get_random_offset(locations[random_location]['lat'])
        }

        # Ingest the location data by sending a PUT Object web-API request to
        # the configured ingestion URL
        response = requests.put(ingest_url, data=json.dumps(request))

        if response.status_code != requests.codes.ok:
            message = f'''Ingestion of drivers failed with error code
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

