from fastapi import FastAPI, Body, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from io import BytesIO
import requests
import base64
import os
import re
from library.messaging import get_message_client
import json
import yaml
import time
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



client = None
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create connection for this worker
    global client
    client = get_message_client()
    await client.connect()
    yield
    # Shutdown: close connection
    await client.close()


tags_metadata = [
    {
        "name": "services",
        "description": "Service management endpoints",
    },
    {
        "name": "requests",
        "description": "Request management endpoints",
    },
]

app = FastAPI(lifespan=lifespan, openapi_tags=tags_metadata)
#app = FastAPI(openapi_tags=tags_metadata)


class ServiceRequest(BaseModel):
    name: str
    # site_id: str
    # json_data: dict

class ErrorRequest(BaseModel):
    service_id: str
    error_code: int

# In-memory state storage
request_states = {}
deployed_services = {}

TOPOLOGY_MODULE_URL = f"http://{os.getenv("TOPOLOGY_MODULE_HOST", "localhost")}:{os.getenv("TOPOLOGY_MODULE_PORT", "8000")}"
SERVICE_CATALOG_URL = f"http://{os.getenv("SERVICE_CATALOG_HOST", "localhost")}:{os.getenv("SERVICE_CATALOG_PORT", "8003")}"


@app.post("/services", tags=["services"])
async def deploy_service(service_request: ServiceRequest = Body(...)):
    start1 = time.time()
    request_id = len(request_states) + 1
    request_states[request_id] = {
        "status": "processing", "input": {"name": service_request.name}, "output": None} # , "site_id": service_request.site_id

    file_name = service_request.name
    try:
        file_content = download_file_from_catalog(file_name)
        if file_content is None:
            raise HTTPException(
                status_code=404, detail=f"File {file_name} not found in the service catalog")
    except:
        raise HTTPException(
            status_code=500, detail=f"Error downloading file from catalog")

    end1 = time.time()

    logger.info(f"Worker PID {os.getpid()} - Connection ID: {id(client.connection)}")
    start2 = time.time()
    response_content = await client.call_oe(base64.b64encode(file_content.encode()))

    #iml_endpoint = "http://localhost:5000"  # Default value if not found
    #site_id = service_request.site_id

    #response_content = await client.receive_message()
    end2 = time.time()
    start3 = time.time()
    response_content=interpret_message(response_content)
    if response_content:
        #print(f"Received final message: {response_content}")
        request_states[request_id]["status"] = "completed"
        request_states[request_id]["output"] = response_content
        if "Error" in response_content:
            request_states[request_id]["status"] = "failed"
            return JSONResponse(content={"message": "Error in Optimization Engine", "status": "failed",
                                         "error": f"Optimization Engine error: {response_content["Error"]}"})
        if "Failed" in response_content:
            request_states[request_id]["status"] = "failed"
            return JSONResponse(content={"message": "Failure in Optimization Engine", "status": "failed",
                                         "error": f"Optimization Engine failure: {response_content["Failed"]}"})
        yaml_file_content = yaml.dump(response_content).encode('utf-8')
        
        end3 = time.time()
        content = list()
        # Convert the string content to a file-like object.
        # TODO: This line caused errors. Perhaps we need to remove it.
        # Also the b64 decode step is not needed at the moment.
        # file_like_object = BytesIO(base64.b64decode(response_content).decode().encode('utf-8'))
        #print(yaml_file_content)
        timings = list()
        for serv in response_content:
            start4 = time.time()
            site_id = serv['lnsd']['ns']['site-id']
            # Check if the site exists in the topology component
            response = requests.get(f"{TOPOLOGY_MODULE_URL}/nodes/{site_id}")
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code,
                                    detail="Site not found")
            site_dict = response.json()
            if "iml_endpoint" in site_dict:
                iml_endpoint = site_dict["iml_endpoint"]
            else:
                print("IML endpoint not found in the site dictionary, using default.")
                iml_endpoint = "http://localhost:5000"  # Default value if not found

            print("Deploying in ", site_id, iml_endpoint)
            end4 = time.time()
            total4 = end4-start4
            print(f"site_id_retrieval: {total4}")
            print("Service in YAML: ")
            start5 = time.time()
            serv_yaml = yaml.dump(serv).encode('utf-8')
            #print(serv_yaml)
        
            file_like_object = BytesIO(serv_yaml)
            
            files = {'file': (f"demo_nsd-{site_id}.yml", file_like_object)}
            
            try:
                # The timeout tuple is set to (0.5, 10) seconds for connection and read timeouts respectively.
                # TODO: When integrating with IML, we need to increase the connection timeout.
                #iml_response = requests.post(f"{iml_endpoint}", files=files, timeout=(0.5, 10))
                #print(iml_response.json())
                # import pdb;pdb.set_trace()

                #json_data = iml_response.json()['response']
                # Use a regular expression to find key-value pairs
                #pattern = r'(\w+):\s*([^,}]+)'
                #matches = re.findall(pattern, json_data)

                # Convert the matches to a dictionary
                #structured_dict = {key: value for key, value in matches}

                structured_dict = {'id': '10', 'Deployed': 'myservice'}
                service_id = int(structured_dict["id"])
                #service_id = str(site_id) + "SOMERANDOMID"
                service_name = structured_dict["Deployed"]
                #service_name = str(site_id) + "-service"
                deployed_services[service_id] = {
                    "status": "deployed", "service_name": service_name, "file_name": file_name, "site_id": site_id, "iml_endpoint": iml_endpoint}

                end5 = time.time()
                total5 = end5 - start5
                print(f"deploy: {total5}")
                #return JSONResponse(content={"message": "Received", "data": iml_response.json(), "file": base64.b64decode(response_content).decode(), "site_id": site_id, "service_id": service_id })
                #return JSONResponse(content={"message": "Received", "status": "deployed", "service_name": service_name,
                #                             "file_name": file_name, "site_id": site_id, "iml_endpoint": iml_endpoint})
            except:
                request_states[request_id]["status"] = "failed"
                return JSONResponse(content={"message": "Failed to deploy service to IML", "status": "failed",
                                         "service_name": service_request.name, "site_id": site_id,
                                         "iml_endpoint": iml_endpoint,
                                         "requested_service": response_content})
            timings.append({"site_retrieve": total4, "deploy": total5})
            content.append({"message": "Received", "status": "deployed", "service_name": service_name,
                "file_name": file_name, "site_id": site_id, "iml_endpoint": iml_endpoint, "data": json.dumps(serv) })
        total1 = end1-start1
        total2 = end2-start2
        total3 = end3-start3
        measurements = {"sc": total1, "mq": total2, "OE": total3, "deploy": timings}
        return JSONResponse(content={'data': content, 'measure': measurements})
    else:
        print("No final message received.")
        request_states[request_id]["status"] = "failed"
        return JSONResponse(content={"message": "No Message"})


