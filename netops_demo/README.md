# NetOps demo

This demo generates network data and detects, predicts and visualizes anomalies. It is composed of:
1. An Iguazio system
2. Nuclio
3. Nuclio functions that generate and ingest historical and real-time metric samples into the Iguazio TSDB and Anodot
4. Grafana for visualization of metrics

Setting up an Iguazio system including Grafana and Nuclio is out of the scope of this document. 

## Deploying and running the demo

### With helm on Kubernetes
TODO: describe how to deploy the demo using helm.

### With nuctl on local Docker
> Note: Pass `--verbose` if you'd like to see what goes behind the scenes of these commands, or if you are running into problems

Prerequisites:
* `nuctl`
* `httpie`

Start by creating a `netops` project:
```sh
nuctl create project netops \
	--display-name 'NetOps demo' \
	--platform local
```

Deploy the functions, substituting the following:
* NETOPS_CONTAINER_URL: The Iguazio container URL (e.g. `http://10.0.0.1:8081/bigdata`)
* NETOPS_CONTAINER_USERNAME: The Iguazio container username
* NETOPS_CONTAINER_PASSWORD: The Iguazio container password
* NETOPS_TSDB_TABLE_NAME: The name of the table to which we will ingest metrics (e.g. `mytsdb`). If this is not set, no ingestion to TSDB occurs
* NETOPS_ANODOT_TOKEN: The Anodot API token. If this is not set, no ingestion to Anodot occurs

```sh
nuctl deploy \
  --run-image iguaziodocker/netops-demo-golang:0.0.1 \
  --runtime golang \
  --handler main:Ingest \
  --project-name netops \
  --readiness-timeout 10 \
  --data-bindings '{"db0": {"class": "v3io", "url": "$(NETOPS_CONTAINER_URL)", "secret": "NETOPS_CONTAINER_USERNAME:NETOPS_CONTAINER_PASSWORD"}}' \
  --env INGEST_V3IO_TSDB_PATH=NETOPS_TSDB_TABLE_NAME \
  --platform local \
  netops-demo-ingest

nuctl deploy --run-image iguaziodocker/netops-demo-py:0.0.1 \
	--runtime python:3.6 \
	--handler functions.generate.generate:generate \
	--readiness-timeout 10 \
	--triggers '{"periodic": {"kind": "cron", "workerAllocatorName": "defaultHTTPWorkerAllocator", "attributes": {"interval": "1s"}}}' \
	--platform local \
	netops-demo-generate
```

You can choose to follow the logs by running `docker logs -f default-<function name>`, for example:
```sh
docker logs -f default-netops-demo-ingest
```

By default, the generate function is idling - waiting for configuration. Let's configure it by POSTing the following configuration to `/configure`:
```
echo '{
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
  "errors": [],
  "error_rate": 0.001,
  "interval": 1,
  "target": "function:netops-demo-ingest",
  "max_samples_per_batch": 720
}
' | http localhost:<function port>/configure
```

We can now start the generation, indicating that we want to prime the time series databases with 1 day worth of historical data:

```sh
echo '{"num_historical_seconds": 86400}' | http localhost:<function port>/start
```

## Building the demo

Clone this repository and cd into the netops directory:
```sh
TODO
```

### Building the function images
Modify the source code and build the images:
```sh
make
```

This will output `netops-golang:latest` and `netops-py:latest` using Nuclio's ability to [build function images from Dockerfiles](https://github.com/nuclio/nuclio/blob/master/docs/tasks/deploy-functions-from-dockerfile.md). 
> The `golang` image contains the `ingest` and `query` functions. The `py` image contains the `generate` and `train` functions. By bunching together a few functions inside a single image we allow for easily sharing code without worrying about versioning, reducing the number of moving parts, etc. 

Push the images to your favorite Docker registry and deploy using one of the methods above