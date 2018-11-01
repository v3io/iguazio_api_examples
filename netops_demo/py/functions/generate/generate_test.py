import unittest.mock
import os
import json
import math

import libs.nuclio_sdk.test
import functions.generate.generate


class TestCase(libs.nuclio_sdk.test.TestCase):

    def setUp(self):
        super().setUp()
        self._module = functions.generate.generate

    def test_configure(self):
        configuration = {
            'metrics': {},
            'error_scenarios': {},
            'deployment': {
                'num_companies': 0,
                'num_sites_per_company': 0,
                'num_devices_per_site': 0
            },
            'error_rate': 0,
            'state': 'generating'
        }

        # call configure - should initialize 'deployment' and 'configuration
        response = self._platform.call_handler(self._module.generate,
                                               event=libs.nuclio_sdk.Event(path='/configure', body=configuration))

        self.assertIsNone(response)

        # make sure 'configuration' was set properly, as was deployment
        self.assertIsNotNone(self._platform.get_context(self._module.generate).user_data.deployment)
        self.assertEqual(configuration, self._platform.get_context(self._module.generate).user_data.configuration)

        # make sure 'state' is now 'generating'
        self.assertEqual('generating', self._platform.get_context(self._module.generate).user_data.state)

    def test_init_context_no_configuration(self):

        # create an empty context
        context = libs.nuclio_sdk.Context(self._platform._logger, self._platform)

        # initialize context
        self._module.init_context(context)

        # expect state to be idle
        self.assertEqual(context.user_data.state, 'idle')

        # expect no configuration set
        self.assertEqual(context.user_data.configuration, None)

    def test_init_context_with_configuration(self):
        configuration = {
            'metrics': {},
            'deployment': {
                'num_companies': 0,
                'num_sites_per_company': 0,
                'num_devices_per_site': 0
            },
            'error_scenarios': {},
            'error_rate': 0,
            'state': 'generating',
            'fixture': {
                'start_timestamp': 100000,
                'end_timestamp': 1000000,
                'interval': 1,
                'max_samples_per_metric': 1000
            }
        }

        # encode configuration into environment variable
        os.environ['GENERATOR_CONFIGURATION'] = json.dumps(configuration)

        # create an empty context
        context = libs.nuclio_sdk.Context(self._platform._logger, self._platform)

        # initialize context
        self._module.init_context(context)

        # verify stuff was set
        self.assertEqual(context.user_data.state, 'generating')
        self.assertEqual(context.user_data.configuration, configuration)

    def test_start_and_stop(self):

        # call start
        response = self._platform.call_handler(self._module.generate, event=libs.nuclio_sdk.Event(path='/start'))
        self.assertIsNone(response)

        self.assertEqual(self._platform.get_context(self._module.generate).user_data.state, 'generating')

        # call stop
        response = self._platform.call_handler(self._module.generate, event=libs.nuclio_sdk.Event(path='/stop'))
        self.assertIsNone(response)

        self.assertEqual(self._platform.get_context(self._module.generate).user_data.state, 'idle')

    def test_send_emitters_to_target(self):
        context = libs.nuclio_sdk.Context(self._platform._logger, self._platform)
        metrics_batch = {'some': 'metrics'}

        with self.assertRaises(ValueError):
            self._module._send_emitters_to_target(context, 'unknown', metrics_batch)

        response = self._module._send_emitters_to_target(context, 'response', metrics_batch)
        self.assertEqual(response, metrics_batch)

        self._module._send_emitters_to_target(context, 'function:some-function', metrics_batch)

        # verify some-function was called
        name, sent_event = self._platform.get_call_function_call_args(0)
        self.assertEqual(name, 'some-function')
        self.assertEqual(sent_event.body, metrics_batch)

    def test_generate_single_batch(self):
        configuration = self._get_sample_configuration()

        # encode configuration into environment variable
        os.environ['GENERATOR_CONFIGURATION'] = json.dumps(configuration)

        request_body = {
            'start_timestamp': 1000,
            'end_timestamp': 1200,
            'interval': 10,
        }

        # call generate (init context will initialize the configuration from env)
        response = self._platform.call_handler(self._module.generate,
                                               event=libs.nuclio_sdk.Event(path='/generate',
                                                                           body=request_body))

        deployment = configuration['deployment']

        # make sure there's one batch
        self.assertEqual(1, len(response))
        emitters = response[0]

        # make sure there are the expected # of emitters
        self.assertEqual(len(emitters), deployment['num_companies'] *
                         deployment['num_sites_per_company'] *
                         deployment['num_devices_per_site'])

        # test emitter
        for metric_name in configuration['metrics'].keys():

            # iterate over all emitters (devices in this case)
            for emitter_name, emitter_info in emitters.items():
                metric = emitter_info['metrics'][metric_name]

                # verify all configuration labels have been kept in tact
                for label in configuration['metrics'][metric_name]['labels'].keys():
                    self.assertEqual(metric['labels'][label], configuration['metrics'][metric_name]['labels'][label])

                # verify number of samples
                expected_num_samples = (request_body['end_timestamp'] - request_body['start_timestamp']) / request_body[
                    'interval']

                for field_name in ['timestamps', 'values', 'alerts', 'is_error']:
                    self.assertEqual(expected_num_samples, len(metric[field_name]))

                # verify correct timestamps
                self.assertEqual(metric['timestamps'][0], request_body['start_timestamp'])
                self.assertEqual(metric['timestamps'][-1], request_body['end_timestamp'] - request_body['interval'])

    def test_predict(self):
        configuration = self._get_sample_configuration()

        # encode configuration into environment variable
        os.environ['GENERATOR_CONFIGURATION'] = json.dumps(configuration)

        # call start
        response = self._platform.call_handler(self._module.generate, event=libs.nuclio_sdk.Event(path='/predict'))
        self.assertEqual(response, '')



    def test_generate_multi_batch(self):
        configuration = self._get_sample_configuration()

        # encode configuration into environment variable
        os.environ['GENERATOR_CONFIGURATION'] = json.dumps(configuration)

        start_timestamp = 1000
        end_timestamp = 9500
        interval = 1
        max_samples_per_metric = 1000

        request_body = {
            'start_timestamp': start_timestamp,
            'end_timestamp': end_timestamp,
            'interval': interval,
            'max_samples_per_metric': max_samples_per_metric
        }

        # patch _generate_batch so that we can see how _generate called it
        with unittest.mock.patch('functions.generate.generate._generate_emitters'):

            # call generate (init context will initialize the configuration from env)
            response = self._platform.call_handler(self._module.generate,
                                                   event=libs.nuclio_sdk.Event(path='/generate',
                                                                               body=request_body))

            # calculate some stuff
            total_num_samples = (end_timestamp - start_timestamp) / interval
            expected_call_count = math.ceil(total_num_samples / max_samples_per_metric)

            # assert # of times generate batch was called
            self.assertEqual(functions.generate.generate._generate_emitters.call_count, expected_call_count)

            # assert the arguments that were passed to it
            for call_index, call_args in enumerate(functions.generate.generate._generate_emitters.call_args_list):
                _, called_start_timestamp, called_num_samples, called_interval = call_args[0]

                # assert start timestamp increments correctly each batch
                self.assertEqual(called_start_timestamp,
                                 start_timestamp + (call_index * (interval * max_samples_per_metric)))

                # number of samples must be equal to max for everything except last
                if call_index != (functions.generate.generate._generate_emitters.call_count - 1):
                    self.assertEqual(called_num_samples, max_samples_per_metric)
                else:
                    self.assertEqual(called_num_samples, end_timestamp % max_samples_per_metric)

                # interval must always be the same
                self.assertEqual(called_interval, interval)

    def test_sites(self):
        configuration = self._get_sample_configuration()

        # encode configuration into environment variable
        os.environ['GENERATOR_CONFIGURATION'] = json.dumps(configuration)

        # call start
        response = self._platform.call_handler(self._module.generate, event=libs.nuclio_sdk.Event(path='/sites'))
        self.assertEqual(
            configuration['deployment']['num_companies'] * configuration['deployment']['num_sites_per_company'],
            len(response))

    def test_devices(self):
        configuration = self._get_sample_configuration()

        # encode configuration into environment variable
        os.environ['GENERATOR_CONFIGURATION'] = json.dumps(configuration)

        # call start
        response = self._platform.call_handler(self._module.generate, event=libs.nuclio_sdk.Event(path='/devices'))
        self.assertEqual(
            configuration['deployment']['num_companies'] * configuration['deployment']['num_sites_per_company']
            * configuration['deployment']['num_devices_per_site'], len(response))

    @staticmethod
    def _get_sample_configuration():
        return {
            'metrics': {
                'cpu_utilization': {
                    'labels': {
                        'ver': 1,
                        'unit': 'percent',
                        'target_type': 'gauge'
                    },
                    'metric': {
                        'mu': 75,
                        'sigma': 4,
                        'noise': 1,
                        'max': 100,
                        'min': 0
                    },
                    'alerts': {
                        'threshold': 80,
                        'alert': 'Operation - Chassis CPU Utilization (StatReplace) exceed Critical threshold (80.0)'
                    }
                },
                'throughput': {
                    'labels': {
                        'ver': 1,
                        'unit': 'mbyte_sec',
                        'target_type': 'gauge'
                    },
                    'metric': {
                        'mu': 200,
                        'sigma': 50,
                        'noise': 50,
                        'max': 300,
                        'min': 0
                    },
                    'alerts': {
                        'threshold': 30,
                        'alert': 'Low Throughput (StatReplace) below threshold (3.0)',
                        'type': True
                    }
                }
            },
            'error_scenarios': [
                {
                    'cpu_utilization': 0,
                    'throughput': 30,
                    'length': 80
                },
            ],
            'deployment': {
                'num_companies': 5,
                'num_sites_per_company': 3,
                'num_devices_per_site': 5,
                'site_locations_bounding_box': {
                    'nw': '(51.520249, -0.071591)',
                    'se': '(51.490988, -0.188702)'
                }
            },
            'errors': [],
            'error_rate': 0.1,
            'target': 'response',

            'state': 'generating'
        }

    @staticmethod
    def _get_prometheus_throughput_avg_1h():
        return {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/3/1",
                            "latitute": "-0.11766485686257479",
                            "longitude": "51.51241260576661",
                            "site_id": "cook_ramirez_and_howell/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "201.84682698565652"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/3/4",
                            "latitute": "-0.11766485686257479",
                            "longitude": "51.51241260576661",
                            "site_id": "cook_ramirez_and_howell/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "202.02232908643256"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/1/9",
                            "latitute": "-0.17937324059872775",
                            "longitude": "51.49981289880396",
                            "site_id": "cook_ramirez_and_howell/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "195.52091063340944"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/1/8",
                            "latitute": "-0.08845125744353492",
                            "longitude": "51.49395842747566",
                            "site_id": "jackson_gibson/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "196.80557368577473"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/3/8",
                            "latitute": "-0.14477605500681137",
                            "longitude": "51.50950646273536",
                            "site_id": "jackson_gibson/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "197.14578076146293"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/3/9",
                            "latitute": "-0.1684063123676963",
                            "longitude": "51.49890595002585",
                            "site_id": "martinez_inc/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "198.25121288933332"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/0/4",
                            "latitute": "-0.08743943934424686",
                            "longitude": "51.49462424727675",
                            "site_id": "cook_ramirez_and_howell/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "200.3116370269399"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/4/6",
                            "latitute": "-0.11922450970538258",
                            "longitude": "51.495592295069905",
                            "site_id": "cook_ramirez_and_howell/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "201.69564330124905"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/4/9",
                            "latitute": "-0.10358309561844188",
                            "longitude": "51.502997658785624",
                            "site_id": "martinez_inc/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "195.72478779138552"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/1/4",
                            "latitute": "-0.17937324059872775",
                            "longitude": "51.49981289880396",
                            "site_id": "cook_ramirez_and_howell/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "197.80413082951264"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/4/7",
                            "latitute": "-0.10358309561844188",
                            "longitude": "51.502997658785624",
                            "site_id": "martinez_inc/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.3129222253966"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/1/1",
                            "latitute": "-0.18856414865471136",
                            "longitude": "51.50398145727124",
                            "site_id": "martinez_inc/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.29127778426687"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/2/0",
                            "latitute": "-0.12588664262819296",
                            "longitude": "51.50221488435059",
                            "site_id": "cook_ramirez_and_howell/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "201.24457498024685"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/1/8",
                            "latitute": "-0.18856414865471136",
                            "longitude": "51.50398145727124",
                            "site_id": "martinez_inc/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "200.3373581533792"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/4/7",
                            "latitute": "-0.10790649546111267",
                            "longitude": "51.505154712405286",
                            "site_id": "jackson_gibson/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.9646135829882"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/3/7",
                            "latitute": "-0.1684063123676963",
                            "longitude": "51.49890595002585",
                            "site_id": "martinez_inc/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "202.4863893062895"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/4/2",
                            "latitute": "-0.11922450970538258",
                            "longitude": "51.495592295069905",
                            "site_id": "cook_ramirez_and_howell/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "200.05184702490186"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/2/0",
                            "latitute": "-0.11642291673866854",
                            "longitude": "51.51683458013747",
                            "site_id": "martinez_inc/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "195.79330791453125"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/3/0",
                            "latitute": "-0.1684063123676963",
                            "longitude": "51.49890595002585",
                            "site_id": "martinez_inc/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.96811468182636"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/2/3",
                            "latitute": "-0.11642291673866854",
                            "longitude": "51.51683458013747",
                            "site_id": "martinez_inc/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "202.77078565378753"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/0/4",
                            "latitute": "-0.14414594436220526",
                            "longitude": "51.51080694746054",
                            "site_id": "martinez_inc/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "204.43106231216132"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/2/4",
                            "latitute": "-0.12588664262819296",
                            "longitude": "51.50221488435059",
                            "site_id": "cook_ramirez_and_howell/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "198.3928395695168"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/1/6",
                            "latitute": "-0.08845125744353492",
                            "longitude": "51.49395842747566",
                            "site_id": "jackson_gibson/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "201.1124768354935"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/3/7",
                            "latitute": "-0.11766485686257479",
                            "longitude": "51.51241260576661",
                            "site_id": "cook_ramirez_and_howell/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "203.6165793877006"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/2/2",
                            "latitute": "-0.11642291673866854",
                            "longitude": "51.51683458013747",
                            "site_id": "martinez_inc/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "198.57428448308957"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/0/0",
                            "latitute": "-0.14414594436220526",
                            "longitude": "51.51080694746054",
                            "site_id": "martinez_inc/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "198.695688192008"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/1/1",
                            "latitute": "-0.08845125744353492",
                            "longitude": "51.49395842747566",
                            "site_id": "jackson_gibson/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "200.3342129942806"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/2/9",
                            "latitute": "-0.11642291673866854",
                            "longitude": "51.51683458013747",
                            "site_id": "martinez_inc/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.56559180485672"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/4/5",
                            "latitute": "-0.11922450970538258",
                            "longitude": "51.495592295069905",
                            "site_id": "cook_ramirez_and_howell/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "201.16954763272514"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/4/6",
                            "latitute": "-0.10790649546111267",
                            "longitude": "51.505154712405286",
                            "site_id": "jackson_gibson/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "196.71524325915243"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/2/6",
                            "latitute": "-0.12588664262819296",
                            "longitude": "51.50221488435059",
                            "site_id": "cook_ramirez_and_howell/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.28072743830444"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/3/9",
                            "latitute": "-0.11766485686257479",
                            "longitude": "51.51241260576661",
                            "site_id": "cook_ramirez_and_howell/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "200.49862413673156"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/4/1",
                            "latitute": "-0.10358309561844188",
                            "longitude": "51.502997658785624",
                            "site_id": "martinez_inc/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "200.80540298841441"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/3/9",
                            "latitute": "-0.14477605500681137",
                            "longitude": "51.50950646273536",
                            "site_id": "jackson_gibson/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "197.9708384853567"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/1/7",
                            "latitute": "-0.17937324059872775",
                            "longitude": "51.49981289880396",
                            "site_id": "cook_ramirez_and_howell/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "198.3352771171675"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/4/5",
                            "latitute": "-0.10358309561844188",
                            "longitude": "51.502997658785624",
                            "site_id": "martinez_inc/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "198.7710944467823"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/0/9",
                            "latitute": "-0.14414594436220526",
                            "longitude": "51.51080694746054",
                            "site_id": "martinez_inc/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "200.13094249930876"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/0/0",
                            "latitute": "-0.09275684203595459",
                            "longitude": "51.50604392091363",
                            "site_id": "jackson_gibson/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "203.74401774477604"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/3/1",
                            "latitute": "-0.1684063123676963",
                            "longitude": "51.49890595002585",
                            "site_id": "martinez_inc/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "195.06474004803403"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/4/1",
                            "latitute": "-0.11922450970538258",
                            "longitude": "51.495592295069905",
                            "site_id": "cook_ramirez_and_howell/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "197.24436504924168"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/0/7",
                            "latitute": "-0.14414594436220526",
                            "longitude": "51.51080694746054",
                            "site_id": "martinez_inc/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "201.08608593580766"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/2/3",
                            "latitute": "-0.12588664262819296",
                            "longitude": "51.50221488435059",
                            "site_id": "cook_ramirez_and_howell/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "198.7599557286866"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/3/6",
                            "latitute": "-0.1684063123676963",
                            "longitude": "51.49890595002585",
                            "site_id": "martinez_inc/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "204.308557481124"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/4/4",
                            "latitute": "-0.11922450970538258",
                            "longitude": "51.495592295069905",
                            "site_id": "cook_ramirez_and_howell/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "193.0099878859856"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/0/1",
                            "latitute": "-0.14414594436220526",
                            "longitude": "51.51080694746054",
                            "site_id": "martinez_inc/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "201.42345580633963"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/1/8",
                            "latitute": "-0.17937324059872775",
                            "longitude": "51.49981289880396",
                            "site_id": "cook_ramirez_and_howell/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "201.77209237275176"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/3/5",
                            "latitute": "-0.14477605500681137",
                            "longitude": "51.50950646273536",
                            "site_id": "jackson_gibson/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "196.69713104761172"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/0/7",
                            "latitute": "-0.09275684203595459",
                            "longitude": "51.50604392091363",
                            "site_id": "jackson_gibson/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "198.31397445378576"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/1/4",
                            "latitute": "-0.08845125744353492",
                            "longitude": "51.49395842747566",
                            "site_id": "jackson_gibson/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "201.82758047257465"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/1/0",
                            "latitute": "-0.08845125744353492",
                            "longitude": "51.49395842747566",
                            "site_id": "jackson_gibson/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.3491855729556"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/1/0",
                            "latitute": "-0.17937324059872775",
                            "longitude": "51.49981289880396",
                            "site_id": "cook_ramirez_and_howell/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "196.17085785311446"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/4/3",
                            "latitute": "-0.11922450970538258",
                            "longitude": "51.495592295069905",
                            "site_id": "cook_ramirez_and_howell/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "204.88745646047883"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/0/2",
                            "latitute": "-0.09275684203595459",
                            "longitude": "51.50604392091363",
                            "site_id": "jackson_gibson/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "196.3480228927308"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/0/2",
                            "latitute": "-0.14414594436220526",
                            "longitude": "51.51080694746054",
                            "site_id": "martinez_inc/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "202.8579103696573"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/0/5",
                            "latitute": "-0.14414594436220526",
                            "longitude": "51.51080694746054",
                            "site_id": "martinez_inc/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "197.37466218794935"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/4/2",
                            "latitute": "-0.10358309561844188",
                            "longitude": "51.502997658785624",
                            "site_id": "martinez_inc/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "202.51812945931016"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/4/9",
                            "latitute": "-0.10790649546111267",
                            "longitude": "51.505154712405286",
                            "site_id": "jackson_gibson/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "197.95775656198037"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/4/3",
                            "latitute": "-0.10358309561844188",
                            "longitude": "51.502997658785624",
                            "site_id": "martinez_inc/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.29505953777763"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/2/1",
                            "latitute": "-0.12588664262819296",
                            "longitude": "51.50221488435059",
                            "site_id": "cook_ramirez_and_howell/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.72902867003324"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/1/9",
                            "latitute": "-0.18856414865471136",
                            "longitude": "51.50398145727124",
                            "site_id": "martinez_inc/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "196.33084254742477"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/2/3",
                            "latitute": "-0.15706157829077952",
                            "longitude": "51.519939570267255",
                            "site_id": "jackson_gibson/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "198.44927576056375"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/0/9",
                            "latitute": "-0.08743943934424686",
                            "longitude": "51.49462424727675",
                            "site_id": "cook_ramirez_and_howell/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "196.92239718637927"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/4/0",
                            "latitute": "-0.10358309561844188",
                            "longitude": "51.502997658785624",
                            "site_id": "martinez_inc/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "202.71815476920034"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/3/5",
                            "latitute": "-0.11766485686257479",
                            "longitude": "51.51241260576661",
                            "site_id": "cook_ramirez_and_howell/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "201.89862443814354"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/2/5",
                            "latitute": "-0.15706157829077952",
                            "longitude": "51.519939570267255",
                            "site_id": "jackson_gibson/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "198.61435786412522"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/3/2",
                            "latitute": "-0.14477605500681137",
                            "longitude": "51.50950646273536",
                            "site_id": "jackson_gibson/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "200.13486464613476"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/1/9",
                            "latitute": "-0.08845125744353492",
                            "longitude": "51.49395842747566",
                            "site_id": "jackson_gibson/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "201.80828117073895"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/1/6",
                            "latitute": "-0.17937324059872775",
                            "longitude": "51.49981289880396",
                            "site_id": "cook_ramirez_and_howell/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "203.5009752841243"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/2/0",
                            "latitute": "-0.15706157829077952",
                            "longitude": "51.519939570267255",
                            "site_id": "jackson_gibson/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "201.03865831051542"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/3/8",
                            "latitute": "-0.11766485686257479",
                            "longitude": "51.51241260576661",
                            "site_id": "cook_ramirez_and_howell/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "202.40276494043889"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/4/0",
                            "latitute": "-0.10790649546111267",
                            "longitude": "51.505154712405286",
                            "site_id": "jackson_gibson/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "202.0984346718554"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/0/3",
                            "latitute": "-0.14414594436220526",
                            "longitude": "51.51080694746054",
                            "site_id": "martinez_inc/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "202.57778277641512"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/3/6",
                            "latitute": "-0.14477605500681137",
                            "longitude": "51.50950646273536",
                            "site_id": "jackson_gibson/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "197.86322701166387"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/3/4",
                            "latitute": "-0.14477605500681137",
                            "longitude": "51.50950646273536",
                            "site_id": "jackson_gibson/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "198.87411958933114"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/1/4",
                            "latitute": "-0.18856414865471136",
                            "longitude": "51.50398145727124",
                            "site_id": "martinez_inc/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "205.39193276923314"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/4/8",
                            "latitute": "-0.11922450970538258",
                            "longitude": "51.495592295069905",
                            "site_id": "cook_ramirez_and_howell/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.6762694607545"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/2/7",
                            "latitute": "-0.15706157829077952",
                            "longitude": "51.519939570267255",
                            "site_id": "jackson_gibson/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "197.30960573882373"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/0/3",
                            "latitute": "-0.09275684203595459",
                            "longitude": "51.50604392091363",
                            "site_id": "jackson_gibson/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "201.771092958179"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/0/5",
                            "latitute": "-0.08743943934424686",
                            "longitude": "51.49462424727675",
                            "site_id": "cook_ramirez_and_howell/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.4923922717868"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/2/4",
                            "latitute": "-0.11642291673866854",
                            "longitude": "51.51683458013747",
                            "site_id": "martinez_inc/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "202.5549280217423"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/0/1",
                            "latitute": "-0.08743943934424686",
                            "longitude": "51.49462424727675",
                            "site_id": "cook_ramirez_and_howell/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "202.9675457506287"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/1/3",
                            "latitute": "-0.17937324059872775",
                            "longitude": "51.49981289880396",
                            "site_id": "cook_ramirez_and_howell/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "198.5703293318505"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/1/5",
                            "latitute": "-0.08845125744353492",
                            "longitude": "51.49395842747566",
                            "site_id": "jackson_gibson/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "202.6195506442932"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/0/1",
                            "latitute": "-0.09275684203595459",
                            "longitude": "51.50604392091363",
                            "site_id": "jackson_gibson/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "200.59050851861292"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/0/8",
                            "latitute": "-0.14414594436220526",
                            "longitude": "51.51080694746054",
                            "site_id": "martinez_inc/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "203.5622379069917"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/4/5",
                            "latitute": "-0.10790649546111267",
                            "longitude": "51.505154712405286",
                            "site_id": "jackson_gibson/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "203.81845968239867"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/1/2",
                            "latitute": "-0.17937324059872775",
                            "longitude": "51.49981289880396",
                            "site_id": "cook_ramirez_and_howell/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "198.08604078610432"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/3/5",
                            "latitute": "-0.1684063123676963",
                            "longitude": "51.49890595002585",
                            "site_id": "martinez_inc/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "198.93246514279485"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/1/5",
                            "latitute": "-0.18856414865471136",
                            "longitude": "51.50398145727124",
                            "site_id": "martinez_inc/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "203.5700383167893"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/4/2",
                            "latitute": "-0.10790649546111267",
                            "longitude": "51.505154712405286",
                            "site_id": "jackson_gibson/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.49954891178135"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/2/2",
                            "latitute": "-0.15706157829077952",
                            "longitude": "51.519939570267255",
                            "site_id": "jackson_gibson/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.3125792525744"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/1/7",
                            "latitute": "-0.08845125744353492",
                            "longitude": "51.49395842747566",
                            "site_id": "jackson_gibson/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.63250114277076"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/4/3",
                            "latitute": "-0.10790649546111267",
                            "longitude": "51.505154712405286",
                            "site_id": "jackson_gibson/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "198.72943358456283"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/0/6",
                            "latitute": "-0.08743943934424686",
                            "longitude": "51.49462424727675",
                            "site_id": "cook_ramirez_and_howell/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "200.4231318636992"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/3/1",
                            "latitute": "-0.14477605500681137",
                            "longitude": "51.50950646273536",
                            "site_id": "jackson_gibson/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.31267730947303"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/3/2",
                            "latitute": "-0.1684063123676963",
                            "longitude": "51.49890595002585",
                            "site_id": "martinez_inc/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.54326952138825"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/2/1",
                            "latitute": "-0.15706157829077952",
                            "longitude": "51.519939570267255",
                            "site_id": "jackson_gibson/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "203.4478702901137"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/4/9",
                            "latitute": "-0.11922450970538258",
                            "longitude": "51.495592295069905",
                            "site_id": "cook_ramirez_and_howell/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "193.502798339676"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/1/3",
                            "latitute": "-0.08845125744353492",
                            "longitude": "51.49395842747566",
                            "site_id": "jackson_gibson/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "202.32434207174623"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/4/8",
                            "latitute": "-0.10358309561844188",
                            "longitude": "51.502997658785624",
                            "site_id": "martinez_inc/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "198.5594718612572"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/3/0",
                            "latitute": "-0.14477605500681137",
                            "longitude": "51.50950646273536",
                            "site_id": "jackson_gibson/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "205.06356467643758"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/0/0",
                            "latitute": "-0.08743943934424686",
                            "longitude": "51.49462424727675",
                            "site_id": "cook_ramirez_and_howell/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "204.31049087691707"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/0/5",
                            "latitute": "-0.09275684203595459",
                            "longitude": "51.50604392091363",
                            "site_id": "jackson_gibson/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "197.64496317318378"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/3/4",
                            "latitute": "-0.1684063123676963",
                            "longitude": "51.49890595002585",
                            "site_id": "martinez_inc/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "196.09901479328602"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/4/1",
                            "latitute": "-0.10790649546111267",
                            "longitude": "51.505154712405286",
                            "site_id": "jackson_gibson/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "197.90912683161795"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/2/1",
                            "latitute": "-0.11642291673866854",
                            "longitude": "51.51683458013747",
                            "site_id": "martinez_inc/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "195.20660684721142"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/0/8",
                            "latitute": "-0.09275684203595459",
                            "longitude": "51.50604392091363",
                            "site_id": "jackson_gibson/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "198.81177258795051"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/0/8",
                            "latitute": "-0.08743943934424686",
                            "longitude": "51.49462424727675",
                            "site_id": "cook_ramirez_and_howell/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.26558341667908"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/1/0",
                            "latitute": "-0.18856414865471136",
                            "longitude": "51.50398145727124",
                            "site_id": "martinez_inc/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "202.63322094012966"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/0/2",
                            "latitute": "-0.08743943934424686",
                            "longitude": "51.49462424727675",
                            "site_id": "cook_ramirez_and_howell/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "201.242829647885"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/1/1",
                            "latitute": "-0.17937324059872775",
                            "longitude": "51.49981289880396",
                            "site_id": "cook_ramirez_and_howell/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "203.47636863611046"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/2/8",
                            "latitute": "-0.12588664262819296",
                            "longitude": "51.50221488435059",
                            "site_id": "cook_ramirez_and_howell/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "196.6303931712822"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/4/8",
                            "latitute": "-0.10790649546111267",
                            "longitude": "51.505154712405286",
                            "site_id": "jackson_gibson/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.4025509158343"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/2/5",
                            "latitute": "-0.11642291673866854",
                            "longitude": "51.51683458013747",
                            "site_id": "martinez_inc/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "202.244381888705"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/2/9",
                            "latitute": "-0.15706157829077952",
                            "longitude": "51.519939570267255",
                            "site_id": "jackson_gibson/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "198.75932886475152"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/0/3",
                            "latitute": "-0.08743943934424686",
                            "longitude": "51.49462424727675",
                            "site_id": "cook_ramirez_and_howell/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "197.55541164406517"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/3/8",
                            "latitute": "-0.1684063123676963",
                            "longitude": "51.49890595002585",
                            "site_id": "martinez_inc/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.67193673177024"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/2/6",
                            "latitute": "-0.11642291673866854",
                            "longitude": "51.51683458013747",
                            "site_id": "martinez_inc/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "201.87301396849193"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/0/4",
                            "latitute": "-0.09275684203595459",
                            "longitude": "51.50604392091363",
                            "site_id": "jackson_gibson/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "208.8742227341114"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/4/6",
                            "latitute": "-0.10358309561844188",
                            "longitude": "51.502997658785624",
                            "site_id": "martinez_inc/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "197.7648261012689"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/0/6",
                            "latitute": "-0.14414594436220526",
                            "longitude": "51.51080694746054",
                            "site_id": "martinez_inc/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.9982144628044"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/0/9",
                            "latitute": "-0.09275684203595459",
                            "longitude": "51.50604392091363",
                            "site_id": "jackson_gibson/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "201.46652012853383"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/2/5",
                            "latitute": "-0.12588664262819296",
                            "longitude": "51.50221488435059",
                            "site_id": "cook_ramirez_and_howell/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "200.39455519286264"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/1/7",
                            "latitute": "-0.18856414865471136",
                            "longitude": "51.50398145727124",
                            "site_id": "martinez_inc/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "200.60777016813307"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/2/4",
                            "latitute": "-0.15706157829077952",
                            "longitude": "51.519939570267255",
                            "site_id": "jackson_gibson/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "195.1289531633795"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/1/2",
                            "latitute": "-0.08845125744353492",
                            "longitude": "51.49395842747566",
                            "site_id": "jackson_gibson/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "203.46170393549912"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/2/7",
                            "latitute": "-0.11642291673866854",
                            "longitude": "51.51683458013747",
                            "site_id": "martinez_inc/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "205.7759776027545"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/4/4",
                            "latitute": "-0.10358309561844188",
                            "longitude": "51.502997658785624",
                            "site_id": "martinez_inc/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "202.10716727798894"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/3/3",
                            "latitute": "-0.14477605500681137",
                            "longitude": "51.50950646273536",
                            "site_id": "jackson_gibson/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.58662763687067"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/2/8",
                            "latitute": "-0.11642291673866854",
                            "longitude": "51.51683458013747",
                            "site_id": "martinez_inc/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.73692392059917"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/3/6",
                            "latitute": "-0.11766485686257479",
                            "longitude": "51.51241260576661",
                            "site_id": "cook_ramirez_and_howell/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "197.8058363586146"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/2/6",
                            "latitute": "-0.15706157829077952",
                            "longitude": "51.519939570267255",
                            "site_id": "jackson_gibson/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "201.4959357936072"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/4/4",
                            "latitute": "-0.10790649546111267",
                            "longitude": "51.505154712405286",
                            "site_id": "jackson_gibson/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "201.15200992534773"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/1/3",
                            "latitute": "-0.18856414865471136",
                            "longitude": "51.50398145727124",
                            "site_id": "martinez_inc/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "198.47767020368474"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/3/0",
                            "latitute": "-0.11766485686257479",
                            "longitude": "51.51241260576661",
                            "site_id": "cook_ramirez_and_howell/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "196.8473143781654"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/1/2",
                            "latitute": "-0.18856414865471136",
                            "longitude": "51.50398145727124",
                            "site_id": "martinez_inc/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "203.16443165242134"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/2/2",
                            "latitute": "-0.12588664262819296",
                            "longitude": "51.50221488435059",
                            "site_id": "cook_ramirez_and_howell/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "204.06110122890823"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/4/7",
                            "latitute": "-0.11922450970538258",
                            "longitude": "51.495592295069905",
                            "site_id": "cook_ramirez_and_howell/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "198.0927403914103"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/0/7",
                            "latitute": "-0.08743943934424686",
                            "longitude": "51.49462424727675",
                            "site_id": "cook_ramirez_and_howell/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.8686825637131"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/3/3",
                            "latitute": "-0.1684063123676963",
                            "longitude": "51.49890595002585",
                            "site_id": "martinez_inc/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "200.35823350690367"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/3/7",
                            "latitute": "-0.14477605500681137",
                            "longitude": "51.50950646273536",
                            "site_id": "jackson_gibson/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "200.6086038246571"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/4/0",
                            "latitute": "-0.11922450970538258",
                            "longitude": "51.495592295069905",
                            "site_id": "cook_ramirez_and_howell/4",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "202.84687489498225"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/3/2",
                            "latitute": "-0.11766485686257479",
                            "longitude": "51.51241260576661",
                            "site_id": "cook_ramirez_and_howell/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "196.86890595546433"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/3/3",
                            "latitute": "-0.11766485686257479",
                            "longitude": "51.51241260576661",
                            "site_id": "cook_ramirez_and_howell/3",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.39106984840805"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/1/5",
                            "latitute": "-0.17937324059872775",
                            "longitude": "51.49981289880396",
                            "site_id": "cook_ramirez_and_howell/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "197.42025139765155"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/2/9",
                            "latitute": "-0.12588664262819296",
                            "longitude": "51.50221488435059",
                            "site_id": "cook_ramirez_and_howell/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "202.4647531090913"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/2/8",
                            "latitute": "-0.15706157829077952",
                            "longitude": "51.519939570267255",
                            "site_id": "jackson_gibson/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "199.47985538380314"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "martinez_inc",
                            "device_id": "martinez_inc/1/6",
                            "latitute": "-0.18856414865471136",
                            "longitude": "51.50398145727124",
                            "site_id": "martinez_inc/1",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "203.75229813981974"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "cook_ramirez_and_howell",
                            "device_id": "cook_ramirez_and_howell/2/7",
                            "latitute": "-0.12588664262819296",
                            "longitude": "51.50221488435059",
                            "site_id": "cook_ramirez_and_howell/2",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "201.04338505108396"
                        ]
                    },
                    {
                        "metric": {
                            "company_id": "jackson_gibson",
                            "device_id": "jackson_gibson/0/6",
                            "latitute": "-0.09275684203595459",
                            "longitude": "51.50604392091363",
                            "site_id": "jackson_gibson/0",
                            "target_type": "gauge",
                            "unit": "mbyte_sec",
                            "ver": "1"
                        },
                        "value": [
                            1540456986.897,
                            "197.69736363634297"
                        ]
                    }
                ]
            }
        }
