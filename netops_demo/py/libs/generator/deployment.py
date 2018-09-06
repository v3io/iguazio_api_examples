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

        self.companies = [Company(num_devices=deployment_configuration['devices'],
                             num_locations=deployment_configuration['locations'],
                             within=deployment_configuration['locations_list'],
                             metrics=configuration['metrics'],
                             error_scenarios=configuration['error_scenarios'],
                             error_rate=configuration['error_rate']) for _ in
                     range(deployment_configuration['companies'])]

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
