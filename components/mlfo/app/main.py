# app/main.py
import json
import logging
from enum import IntEnum
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
import httpx
import yaml
from typing import Optional

# Force all string scalars to be double-quoted in YAML
from yaml import SafeDumper

# RabbitMQ
import pika
import os

from config import settings

class QuotedString(str):
    pass

def quoted_str_representer(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')

SafeDumper.add_representer(QuotedString, quoted_str_representer)

app = FastAPI()
logger = logging.getLogger("mlfo")
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logging.getLogger("pika").setLevel(logging.CRITICAL)

# one AsyncClient for all outbound calls
http_client = httpx.AsyncClient(timeout=10.0)

# ─── Error Codes ────────────────────────────────────────────────────────────────

class ErrorCode(IntEnum):
    INSUFFICIENT_RESOURCES = 1001
    OUTDATED_CONFIGURATION  = 1002
    # add more here…

# ─── Models ─────────────────────────────────────────────────────────────────────
class PipelineRequest(BaseModel):
    service_id: str
    num_agents: int = 1
    kafka_ip: Optional[str] = "10.5.1.21"
    kafka_port: Optional[str] = "9191"
    kafka_topic: Optional[str] = "applications"
    kafka_id: Optional[str] = "30"
    cpu_percentage_threshold: Optional[str] = "90"
    mlfo_endpoint: Optional[str] = "http://10.5.15.55:8004"
    container_port: Optional[int] = 8000
    host_port: Optional[int] = 8005
    image: Optional[str] = 'mas-agent:latest'
    image_pull_policy: Optional[str] = 'IfNotPresent'

class ErrorRequest(BaseModel):
    agent_id: str
    service_id: str
    error_code: int

# ─── Endpoints ───────────────────────────────────────────────────────────────────

@app.get("/")
def health_check():
    return {"config": settings.model_dump()}


@app.post(
    "/compute_mas_pipeline",
    response_class=Response,
    responses={200: {"content": {"application/x-yaml": {}}}},
)
def compute_mas_pipeline(req: PipelineRequest):
    """
    Returns N Pod descriptors as YAML, one per agent, using parameters passed in request.
    Increments container_port for each pod.
    """
    mlfo_ep = QuotedString(req.mlfo_endpoint.rstrip('/'))
    pods = []

    for i in range(1, req.num_agents + 1):
        name = f"mas-agent-{i}"
        # increment container port per agent
        hport = req.host_port + (i - 1)
        cport = req.container_port
        env_vars = [
            {"name": "KAFKA_IP", "value": QuotedString(req.kafka_ip)},
            {"name": "KAFKA_PORT", "value": QuotedString(req.kafka_port)},
            {"name": "KAFKA_TOPIC", "value": QuotedString(req.kafka_topic)},
            {"name": "KAFKA_ID", "value": QuotedString(req.kafka_id)},
            {"name": "CPU_PERCENTAGE_THRESHOLD", "value": QuotedString(req.cpu_percentage_threshold)},
            {"name": "TARGET_SERVICE_ID", "value": QuotedString(req.service_id)},
            {"name": "MLFO_ENDPOINT", "value": mlfo_ep},
            {"name": "ID", "value": QuotedString(f"agent_{i}")},
        ]
        container = {
            "name": "agent",
            "image": QuotedString(req.image),
            "imagePullPolicy": QuotedString(req.image_pull_policy),
            "ports": [{"containerPort": cport, "hostPort": hport}],
            "env": env_vars,
        }
        pod = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": name, "labels": {"app": "mas-agent"}},
            "spec": {"containers": [container]},
        }
        pods.append(pod)
    yaml_str = yaml.dump_all(
        pods,
        sort_keys=False,
        Dumper=SafeDumper,
        default_flow_style=False,
        indent=2
    )
    return Response(content=yaml_str, media_type="application/x-yaml")

@app.post("/process_error")
async def process_error(req: ErrorRequest):
    if req.error_code == ErrorCode.INSUFFICIENT_RESOURCES:
        logger.error(
            "🚨 KPI violation detected by agent '%s' for service '%s' (ERROR_CODE=%s)",
            req.agent_id,
            req.service_id,
            ErrorCode.INSUFFICIENT_RESOURCES.name
        )
        payload = {
            "service_id": req.service_id,
            "error_code": req.error_code,
        }
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=settings.rabbitmq_host, port=settings.rabbitmq_port))
            channel = connection.channel()
            channel.queue_declare(queue=settings.so_topic)
            channel.basic_publish(exchange='', routing_key=settings.so_topic, body=json.dumps(payload))
            connection.close()
            return {"status": "mitigated", "error_code": req.error_code}
        except httpx.HTTPError as e:
            logger.error("Failed to notify SO: %s", e)
            raise HTTPException(status_code=502, detail=str(e))
        else:
            return {"status": "mitigated", "error_code": req.error_code}

@app.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()
