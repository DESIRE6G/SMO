# d6g Optimization Engine

The source code found in this repo is copied from [desire6g-test-component](https://github.com/anestisdalgkitsis/desire6g-test-component).
Only a minor change was required to allow the system to handle both JSON and YAML formatted messages.

## Build the Docker image

To build the Docker image:

```bash
git clone git@github.com:nubispc/d6g.git
cd d6g/components/optimization-engine
TAG=$(git describe --dirty --long --always)
docker build -t harbor.nbfc.io/desire6g/desire6g-oe:$TAG .
```

## Required ENV variables

To run this component, the user must define the following ENV variables:

- `RABBITMQ_HOST`: The hostname or IP address of the RabbitMQ broker (only applicable when using RabbitMQ messaging system)
- `INPUT_TOPIC`: The topic that the Optimization Engine will use to receive the unoptimized Service Graph to the Service Orchestrator
- `OUTPUT_TOPIC`: The topic that the Optimization Engine will use to return the optimized Service Grahps
- `KAFKA_BOOTSTRAP_SERVERS`: The Kafka bootstrap server (only applicable when using Kafka messaging system)
- `SITE`: List of D6G site IDs where the SMO manages.
- `TOPOLOGY_MODULE_HOST`: The hostname or IP address of the Topology component
- `TOPOLOGY_MODULE_PORT`: The port of the Topology component
- `SERVICE_CATALOG_HOST`: The hostname or IP address of the Service Catalog component
- `SERVICE_CATALOG_PORT`: The port of the Service Catalog component
