# NetOps demo

This demo generates network data and detects, predicts and visualizes anomalies. It is composed of:
1. An Iguazio system
2. Nuclio
3. Nuclio functions that generate and ingest historical and real-time metric samples into the Iguazio TSDB and Anodot
4. Grafana for visualization of metrics

Setting up an Iguazio system including Grafana and Nuclio is out of the scope of this document. 

## Deploying and running the demo

### With helm on Kubernetes
```sh
helm repo add v3io-demo https://v3io.github.io/helm-charts/demo
helm install v3io-demo/netops \
  --set ingest.tsdb.url <webapi url> \
  --set ingest.tsdb.username <webapi username> \
  --set ingest.tsdb.password <webapi password> \
  --set ingest.tsdb.path <tsdb path>
```

> Note: To ingest into Anodot, add `--set ingest.anodot.token <anodot token>` to the above. 

The demo is configured with defaults, as can be found in the values.yaml (#REF). You can download and modify these settings and pass `--values <values-file-path>` rather than the `--set` arguments above. The generator is configured through a Kubernetes configmap, so it comes up configured. All we need to do is start the generation, including a day of historical data:

```sh
echo '{"num_historical_seconds": 86400}' | http ???/start
```

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

## Developing

### Python (Pycharm)
Create a project at `py` and specify a virtualenv under `py/venv`. Install the `requirements.txt` file and simply one of the unit tests with `Unittest` (e.g. py/functions/generate/generate_test.py). This uses a Nuclio SDK Python wrapper.

### Golang (Goland)
Create a project at `golang/src/github.com/v3io/demos` and specify `GOPATH` to be `golang`. Execute `go get` to some packages that cannot be vendored:
```sh
go get github.com/nuclio/logger github.com/nuclio/nuclio-sdk-go github.com/v3io/v3io-go-http
```

Run the unit test at `src/github.com/v3io/demos/functions/ingest/ingest_test.go`. This uses a Nuclio SDK Golang wrapper.

### Building the demo

Clone this repository and cd into the netops directory:
```sh
git clone git@github.com:v3io/demos
cd netops
```

### Building the function images
Modify the source code and build the images:
```sh
NETOPS_TAG=latest make
```

This will output `netops-demo-golang:latest` and `netops-demo-py:latest` using Nuclio's ability to [build function images from Dockerfiles](https://github.com/nuclio/nuclio/blob/master/docs/tasks/deploy-functions-from-dockerfile.md). 
> The `golang` image contains the `ingest` and `query` functions. The `py` image contains the `generate` and `train` functions. By bunching together a few functions inside a single image we allow for easily sharing code without worrying about versioning, reducing the number of moving parts, etc. 

Push the images to your favorite Docker registry:
```
NETOPS_TAG=latest NETOPS_REGISTRY_URL=mydockerhubaccount make push
```

