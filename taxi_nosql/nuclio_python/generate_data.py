import requests
import os
import json
from decimal import *
from random import *

def handler(context, event):

    # Get IP and Port of the ingestion function from environment variables defined using Nuclio
    INGEST_URL = os.getenv ("INGEST_URL")
    
    # List of random locations - feel free to replace the list with your favourite locations
    Downtown_London = [-0.1195,51.5033]
    Westminster = [-0.1357,51.4975]
    Oxford_St = [-0.1410,51.5154]
    Heathrow = [-0.4543,51.4700]
    Heathrow_Parking = [-0.4473,51.4599]
    Gatwick =  [0.1821,51.1537]
    Canary_Wharf = [-0.0235,51.5054]
    Locations = [Canary_Wharf,Canary_Wharf,Downtown_London,Westminster,Oxford_St,Oxford_St,Oxford_St,Heathrow,Heathrow_Parking,Gatwick]

    # Get IP and Port of the ingestion function from environment variables defined using Nuclio
    INGEST_URL = os.getenv ("INGEST_URL")

    # Create a session for sending requests for ingestion
    s = requests.Session()
    request_json = {}

    # generate random location for drivers and send for ingestion
    for x in range (1,100):
        rnd_driver = randint (1,5000)
        rnd_location = randint (0,9)
        rnd_radius =randint (0,8)
        rnd_long = randint (-rnd_radius,rnd_radius)
        rnd_lat  = randint (-rnd_radius,rnd_radius)
        longitude =  Decimal (Locations[rnd_location][0]) + (Decimal (rnd_long) / Decimal (300))
        latitude = Decimal (Locations[rnd_location][1])  + (Decimal (rnd_lat) / Decimal (300))
        
        #context.logger.info('driver id - '+ str(rnd_driver))

        # Build request json
        request_json["RecordType"] = "driver"
        request_json["ID"] = rnd_driver
        request_json["longitude"] = str (longitude)
        request_json["latitude"] = str (latitude)
        
        payload = json.dumps(request_json)

        # send request to ingest functiom
        res = s.put(INGEST_URL, data=payload)
        
        #context.logger.info(request_json)
        #context.logger.info(res)

   # generate random location for passengers and send for ingestion
    for x in range (1,100):
        rnd_driver = randint (1,5000)
        rnd_location = randint (0,9)
        rnd_radius =randint (0,8)
        rnd_long = randint (-rnd_radius,rnd_radius)
        rnd_lat  = randint (-rnd_radius,rnd_radius)
        longitude =  Decimal (Locations[rnd_location][0]) + (Decimal (rnd_long) / Decimal (300))
        latitude = Decimal (Locations[rnd_location][1])  + (Decimal (rnd_lat) / Decimal (300))
        
        #context.logger.info('passenger id - '+ str(rnd_driver))

        # Build request json
        request_json["RecordType"] = "passenger"
        request_json["ID"] = rnd_driver
        request_json["longitude"] = str (longitude)
        request_json["latitude"] = str (latitude)
        
        payload = json.dumps(request_json)

        # send request to ingest functiom
        res = s.put(INGEST_URL, data=payload)
        
        
        #context.logger.info(request_json)
        #context.logger.info(res)

    context.logger.info('End - Generating Data')

    return context.Response(body='Ingestion of drivers and passengers completed successfully',
                            headers={},
                            content_type='text/plain',
                            status_code=200)


