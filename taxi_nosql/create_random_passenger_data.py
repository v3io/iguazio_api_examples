from decimal import *
from random import *

Downtown = [-0.1195,51.5033]

Westminster = [-0.1357,51.4975]

Oxford_St = [-0.1410,51.5154]

Heathrow = [-0.4543,51.4700]

Heathrow_Parking = [-0.4473,51.4599]

Gatwick =  [0.1821,51.1537]

Canary_Wharf = [-0.0235,51.5054]

Wembly = [-0.2795,51.5560]

Locations = [Wembly,Wembly,Canary_Wharf,Canary_Wharf,Downtown,Westminster,Heathrow_Parking,Heathrow,Heathrow_Parking,Heathrow_Parking,Heathrow_Parking,Gatwick]

print ('Driver,Timestamp,Longitude,Latitude')
for x in range (1,1200):
	rnd_location = randint (0,11)
	rnd_long = randint (-10,10)
	rnd_lat  = randint (-10,10)
	long =  Decimal (Locations[rnd_location][0]) + (Decimal (rnd_long) / Decimal (300))
	lat = Decimal (Locations[rnd_location][1])  + (Decimal (rnd_lat) / Decimal (300))
	print ("%d,2017-12-05 09:00:00.050000000,%f,%f"  %(x,long,lat))
