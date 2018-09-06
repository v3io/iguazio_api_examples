## Build functions
```sh
make py
```

Will output the `netops-py:latest` image. 

## Generator

```sh
nuctl deploy --run-image netops-py:latest \
	--runtime python:3.6 \
	--handler functions.generator.generator:handler \
	--platform local \
	--verbose \
	--readiness-timeout 5 \
	netops-generator
```

### Invoking the generator

`POST` to `/start` with `application/json` and the following body:
```
{
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
        "type": true
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
  "deployment": {
        "companies": 5,
        "locations": 3,
        "devices": 5,
        "locations_list": {
            "nw": "(51.520249, -0.071591)",
            "se": "(51.490988, -0.188702)"
        }
    },
  "errors": [],
  "error_rate": 0.001,
  "interval": 1,
  "target": "response",
  "max_samples_per_batch": 100
}
```

Periodically, invoke with `POST` to `/generate`