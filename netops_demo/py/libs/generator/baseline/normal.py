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