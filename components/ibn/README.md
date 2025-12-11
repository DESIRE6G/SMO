# DESIRE6G IBN

IBN docker image generation is integrated into SMO/Makefile as well.
TODO: Kubernetes manifests

## Build the Docker image

To build the Docker image:

```bash
git clone git@github.com:nubispc/d6g.git
cd d6g/components/ibn
TAG=$(git describe --dirty --long --always)
docker build -t harbor.nbfc.io/desire6g/desire6g-ibn:$TAG .
```

## Required ENV variables

To run this component, the user must define the following ENV variables:

- `SERVICE_ORCHESTRATOR_HOST`: The hostname or IP address of the Service Orchestrator component
- `SERVICE_ORCHESTRATOR_PORT`: The port of the Service Orchestrator component
- `TOPOLOGY_MODULE_HOST`: The hostname or IP address of the Topology component
- `TOPOLOGY_MODULE_PORT`: The port of the Topology component
- `SERVICE_CATALOG_HOST`: The hostname or IP address of the Service Catalog component
- `SERVICE_CATALOG_PORT`: The port of the Service Catalog component

## Usage

Running the entire demo:

```bash
curl http://localhost:8005/api/demo
```

Listing catalog content:

```bash
curl http://localhost:8005/api/list
```

In case the required nodes are not defined in the topology the following command is used for easy node addition.
POST method is implemented.
TODO: Enable reading parameters from json file.

```bash
curl -X POST http://localhost:8005/api/add_topology \
    -H 'Content-Type: application/json' \
    -d '{"text": "fastapi is cool"}'
```
