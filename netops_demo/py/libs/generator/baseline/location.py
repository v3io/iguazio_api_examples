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