@app.get("/services", tags=["services"])
async def get_services():
    return JSONResponse(content={"deployed_services": list(deployed_services.keys())})


@app.get("/services/{service_id}", tags=["services"])
async def get_service_by_id(service_id: str):
    if service_id not in deployed_services:
        raise HTTPException(status_code=404, detail="Service not found")
    return JSONResponse(content={"service_name": service_id, "details": deployed_services[service_id]})


@app.delete("/services/{service_id}", tags=["services"])
async def delete_service(service_id: str):
    if service_id not in deployed_services:
        raise HTTPException(status_code=404, detail="Service not found")
    iml_endpoint = deployed_services[service_id]["iml_endpoint"]

    # TODO: Check if the deletion was successful
    response = requests.delete(f"{iml_endpoint}/{service_id}")

    # Remove the service from the deployed_services dictionary
    del deployed_services[service_id]
    return JSONResponse(content={"message": "Service deleted", "service_id": service_id})


@app.get("/requests", tags=["requests"])
async def get_requests():
    return JSONResponse(content={"requested_services": list(request_states.keys())})


@app.get("/requests/{request_id}", tags=["requests"])
async def get_request_by_id(request_id: int):
    if request_id not in request_states:
        raise HTTPException(status_code=404, detail="Request not found")
    return JSONResponse(content={"request": request_id, "details": request_states[request_id]})


def download_file_from_catalog(file_name: str) -> str | None:
    url = f'{SERVICE_CATALOG_URL}/retrieve/{file_name}'
    print(f"Downloading file from {url}")
    try:
        response = requests.get(url)
        print(f"Response status code: {response.status_code}")
        response.raise_for_status()
    except:
        print(f"Error downloading file: {response.text}")
        return None
    if response.status_code == 200:
        return response.json()["file_content"]
    else:
        print(f"Failed to download file: {response.text}")
        return None

def interpret_message(message):
    if message is None:
        return None
    try:
        message = base64.b64decode(message).decode('utf-8')
    except Exception:
        pass
    msg = ""
    try:
        msg = json.loads(message)
    except:
        pass
    try:
        msg = yaml.safe_load(message)
    except:
        pass
    if isinstance(msg, str):
        if msg == "":
            return None
    return msg
        
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
