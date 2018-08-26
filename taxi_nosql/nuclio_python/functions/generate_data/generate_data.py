import requests
import os
import json
from decimal import *
from random import *

def handler(context, event):

    # list of random locations 
    Downtown_London = [-0.1195,51.5033]
    Westminster = [-0.1357,51.4975]
    Oxford_St = [-0.1410,51.5154]
    Heathrow = [-0.4543,51.4700]
    Heathrow_Parking = [-0.4473,51.4599]
    Gatwick =  [0.1821,51.1537]
    Canary_Wharf = [-0.0235,51.5054]
    Locations = [Canary_Wharf,Canary_Wharf,Downtown_London,Westminster,Oxford_St,Oxford_St,Oxford_St,Heathrow,Heathrow_Parking,Gatwick]

    INGEST_URL = os.getenv ("INGEST_URL")

    s = requests.Session()
    request_json = {}

    # generate random location for 1000 drivers and send for ingestion
    for x in range (1,1000):
        rnd_driver = randint (1,5000)
        rnd_location = randint (0,9)
        rnd_radius =randint (0,8)
        rnd_long = randint (-rnd_radius,rnd_radius)
        rnd_lat  = randint (-rnd_radius,rnd_radius)
        longitude =  Decimal (Locations[rnd_location][0]) + (Decimal (rnd_long) / Decimal (300))
        latitude = Decimal (Locations[rnd_location][1])  + (Decimal (rnd_lat) / Decimal (300))
        
        context.logger.info('driver id - '+ str(rnd_driver))

        request_json["driverID"] = rnd_driver
        request_json["longitude"] = str (longitude)
        request_json["latitude"] = str (latitude)
        
        payload = json.dumps(request_json)

        res = s.put(INGEST_URL, data=payload)
        
        context.logger.info(request_json)
        context.logger.info(res)

    context.logger.info('End - Generating Data')

    return context.Response(body='Ingestion of 1000 drivers completed successfully',
                            headers={},
                            content_type='text/plain',
                            status_code=200)


