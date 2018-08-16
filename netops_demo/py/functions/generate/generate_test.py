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

        # encode configuration into environment variable
        os.environ['GENERATOR_CONFIGURATION'] = json.dumps(self._get_sample_configuration())

        # call start
        response = self._platform.call_handler(self._module.generate, event=libs.nuclio_sdk.Event(path='/sites'))
        print(response)

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
