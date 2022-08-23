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
import numpy as np

def Normal(mu=0, sigma=0.5, noise=0):
    '''
    The function used to create the actual device performance data

    :param mu: Mean of the normal distribution to draw the metric from
    :param sigma: Deviation from the mean of the distribution
    :param noise: Sigma for the noise, (Drawn from distribution of Normal(0, noise)
    :return: Metric
    '''
    # while True:
    if noise is not 0:
        added_noise = np.random.normal(loc=0, scale=noise, size=1)
    tick = np.random.normal(loc=mu, scale=sigma, size=1) + added_noise
    return tick