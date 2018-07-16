import requests
import os
import json
import random
from decimal import *

# List of GPS coordinates for randomly selected locations
all_locations = {
    'downtown_london': {'long': -0.1195, 'lat': 51.5033},
    'westminster': {'long': -0.1357, 'lat': 51.4975},
    'oxford_St': {'long': -0.1410, 'lat': 51.5154},
    'heathrow': {'long': -0.4543, 'lat': 51.4700},
    'heathrow_parking': {'long': -0.4473, 'lat': 51.4599},
    'gatwick': {'long': 0.1821, 'lat': 51.1537},
    'canary_wharf': {'long': -0.0235, 'lat': 51.5054}
}

# Most drivers are in downtown - provide more weight to downtown - note this is just an example
drivers_weighted_locations = {'downtown_london':4, 'westminster':3}

# Most passengers are in airports - provide more weight to downtown - note this is just an example
passengers_weighted_locations = {'heathrow':4, 'heathrow_parking':3, 'gatwick':4}

# Get IP and Port of the ingestion function from Nuclio environment variables
ingest_url = os.getenv("INGEST_URL")

# Number of drivers and passengers to ingest
num_drivers_to_ingest = 1000
num_passengers_to_ingest = 500

# Max ID for drivers and passengers, defines the total number in the system
max_driver_id = 5000
max_passenger_id = 5000


def handler(context, event):

    # ingest drivers
    _ingest_locations(context, ingest_url, num_drivers_to_ingest, max_driver_id, 'driver', drivers_weighted_locations)

    # ingest passengers
    _ingest_locations(context, ingest_url, num_drivers_to_ingest, max_passenger_id, 'passenger', passengers_weighted_locations)

    return context.Response(status_code=204)


def _ingest_locations(context, ingest_url, num_records, max_record_id, record_type, weighted_locations):

    # generate random location for 1000 drivers and send for ingestion
    for x in range(1, num_records):

        # get a random locations
        random_location = _get_random_location(_weighted_keys (all_locations,weighted_locations))

        request = {
                  'RecordType': record_type,
                  'ID': random.randint(1, max_record_id),
                  'Longitude': _get_random_offset(all_locations[random_location]['long']),
                  'Latitude': _get_random_offset (all_locations[random_location]['lat'])
        }

        response = requests.put(ingest_url, data=json.dumps(request))

        if response.status_code != requests.codes.ok:
            message = f'Ingestion of drivers failed with error code {response.status_code}'
            context.logger.error(message)
            return context.Response(body={'error': message}, status_code=500)


# get a random location from the available locations
def _get_random_location(locations):

    random_location_name = random.choice(locations)

    return random_location_name


# move to a close offset of the exact point - for demo purposes only
def _get_random_offset(location):

    rnd_radius = random.randint(0, 8)

    rnd_offset = random.randint (-rnd_radius,rnd_radius)

    new_location = Decimal(location) + (Decimal(rnd_offset) / Decimal(300))

    return str(new_location)

# given dict "d", returns the keys weighted by weight "weights"
# For example: 
#  input: d = {'a': 1, 'b': 2, 'c': 3}, weights = {'b': 3, 'c': 2}
#  output: ['a', 'b', 'b', 'b', 'c', 'c']
def _weighted_keys(d, weights):
  result = []
  
  for key in d.keys():
    result.extend([key] * weights.get(key, 1))

  return result
