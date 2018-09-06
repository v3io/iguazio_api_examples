## Build functions
```sh
make golang
```

Will output the `netops-golang:latest` image. 

## Running unit tests
Get dependencies that can't be vendored (set `GOPATH` to `golang` first):
```sh
go get github.com/nuclio/nuclio-sdk-go github.com/nuclio/logger github.com/v3io/v3io-go-http
```

## Ingest

Now simply run the unit test for the applicable function via your favorite IDE / shell.

### Manually deploying to (local) Nuclio
```sh
nuctl deploy \
  --run-image netops-golang:latest \
  --runtime golang \
  --handler main:Ingest \
  --platform local \
  --verbose \
  --readiness-timeout 5 \
  --data-bindings '{"db0": {"class": "v3io", "url": "http://<appnode IP address>:8081/1024", "secret": "<user>:<password>"}}' \
  --env V3IO_TSDB_PATH=mytsdb \
  netops-ingest
```

### Invoking ingest

`POST` to `/` with `application/json` and the following body:
```
[
    [
        {
            "cpu_utilization": {
                "labels": {
                    "latitude": 51.50023102202496,
                    "longtitude": -0.10965841495815892,
                    "name": "Marsh, Douglas and Thompson",
                    "location": "Marsh, Douglas and Thompson/0",
                    "ver": 1,
                    "unit": "percent",
                    "target_type": "gauge"
                },
                "timestamps": [
                    1534165799
                ],
                "values": [
                    77.93779713418735
                ],
                "alerts": [
                    ""
                ],
                "is_error": [
                    0
                ]
            },
            "throughput": {
                "labels": {
                    "latitude": 51.50023102202496,
                    "longtitude": -0.10965841495815892,
                    "name": "Marsh, Douglas and Thompson",
                    "location": "Marsh, Douglas and Thompson/0",
                    "ver": 1,
                    "unit": "mbyte_sec",
                    "target_type": "gauge"
                },
                "timestamps": [
                    1534165799
                ],
                "values": [
                    109.31347105036815
                ],
                "alerts": [
                    "Low Throughput (109.31347105036815) below threshold (3.0)"
                ],
                "is_error": [
                    0
                ]
            }
        },
        {
            "cpu_utilization": {
                "labels": {
                    "latitude": 51.50023102202496,
                    "longtitude": -0.10965841495815892,
                    "name": "Marsh, Douglas and Thompson",
                    "location": "Marsh, Douglas and Thompson/0",
                    "ver": 1,
                    "unit": "percent",
                    "target_type": "gauge"
                },
                "timestamps": [
                    1534165799
                ],
                "values": [
                    76.02721120257534
                ],
                "alerts": [
                    ""
                ],
                "is_error": [
                    0
                ]
            },
            "throughput": {
                "labels": {
                    "latitude": 51.50023102202496,
                    "longtitude": -0.10965841495815892,
                    "name": "Marsh, Douglas and Thompson",
                    "location": "Marsh, Douglas and Thompson/0",
                    "ver": 1,
                    "unit": "mbyte_sec",
                    "target_type": "gauge"
                },
                "timestamps": [
                    1534165799
                ],
                "values": [
                    247.43390221992854
                ],
                "alerts": [
                    "Low Throughput (247.43390221992854) below threshold (3.0)"
                ],
                "is_error": [
                    0
                ]
            }
        }
    ]
]
```

## Query

### Manually deploying to (local) Nuclio
```sh
nuctl deploy \
  --run-image netops-golang:latest \
  --runtime golang \
  --handler main:Query \
  --platform local \
  --verbose \
  --readiness-timeout 5 \
  netops-query
```
