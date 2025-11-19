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
TOPOLOGY_ENDPOINT="localhost:8002"
curl -X 'POST' \
"http://$TOPOLOGY_ENDPOINT/nodes/" \
-H 'accept: application/json' \
-H 'Content-Type: application/json' \
-d '{
"site_id": "SITEID1",
"cpu": 8,
"mem": 32,
"storage": 1024,
"iml_endpoint": "iml.siteid1.com"
}'

# curl -X 'POST' \
# "http://$TOPOLOGY_ENDPOINT/nodes/" \
# -H 'accept: application/json' \
# -H 'Content-Type: application/json' \
# -d '{
# "site_id": "SITEID2",
# "cpu": 32,
# "mem": 128,
# "storage": 3072,
# "iml_endpoint": "iml.siteid2.com"
# }'

# curl -X 'POST' \
# "http://$TOPOLOGY_ENDPOINT/nodes/" \
# -H 'accept: application/json' \
# -H 'Content-Type: application/json' \
# -d '{
# "site_id": "SITEID3",
# "cpu": 256,
# "mem": 1024,
# "storage": 131072,
# "iml_endpoint": "iml.siteid3.com"
# }'
```

Verify the nodes have been added succesfully:

```bash
TOPOLOGY_ENDPOINT="localhost:8002"
curl -X 'GET' \
"http://$TOPOLOGY_ENDPOINT/nodes/"  \
-H 'accept: application/json'
```

Check the fields of a specific node:

```bash
TOPOLOGY_ENDPOINT="localhost:8002"
curl -X 'GET' \
"http://$TOPOLOGY_ENDPOINT/nodes/SITEID1"  \
-H 'accept: application/json'
```

### Step 2: Upload Service Graph file to Service Catalog (Updated)

Next, we need to upload [demo_nsd2.sg.yaml](./demo/demo_nsd2.sg.yaml) to the Service Catalog.

```bash
SC_CATALOG=localhost:8001
curl -X 'POST' \
"http://$SC_CATALOG/catalog/" \
-F "file=@demo/demo_nsd2.sg.yaml" 
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
"http://$SC_CATALOG/retrieve/demo_nsd2.sg.yaml" \
  -H 'accept: application/json'
```

<!-- ### Step 3: Upload Network Functions file to Service Catalog -->

<!-- ```bash
SC_CATALOG=localhost:8001
curl -X 'POST' \
"http://$SC_CATALOG/catalog/" \
-F "file=@demo/apps.nf.yaml" 
``` -->

<!-- Similar with step 2, you can list and view all the files in the service catalog. -->

### Step 4: Deploy Service to Service Orchestrator

Deploy the Service Graph to the Service Orchestrator. 
<!-- This should fail since `desire6g-site` is not a site we have added to the Topology module. -->

<!-- ```terminal
$ SO_ENDPOINT=localhost:8000
$ curl -X 'POST' \
"http://$SO_ENDPOINT/services" \
-H 'Content-Type: application/json' \
-d '{"name": "demo_nsd2.sg.yaml"}'
{"detail":"Site not found"}
``` -->

<!-- Let's try again with an existing site: -->

```terminal
$ SO_ENDPOINT=localhost:8000
$ curl -X 'POST' \
"http://$SO_ENDPOINT/services" \
-H 'Content-Type: application/json' \
-d '{"name": "demo_nsd2.sg.yaml"}'
{"message":"Failure in Optimization Engine","status":"failed","error":"Optimization Engine failure: The local region does not have enough resources to host the service. Relaying service request to the next region."}
```

If we do that, we can now see the response when the Site has the required resources:

```terminal
$ SO_ENDPOINT=localhost:8000
$ curl -X 'POST' \
"http://$SO_ENDPOINT/services" \
-H 'Content-Type: application/json' \
-d '{"name": "demo_nsd2.sg.yaml"}' | jq
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

---

### Step 5: Trigger error (received from MAS->MLFO)


Check if MLFO is running:

```bash
curl -X 'GET' http://localhost:8004
```

Simulate error sent from MAS to MLFO (error code 1001 refers to application function for a given service_id is not running properly due to resource saturation):

```bash
curl -X 'POST' \
http://localhost:8004/process_error \
-H "Content-Type: application/json" \
-d '{
"agent_id":"agent_1",
"service_id":"dt-service-id",
"error_code":1001
}'
```

## Demo1

### Step 1: Add sites to the Topology Module

Add sites to the Topology Module:

```bash
TOPOLOGY_ENDPOINT="localhost:8002"
curl -X 'POST' \
   "http://$TOPOLOGY_ENDPOINT/nodes/" \
   -H 'accept: application/json' \
   -H 'Content-Type: application/json' \
   -d '{
   "site_id": "d6g-000",
   "cpu": 4,
   "mem": 8,
   "storage": 64,
   "iml_endpoint": "iml.siteid0.com"
   }'
curl -X 'POST' \
   "http://$TOPOLOGY_ENDPOINT/nodes/" \
   -H 'accept: application/json' \
   -H 'Content-Type: application/json' \
   -d '{
   "site_id": "d6g-001",
   "cpu": 8,
   "mem": 64,
   "storage": 2048,
   "iml_endpoint": "iml.siteid1.com"
   }'
curl -X 'POST' \
   "http://$TOPOLOGY_ENDPOINT/nodes/" \
   -H 'accept: application/json' \
   -H 'Content-Type: application/json' \
   -d '{
   "site_id": "d6g-002",
   "cpu": 32,
   "mem": 128,
   "storage": 3072,
   "iml_endpoint": "iml.siteid2.com"
   }'
```

Verify the nodes have been added succesfully:

```bash
curl -X 'GET' \
  "http://$TOPOLOGY_ENDPOINT/nodes/"  \
  -H 'accept: application/json'
```

### Step 2: Upload Service Graph to Service Catalog

Next, we need to upload [demo_nsd1.sg.yaml](./demo/demo_nsd1.sg.yaml) to the Service Catalog.

```bash
SC_CATALOG=localhost:8001
curl -X 'POST' \
"http://$SC_CATALOG/catalog/" \
-F "file=@demo/demo1_nsd.sg.yml"
```

Verify the Service Graph has been uploaded:

```bash
SC_CATALOG=localhost:8001
curl -X 'GET' \
"http://$SC_CATALOG/catalog/service_graph" \
-H 'accept: application/json'
```

Upload Applications to the Service Catalog.

```bash
SC_CATALOG=localhost:8001
# curl -X POST \
# "http://$SC_CATALOG/catalog/" \
# -H "Content-Type: application/json" -d '{"name": "apps","data": {"application-functions": [{"af-instance-id": "ar-edge-app-i01", "nf-vcpu": 2, "nf-memory": 5, "nf-storage": 25}, {"af-instance-id": "ar-source-app-i01", "nf-vcpu": 10, "nf-memory": 18, "nf-storage": 258}]}}'
echo 'application-functions:
  - af-instance-id: ar-edge-app-i01
    nf-vcpu: 2
    nf-memory: 5
    nf-storage: 25
  - af-instance-id: ar-source-app-i01
    nf-vcpu: 10
    nf-memory: 18
    nf-storage: 258' | curl -X POST \
"http://$SC_CATALOG/catalog/" \
-F "file=@-;filename=apps.nf.yaml"
```

### Step 3: Deploy Service to Service Orchestrator

Deploy the Service Graph to the Service Orchestrator. 

```terminal
$ SO_ENDPOINT=localhost:8000
$ curl -X 'POST' \
"http://$SO_ENDPOINT/services" \
-H 'Content-Type: application/json' \
-d '{"name": "demo1_nsd.sg.yml"}'