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
      "labels": {
        "ver": 1,
        "unit": "percent",
        "target_type": "gauge"
      },
      "metric": {
        "mu": 75,
        "sigma": 4,
        "noise": 1,
        "max": 100,
        "min": 0
      },
      "alerts": {
        "threshold": 80,
        "alert": "Operation - Chassis CPU Utilization (StatReplace) exceed Critical threshold (80.0)"
      }
    },
    "throughput": {
      "labels": {
        "ver": 1,
        "unit": "mbyte_sec",
        "target_type": "gauge"
      },
      "metric": {
        "mu": 200,
        "sigma": 50,
        "noise": 50,
        "max": 300,
        "min": 0
      },
      "alerts": {
        "threshold": 30,
        "alert": "Low Throughput (StatReplace) below threshold (3.0)",
        "type": false
      }
    },
    "packet_loss": {
      "labels": {
        "ver": 1,
        "unit": "num_packets",
        "target_type": "counter"
      },
      "metric": {
        "mu": 1.5,
        "sigma": 0.01,
        "noise": 0.3,
        "max": 3,
        "min": 0
      },
      "alerts": {
        "threshold": 2,
        "alert": "High Packet Loss (StatReplace) above threshold (2.0)"
      }
    },
    "latency": {
      "labels": {
        "ver": 1,
        "unit": "microseconds",
        "target_type": "gauge"
      },
      "metric": {
        "mu": 5,
        "sigma": 1,
        "noise": 0.4,
        "max": 10,
        "min": 0.1
      },
      "alerts": {
        "threshold": 7,
        "alert": "High Latency (StatReplace) above threshold (7.0)"
      }
    }
  },
  "error_scenarios": [
    {
      "cpu_utilization": 0,
      "latency": 10,
      "packet_loss": 20,
      "throughput": 30,
      "length": 80
    },
    {
      "cpu_utilization": 30,
      "latency": 10,
      "packet_loss": 20,
      "throughput": 0,
      "length": 80
    },
    {
      "cpu_utilization": 0,
      "latency": 0,
      "packet_loss": 20,
      "throughput": 20,
      "length": 50
    }
  ],
  "errors": [],
	"error_rate": 0.1,
  "samples_per_batch": 1000
}
```

Periodically, invoke with `POST` to `/generate`