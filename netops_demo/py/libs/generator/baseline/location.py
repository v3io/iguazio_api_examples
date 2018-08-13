from faker.providers import BaseProvider
from random import Random
from ast import literal_eval as make_tuple

class LocationProvider(BaseProvider):
    '''
    Creates locations for company deployments within given GPS Coordinates rectangle
    '''
    def location(self, within: dict = {}):
        '''

        :param within: GPS rectangle Coordinates containing:
                nw: ()
                se: ()
        :return: GPS Coordinate within the given rectangle
        '''
        nw = make_tuple(within['nw'])
        se = make_tuple(within['se'])

        width = abs(nw[1] - se[1])
        height = abs(nw[0] - se[0])

        r = Random()

        location = (se[0] + r.uniform(0, height), se[1] + r.uniform(0, width))

        return location