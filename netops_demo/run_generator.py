from generator.manager import Manager

if __name__ == '__main__':

    configuration = {
        'CPU Utilization': {
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
        'Throughput (MB/s)': {
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
                'type': -1
            }
        },
        'Packet loss': {
            'metric': {
                'mu': 1.5,
                'sigma': 0.01,
                'noise': 0.3,
                'max': 3,
                'min': 0
            },
            'alerts': {
                'threshold': 2,
                'alert': 'High Packet Loss (StatReplace) above threshold (2.0)'
            }
        },
        'Latency': {
            'metric': {
                'mu': 5,
                'sigma': 1,
                'noise': 0.4,
                'max': 10,
                'min': 0.1
            },
            'alerts': {
                'threshold': 7,
                'alert': 'High Latency (StatReplace) above threshold (7.0)'
            }
        },
    }

    error_scenarios = [{
        'CPU Utilization': 0,
        'Latency': 10,
        'Packet loss': 20,
        'Throughput (MB/s)': 30,
        'length': 80
    }, {
        'CPU Utilization': 30,
        'Latency': 10,
        'Packet loss': 20,
        'Throughput (MB/s)': 0,
        'length': 80
    }, {
        'CPU Utilization': 0,
        'Latency': 0,
        'Packet loss': 20,
        'Throughput (MB/s)': 20,
        'length': 50
    }]

    errors = [

    ]

    error_rate = 0.01

    metrics = Manager(metrics=configuration,
                      error_scenarios=error_scenarios,
                      error_rate=error_rate)

    for i in range(1000):
        print(next(metrics.generate()))
