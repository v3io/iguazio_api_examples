# NetOps demo

This demo simulates network data and both detects and predicts anomalies. 

This demo is composed of a few parts:
1. An Iguazio system
2. Nuclio functions that generate and ingest historical and real-time metric samples into the Iguazio TSDB
3. Grafana for visualization of metrics

Setting up an Iguazio system including Grafana and Nuclio is out of the scope of this document


## Deploying the demo

### With helm
TODO: describe how to deploy the demo using helm.


### With nuctl
> Reminder: Add `--platform local` to deploy to a Docker-based Nuclio installation (as opposed to Nuclio over Kubernetes)

Start by creating a `netops` project:
```sh
nuctl create project netops --display-name 'NetOps demo'
```

Deploy the functions, providing the following variables:
* NETOPS_WEBAPI_URL: The WebAPI URL (e.g. `http://10.0.0.1:8081`)
* NETOPS_CONTAINER_ALIAS: The Iguazio container URL to which we want to ingest the metrics (e.g. `bigdata`)
* NETOPS_TSDB_TABLE_NAME: The name of the table to which we will ingest metrics (e.g. `mytsdb`). If this is not set, no ingestion to TSDB occurs
* NETOPS_ANODOT_TOKEN: The Anodot API token. If this is not set, no ingestion to Anodot occurs

```sh
nuctl deploy \
  --run-image netops-golang:latest \
  --runtime golang \
  --handler main:Ingest \
  --project-name netops \
  --readiness-timeout 10 \
  --data-bindings '{"db0": {"class": "v3io", "url": "$(NETOPS_WEBAPI_URL)/$(NETOPS_CONTAINER_ALIAS)", "secret": "<user>:<password>"}}' \
  --env INGEST_V3IO_TSDB_PATH=NETOPS_TSDB_TABLE_NAME \
  netops-ingest
`
```

## Building the images

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