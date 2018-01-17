# Generate random drivers stream data

from decimal import *
from random import *

# GPS coordinates
Downtown = [-0.1195, 51.5033]

Westminster = [-0.1357, 51.4975]

Oxford_St = [-0.1410, 51.5154]

Heathrow = [-0.4543, 51.4700]

Heathrow_Parking = [-0.4473, 51.4599]

Gatwick = [0.1821, 51.1537]

Canary_Wharf = [-0.0235, 51.5054]

Locations = [Canary_Wharf, Canary_Wharf, Downtown, Westminster, Oxford_St,
             Oxford_St, Oxford_St, Heathrow, Heathrow_Parking, Gatwick]

# Driver ride status
Statuses = ["Available", "Busy", "Passenger"]

# Create a driver-information CSV file
print("Driver, Timestamp, Longitude, Latitude, status")
for x in range(1, 1000):
    rnd_location = randint(0, 9)
    rnd_radius = randint(0, 8)
    for y in range(1, 300):
        rnd_driver = randint(1, 5000)
        rnd_long = randint(-rnd_radius, rnd_radius)
        rnd_lat = randint(-rnd_radius, rnd_radius)
        long = Decimal(Locations[rnd_location][0]) + \
            (Decimal(rnd_long) / Decimal(300))
        lat = Decimal(Locations[rnd_location][1]) + \
            (Decimal(rnd_lat) / Decimal(300))
        rnd_status = randint(0, 2)
        status = Statuses[rnd_status]
        print("%d, 2017-12-05 09:00:00.050000000, %f, %fi, %s"
              % (rnd_driver, long, lat, status))

