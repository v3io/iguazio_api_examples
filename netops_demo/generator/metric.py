from generator.baseline.normal import Normal
# from generator.baseline.peak_error import Peak_error
from random import Random


class Metric:

    def __init__(self,
                 name: str,
                 threshold_alerts_dict: dict,
                 mu: float,
                 sigma: float,
                 noise: float,
                 max: float,
                 min: float):
        '''

        :param name: Metric name
        :param threshold_alerts_dict:
            Dictionary of: (Threshold -> Alert)

            Note: StatReplace is the Stub to replace for the current generated metric to the log line
            Example:
                - CPU Utilization metric
                    - Threshold: 80%
                    - Alert: "Operation - Chassis CPU Utilization (StatReplace) exceed Critical threshold (80.0)"
        :param mu: Mean of the metric distribution
        :param sigma: Deviation of the metric distribution
        :param noise: Noise added to the metric distribution (As Normal(mu=0, sigma=noise))
        :return:
        '''

        self.name = name
        self.mu = mu
        self.sigma = sigma
        self.noise = noise
        self.max = max
        self.min = min

        self.alert_threshold = threshold_alerts_dict.get('threshold') if len(threshold_alerts_dict) > 0 else -1
        self.threshold_alerts_dict = threshold_alerts_dict
        self.is_threshold_below = threshold_alerts_dict.get('type') if 'type' in threshold_alerts_dict.keys() else 1

        self.is_error = False
        self.steps = 0
        self.error_length = 80

        self.peaks = 0
        self.error_peak_length = 0
        self.peak_chance = 0
        self.r = Random()
        self.r.seed(42)

        self.generator_metric = Normal
        self.error_metric = self.Peak_error()
        self.current_metric = self.generator_metric

    def Peak_error(self, target_peaks: int = 4, error_peak_ratio: float = 0.5):
        def return_peak():
            return self.max if self.is_threshold_below else self.min

        while True:
            # Are we in Pre-Error?
            if self.steps <= self.error_length - self.error_peak_length:
                # Will it peak?
                is_peak = True if self.r.uniform(0, 1) <= self.peak_chance else False
                yield return_peak() if is_peak else self.generator_metric(mu=self.mu,
                                                                           sigma=self.sigma,
                                                                           noise=self.noise)[0]

            # Are we in Peak-Error?
            else:
                yield return_peak()


    def generator(self):
        '''
            Produces the metric from normal distribution as defined by the user
        :return: One metric sample
        '''
        if self.is_error:
            self.steps += 1
            return next(self.error_metric)
        else:
            return self.generator_metric(mu=self.mu,
                                         sigma=self.sigma,
                                         noise=self.noise)[0]


    def get_alert(self, metric):
        '''
            Checks weather an alert should be made
        :param metric: Current sample
        :return: A Metric Alert if needed
        '''
        return self.threshold_alerts_dict.get('alert').replace('StatReplace', str(
            metric)) if ((self.is_threshold_below == 1 and metric >= self.alert_threshold) or
                         (self.is_threshold_below == -1 and metric <= self.alert_threshold)) and \
                        self.alert_threshold is not -1 else ''


    def validate_value(self, metric):
        '''
            Validates the metric values are within valid range as defined by min / max
        '''
        # Need to switch to by parameters
        metric = metric if metric > self.min else self.min
        metric = metric if metric < self.max else self.max
        return metric


    def start_error(self, error_length: int, target_peaks: int = 4, error_peak_ratio: float = 0.5):
        r = Random()
        r.seed(42)

        # Pick one error scenario
        self.error_length = error_length
        self.is_error = True
        self.error_metric = self.Peak_error()
        self.peaks = int(r.gauss(mu=target_peaks, sigma=0.5 * target_peaks))
        self.error_peak_length = int(
            r.gauss(mu=self.error_length * error_peak_ratio, sigma=self.error_length * 0.1))
        self.peak_chance = self.peaks / (self.error_length - self.error_peak_length)
        return 0


    def stop_error(self):
        # Return generator to Normal
        self.current_metric = self.generator_metric
        self.is_error = False
        self.steps = 0
        self.error_length = 0
        return 0


    def get_metric(self):
        while True:
            metric = self.validate_value(self.generator())
            yield {
                self.name: metric,
                'alert': self.get_alert(metric=metric),
                'is_error': self.is_error
            }
