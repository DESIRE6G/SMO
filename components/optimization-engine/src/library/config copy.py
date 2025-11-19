# ProcessingSystems/config.py

import os

# RabbitMQ connection parameters
rabbitmq_host = os.getenv("RABBITMQ_HOST", "localhost")
input_topic = os.getenv("INPUT_TOPIC", "input_topic")
output_topic = os.getenv("OUTPUT_TOPIC", "output_topic")

# Kafka connection parameters
kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

# Site parameters (backwards compatible with old version)
d6g_site = None
site = os.getenv("SITE", "").strip()
# Remove surrounding quotes if present
if site.startswith('"') and site.endswith('"'):
    site = site[1:-1]
elif site.startswith("'") and site.endswith("'"):
    site = site[1:-1]

if "," in site:
    d6g_site = [s.strip() for s in site.split(",") if s.strip()]
else:
    d6g_site = site or None

# Topology Module connection parameters
TOPOLOGY_MODULE_HOST = os.getenv("TOPOLOGY_MODULE_HOST", "localhost")
TOPOLOGY_MODULE_PORT = os.getenv("TOPOLOGY_MODULE_PORT", "8000")

# Service Catalog connection parameters
SERVICE_CATALOG_HOST = os.getenv("SERVICE_CATALOG_HOST", "localhost")
SERVICE_CATALOG_PORT = os.getenv("SERVICE_CATALOG_PORT", "8003")
