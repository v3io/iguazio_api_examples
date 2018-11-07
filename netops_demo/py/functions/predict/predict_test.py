import unittest.mock
import os
import json
import math

import libs.nuclio_sdk.test
import functions.predict.predict
import libs.utils.utils


class TestCase(libs.nuclio_sdk.test.TestCase):

    def setUp(self):
        super().setUp()
        self._module = functions.predict.predict
        self._utils = libs.utils.utils

    def test_configure(self):
        configuration = self._get_configuration()

        # call configure - should initialize 'deployment' and 'configuration
        response = self._platform.call_handler(self._module.predict,
                                               event=libs.nuclio_sdk.Event(path='/configure', body=configuration))

        self.assertIsNone(response)

        # make sure 'configuration' was set properly, as was metrics
        self.assertIsNotNone(self._platform.get_context(self._module.predict).user_data.metrics)
        self.assertEqual(configuration, self._platform.get_context(self._module.predict).user_data.configuration)

        # make sure 'state' is now 'predicting'
        self.assertEqual('predicting', self._platform.get_context(self._module.predict).user_data.state)

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
        configuration = self._get_configuration()

        # encode configuration into environment variable
        os.environ['PREDICTOR_CONFIGURATION'] = json.dumps(configuration)

        # create an empty context
        context = libs.nuclio_sdk.Context(self._platform._logger, self._platform)

        # initialize context
        self._module.init_context(context)

        # verify stuff was set
        self.assertEqual(context.user_data.state, 'predicting')
        self.assertEqual(context.user_data.configuration, configuration)

    def test_start_and_stop(self):

        # call start
        response = self._platform.call_handler(self._module.predict, event=libs.nuclio_sdk.Event(path='/start'))
        self.assertIsNone(response)

        self.assertEqual(self._platform.get_context(self._module.predict).user_data.state, 'predicting')

        # call stop
        response = self._platform.call_handler(self._module.predict, event=libs.nuclio_sdk.Event(path='/stop'))
        self.assertIsNone(response)

        self.assertEqual(self._platform.get_context(self._module.predict).user_data.state, 'idle')

    def _get_configuration(self):
        return {
            'metrics': ['cpu_utilization', 'throughput'],
            'tsdb': 'http://192.168.224.49:9090',
            'state': 'predicting',
            'target': 'function:netops-demo-ingest'
        }
