#from generator.manager import Manager
import libs.generator.deployment
import json
import csv
from datetime import datetime, timedelta

def unix_time_millis(date_time):
    epoch = datetime.utcfromtimestamp(0)
    return int((date_time - epoch).total_seconds() * 1000.0)

if __name__ == '__main__':

    configuration2 = {
        "interval": 1,
        "target": "function:netops - demo - ingest",
        "max_samples_per_batch": 720,
        "metrics": {
            "cpu_utilization": {
                "labels": {"ver": 1, "unit": "percent", "target_type": "gauge"},
                "metric": {"mu": 75, "sigma": 4, "noise": 1, "max": 100, "min": 0},
                "alerts": {
                    "threshold": 80,
                    "alert": "Operation - Chassis CPU Utilization (StatReplace) exceed Critical threshold (80.0)"
                }
            },
            "throughput": {
                "labels": {"ver": 1, "unit": "mbyte_sec", "target_type": "gauge"},
                "metric": {"mu": 200, "sigma": 50, "noise": 50, "max": 300, "min": 0},
                "alerts": {
                    "threshold": 30,
                    "alert": "Low Throughput (StatReplace) below threshold (3.0)",
                    "type": True
                }
            }
        },
        "error_scenarios": [
            {
                "cpu_utilization": 0,
                "throughput": 30,
                "length": 80
            }
        ],
        "errors": [],
        "error_rate": 0.001,
        "deployment": {
            "num_companies": 3,
            "num_sites_per_company": 5,
            "num_devices_per_site": 10,
            "site_locations_bounding_box": {
                "nw": "(51.520249, -0.071591)",
                "se": "(51.490988, -0.188702)"
            }
        }
    }

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

    deployment = libs.generator.deployment.Deployment(configuration=configuration2)

    #metrics = Deployment(metrics=configuration,
    #                  error_scenarios=error_scenarios,
    #                  error_rate=error_rate)

    days_start = 10
    timestamp = datetime.utcnow() - timedelta(days=days_start)
    with open("C:\\Users\\ronenf\\Downloads\\netops_metrics.csv", 'w', newline='') as csvfile:
        #f = csv.writer(csvfile, delimiter=',',quotechar='"', quoting=csv.QUOTE_MINIMAL)
        f = csv.writer(csvfile, delimiter=',', quotechar='"')
    #f = csv.writer(open("C:\\Users\\ronenf\\Downloads\\test.csv", "w", newline=''))
        f.writerow(['company', 'location', 'lat', 'lon', 'device', 'metric', 'value', 'alert', 'is_error', 'timestamp'])

        for i in range(50000):
            #print(next(deployment.generate()))
            dep = next(deployment.generate())
            #print(dep)
            timestamp += timedelta(milliseconds=1 * 100)
            for company, locations in dep.items():
                for location,details in locations.items():
                    lat = details["location"][0]
                    lon = details["location"][1]
                    for device, metrics in details["devices"].items():
                        for metric, values in metrics.items():
                            val = values["value"]
                            alert = values["alert"]
                            is_error = values["is_error"]
                            #print(company,",",location,",",lat,",",lon,",",device,",",metric,",",val,",",alert,",",is_error)
                            f.writerow([company,location,lat,lon,device,metric,val,alert,is_error,unix_time_millis(timestamp)])
                            #timestamp += timedelta(milliseconds=1 * 100)