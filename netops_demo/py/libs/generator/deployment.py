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
from libs.generator.baseline.company import Company


class Deployment:

    def __init__(self, configuration: dict):
        '''

        :param locations:
        :param companies:
        :param metrics:
        :param error_scenarios:
        :param error_rate:
        '''

        # Init
        deployment_configuration = configuration['deployment']
        self.configuration = configuration

        self.companies = [Company(num_devices=deployment_configuration['num_devices_per_site'],
                             num_locations=deployment_configuration['num_sites_per_company'],
                             within=deployment_configuration['site_locations_bounding_box'],
                             metrics=configuration['metrics'],
                             error_scenarios=configuration['error_scenarios'],
                             error_rate=configuration['error_rate']) for _ in
                     range(deployment_configuration['num_companies'])]

    def generate(self):

        while True:
            tick = {}

            for company in self.companies:
                tick[company.name] = {}
                for i, l in enumerate(company.locations):
                    tick[company.name][i] = {
                        'location': l,
                        'devices': {}
                    }
                    for j, d in enumerate(company.devices):
                        tick[company.name][i]['devices'][j] = next(d.generate())

            yield tick
