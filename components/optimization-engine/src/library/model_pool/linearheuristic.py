# Linear Heuristic Demo 1 Deterministic Partitioning
# MOCK PARTITIONING ALGORITHM FOR DEMO PURPOSES
# Anestis Dalgkitsis | v2.58

# Modules
import logging
import networkx as nx
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# simple partition with random cut points
def linearheuristic(service_request, apps, resources, service_graph, topology_graph, domains):

    # Check delete after testing
    # logger.info("service_request: " + str(service_request))
    # logger.info("apps: " + str(apps))
    # logger.info("resources: " + str(resources))
    # logger.info("service_graph: " + str(service_graph))
    # logger.info("topology_graph: " + str(topology_graph))
    # logger.info("domains: " + str(domains))

    # SERVICE DECORATIONS MOD
    
    # Decode bytes to string and parse JSON
    if isinstance(service_request, bytes):
        service_request_str = service_request.decode('utf-8')
        service_request_dict = json.loads(service_request_str)
    else:
        service_request_dict = service_request
    
    # Extract common fields from service request
    ns_instance_id = str(service_request_dict.get("lnsd", {}).get("ns-instance-id", "Not found"))
    name = str(service_request_dict.get("lnsd", {}).get("ns", {}).get("name", "Not found"))
    parent_service_id = str(service_request_dict.get("lnsd", {}).get("ns", {}).get("id", "Not found"))
    vendor = str(service_request_dict.get("lnsd", {}).get("ns", {}).get("vendor", "Not found"))
    version = str(service_request_dict.get("lnsd", {}).get("ns", {}).get("descriptor-version", "Not found"))
    location_id = service_request_dict.get("lnsd", {}).get("ns", {}).get("location-id", "Not found")
    default_service_id = str(service_request_dict.get("lnsd", {}).get("ns", {}).get("default-service-id", "Not found"))
    default_nfrouter_mode = str(service_request_dict.get("lnsd", {}).get("ns", {}).get("default-nfrouter-mode", "Not found"))
    default_interpod_mode = str(service_request_dict.get("lnsd", {}).get("ns", {}).get("default-interpod-mode", "Not found"))

    # Extract application-functions, site-connections, and forwarding_graphs
    application_functions = service_request_dict.get("lnsd", {}).get("ns", {}).get("application-functions", [])
    site_connections = service_request_dict.get("lnsd", {}).get("ns", {}).get("site-connections", [])
    forwarding_graphs = service_request_dict.get("lnsd", {}).get("ns", {}).get("forwarding_graphs", [])

    # logger.info("----")

    # LINEAR HEURISTIC PARTITIONING
    # Extract site-connections by id
    site1_connection = None
    site2_connection = None
    for sc in site_connections:
        if sc.get("id") == "site1":
            site1_connection = sc
        elif sc.get("id") == "site2":
            site2_connection = sc

    # logger.info("site1_connection: " + str(site1_connection))
    # logger.info("site2_connection: " + str(site2_connection))
    # logger.info("application_functions: " + str(application_functions))
    # logger.info("forwarding_graphs: " + str(forwarding_graphs))

    # logger.info("----")

    # SERVICEGEN
    partitions = []
    
    # Generate partition 0 for site1 (empty base partition)
    partition_0 = {
        "lnsd": {
            "ns-instance-id": ns_instance_id,
            "ns": {
                "name": name,
                "id": parent_service_id,
                "vendor": vendor,
                "descriptor-version": version,
                "site-id": "site1",
                "location-id": location_id,
                "default-service-id": default_service_id,
                "default-nfrouter-mode": default_nfrouter_mode,
                "default-interpod-mode": default_interpod_mode,
                "infra-nfs": [],
                "network-functions": [],
                "application-functions": [],
                "site-connections": [],
                "forwarding_graphs": []
            }
        }
    }
    partitions.append(partition_0)
    
    # Generate partition 1 for site1 (with site2 connection and forwarding graphs)
    partition_1 = {
        "lnsd": {
            "ns-instance-id": ns_instance_id,
            "ns": {
                "name": name,
                "id": parent_service_id,
                "vendor": vendor,
                "descriptor-version": version,
                "site-id": "site1",
                "location-id": location_id,
                "default-service-id": default_service_id,
                "default-nfrouter-mode": default_nfrouter_mode,
                "default-interpod-mode": default_interpod_mode,
                "infra-nfs": [],
                "network-functions": [],
                "application-functions": [],
                "site-connections": [site2_connection] if site2_connection else [],
                "forwarding_graphs": forwarding_graphs if forwarding_graphs else []
            }
        }
    }
    partitions.append(partition_1)
    
    # Generate partition 2 for site2 (with site1 connection, application-functions, and forwarding graphs)
    partition_2 = {
        "lnsd": {
            "ns-instance-id": "55667788",  # New instance id for site2 partition
            "ns": {
                "name": name,
                "id": "ccccdddd",  # New id for site2 partition
                "vendor": vendor,
                "descriptor-version": version,
                "site-id": "site2",
                "location-id": location_id,
                "default-service-id": default_service_id,
                "default-nfrouter-mode": default_nfrouter_mode,
                "default-interpod-mode": default_interpod_mode,
                "infra-nfs": [],
                "network-functions": [],
                "site-connections": [site1_connection] if site1_connection else [],
                "application-functions": application_functions if application_functions else [],
                "forwarding_graphs": forwarding_graphs if forwarding_graphs else []
            }
        }
    }
    partitions.append(partition_2)
    
    logger.info("Generated " + str(len(partitions)) + " partitions")
    
    return partitions
