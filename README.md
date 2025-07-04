# d6g

This repository contains the required code, deployment files and instructions
to deploy the Desire6G framework in an existing Kubernetes cluster.

## Deployment

### Build the images

To build the Docker images for the DESIRE6G components:

```bash
git clone git@github.com:nubispc/d6g.git
cd d6g
make images
```

### Generate the K8S YAMLs

```bash
make deploy
```

### Deploy the components

```bash
kubectl apply -f deployment/deploy/
```

> Note: Before deploying make sure you edit the `servicecatalog-creds.yaml` file to contain your base64 encoded Github credentials.

## Local deployment

To faciliate easier debugging, another Makefile target is available to allow users to deploy
all components locally using Docker Compose.

```bash
git clone git@github.com:nubispc/d6g.git
cd d6g
make images
make local
docker compose -f deployment/compose/docker-compose.yaml up -d
```

> Note: Before deploying make sure you edit the `deployment/compose/docker-compose.yaml` file to contain your base64 encoded Github credentials.

## Usage

The following instruction were tested on a local deployment. However, the only change required to
use them in a Kubernetes cluster is to change the URL of each component with the respective
k8s service exposing that component.

### Step 1: Add sites to Topology module

To add sites to Topology module:

```bash
TOPOLODY_ENDPOINT="localhost:8002"
curl -X 'POST' \
"http://$TOPOLODY_ENDPOINT/nodes/" \
-H 'accept: application/json' \
-H 'Content-Type: application/json' \
-d '{
"site_id": "SITEID1",
"cpu": 8,
"mem": 32,
"storage": 1024,
"iml_endpoint": "iml.siteid1.com"
}'

curl -X 'POST' \
"http://$TOPOLODY_ENDPOINT/nodes/" \
-H 'accept: application/json' \
-H 'Content-Type: application/json' \
-d '{
"site_id": "SITEID2",
"cpu": 32,
"mem": 128,
"storage": 3072,
"iml_endpoint": "iml.siteid2.com"
}'

curl -X 'POST' \
"http://$TOPOLODY_ENDPOINT/nodes/" \
-H 'accept: application/json' \
-H 'Content-Type: application/json' \
-d '{
"site_id": "SITEID3",
"cpu": 256,
"mem": 1024,
"storage": 131072,
"iml_endpoint": "iml.siteid3.com"
}'
```

Verify the nodes have been added succesfully:

```bash
TOPOLODY_ENDPOINT="localhost:8002"
curl -X 'GET' \
"http://$TOPOLODY_ENDPOINT/nodes/"  \
-H 'accept: application/json'
```

Check the fields of a specific node:

```bash
TOPOLODY_ENDPOINT="localhost:8002"
curl -X 'GET' \
"http://$TOPOLODY_ENDPOINT/nodes/SITEID1"  \
-H 'accept: application/json'
```

### Step 2: Upload Service Graph file to Service Catalog

Next, we need to upload [demo_nsd1.sg.yaml](./demo/demo_nsd1.sg.yaml) to the Service Catalog.

```bash
SC_CATALOG=localhost:8001
curl -X 'POST' \
"http://$SC_CATALOG/catalog/" \
-F "file=@demo/demo_nsd1.sg.yaml" 
```

Verify the Service Graph has been uploaded:

```bash
SC_CATALOG=localhost:8001
curl -X 'GET' \
"http://$SC_CATALOG/catalog/service_graph" \
-H 'accept: application/json'
```

Inspect the contents of the Service Graph:

```bash
SC_CATALOG=localhost:8001
curl -X 'GET' \
"http://$SC_CATALOG/retrieve/demo_nsd1.sg.yaml" \
  -H 'accept: application/json'
```

### Step 3: Upload Network Functions file to Service Catalog

```bash
SC_CATALOG=localhost:8001
curl -X 'POST' \
"http://$SC_CATALOG/catalog/" \
-F "file=@demo/apps.nf.yaml" 
```

Similar with step 2, you can list and view all the files in the service catalog.

### Step 4: Deploy Service to Service Orchestrator

Deploy the Service Graph to the Service Orchestrator. This should fail since `desire6g-site` is not
a site we have added to the Topology module.

```terminal
$ SO_ENDPOINT=localhost:8000
$ curl -X 'POST' \
"http://$SO_ENDPOINT/services" \
-H 'Content-Type: application/json' \
-d '{"name": "demo_nsd2.sg.yaml", "site_id": "desire6g-site"}'
{"detail":"Site not found"}
```

Let's try again with an existing site:

```terminal
$ SO_ENDPOINT=localhost:8000
$ curl -X 'POST' \
"http://$SO_ENDPOINT/services" \
-H 'Content-Type: application/json' \
-d '{"name": "demo_nsd2.sg.yaml", "site_id": "SITEID1"}'
{"message":"Failure in Optimization Engine","status":"failed","error":"Optimization Engine failure: The local region does not have enough resources to host the service. Relaying service request to the next region."}
```

If we do that, we can now see the response when the Site has the required resources:

```terminal
$ SO_ENDPOINT=localhost:8000
$ curl -X 'POST' \
"http://$SO_ENDPOINT/services" \
-H 'Content-Type: application/json' \
-d '{"name": "demo_nsd2.sg.yaml", "site_id": "SITEID3"}' | jq
{
  "message": "Failed to deploy service to IML",
  "status": "failed",
  "service_name": "demo_nsd2.sg.yaml",
  "site_id": "SITEID3",
  "iml_endpoint": "iml.siteid3.com",
  "requested_service": {
    "lnsd": {
      "ns-instance-id": "11223344-e2a8-4338-bc8c-be685548bad2",
      "ns": {
        "name": "Digital Twin Demo",
        "id": "418420e3-e2a8-4338-bc8c-be685548bad2",
        "vendor": "D6G",
        .
        .
        .
      }
    }
  }
}
```

This is expected since there is no IML endpoint reachable in this configuration.

Now we can query the API to get all the deployed services as well as all the service requests:

```bash
SO_ENDPOINT=localhost:8000
curl -X 'GET' \
"http://$SO_ENDPOINT/services" \
-H 'accept: application/json'

curl -X 'GET' \
"http://$SO_ENDPOINT/requests" \
-H 'accept: application/json'
```
