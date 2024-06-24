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
                for l, location in enumerate(company.components.values()):
                    tick[company.name][l] = {
                        'location': location['location'],
                        'devices': {}
                    }
                    for d, device in enumerate(location['devices']):
                        tick[company.name][l]['devices'][d] = next(device.generate())

            yield tick
