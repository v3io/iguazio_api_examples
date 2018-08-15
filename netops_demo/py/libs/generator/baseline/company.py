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
