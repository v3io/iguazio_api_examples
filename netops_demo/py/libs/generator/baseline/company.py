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
from faker import Faker
from libs.generator.baseline.location import LocationProvider
from libs.generator.device import Device


class Company:
    '''
    Creates a company with locations
    '''

    def __init__(self, num_devices: int, num_locations: int, within: dict, metrics: dict, error_scenarios: [],
                 error_rate: float):
        # Init
        self.f = Faker('en_US')
        self.f.add_provider(LocationProvider)

        # Set parameters
        self.name = self.f.company()
        self.locations = [self.f.location(within) for i in range(num_locations)]
        self.devices = [Device(metrics=metrics,
                               error_scenarios=error_scenarios,
                               error_rate=error_rate) for i in range(num_devices)]
