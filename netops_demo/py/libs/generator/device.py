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
from libs.generator.metric import Metric
from random import Random


class Device:

    def __init__(self, metrics: dict, error_scenarios: [], error_rate: float):
        '''
            Component Manager:
            Receives configuration dictionary and -
                - Creates metrics
                - Runs scenarios
        :param metrics: Configuration dictionary
        '''
        self.metrics = [Metric(name=metric,
                               mu=metrics[metric]['metric']['mu'],
                               sigma=metrics[metric]['metric']['sigma'],
                               noise=metrics[metric]['metric']['noise'],
                               max=metrics[metric]['metric']['max'],
                               min=metrics[metric]['metric']['min'],
                               threshold_alerts_dict=metrics[metric]['alerts']) for metric in metrics.keys()]

        self.error_rate = error_rate
        self.error_scenarios = error_scenarios

        self.is_error = False
        self.steps = 0
        self.error_length = -1
        self.scenario = []

        self.r = Random()
        self.r.seed(42)

    def select_error(self):
        '''
            Chooses randomly an error scenario from
            the given scenarios
        :return: an error scenario dict
        '''
        return self.r.choice(self.error_scenarios)

    def notify_metric_of_error(self):
        [component.start_error(self.error_length-self.steps) for component in self.metrics
         if self.steps == self.scenario[component.name]]

    def notify_metrics_of_normalization(self):
        [component.stop_error() for component in self.metrics]

    def generate(self):
        # Initialize state

        # Main generator loop
        while True:
            # Check if we are in an error state (Prev or New)
            self.is_error = True if (
                    (self.is_error is False) and self.r.uniform(0, 1) <= self.error_rate) else self.is_error

            # If we are in error
            if self.is_error:

                # If this is the first error step
                if self.steps == 0:
                    # Initialize error
                    self.scenario = self.select_error()
                    self.error_length = int(
                        self.r.gauss(mu=self.scenario['length'], sigma=0.1 * self.scenario['length']))

                    # Do we need to notify a metric to start an error state?
                    self.notify_metric_of_error()

                    # Advance steps
                    self.steps += 1

                # If we are already in an error state, do we need to stop?
                elif self.steps == self.error_length:
                    # Change internal state
                    self.is_error = False
                    self.steps = 0
                    # Notify metrics
                    self.notify_metrics_of_normalization()

                # Normal in-error step
                else:
                    self.notify_metric_of_error()
                    self.steps += 1

            # If we are not in an error state
            # else:
            yield {component.name: next(component.get_metric()) for component in self.metrics}
