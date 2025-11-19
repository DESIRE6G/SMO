# Linear Heuristic Demo 1 Deterministic Partitioning
# MOCK PARTITIONING ALGORITHM FOR DEMO PURPOSES
# Anestis Dalgkitsis | v1.2

# Modules
import logging
import networkx as nx
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# simple partition with random cut points
def linearheuristic(service_request, apps, resources, service_graph, topology_graph, domains):

    # Check delete after testing
    logger.info("service_request: " + str(service_request))
    logger.info("apps: " + str(apps))
    logger.info("resources: " + str(resources))
    logger.info("service_graph: " + str(service_graph))
    logger.info("topology_graph: " + str(topology_graph))
    logger.info("domains: " + str(domains))

    # SERVICE DECORATIONS MOD
    
    # Decode bytes to string and parse JSON
    if isinstance(service_request, bytes):
        service_request_str = service_request.decode('utf-8')
        service_request_dict = json.loads(service_request_str)
    else:
        service_request_dict = service_request
    
    # logger.info("NSD_TEST: " + str(service_request_dict.get("lnsd", {}).get("ns-instance-id", "Not found")))
    partition_type = "lnsd"
    ns_instance_id = str(service_request_dict.get("lnsd", {}).get("ns-instance-id", "Not found"))
    name = str(service_request_dict.get("lnsd", {}).get("ns", {}).get("name", "Not found"))
    parent_service_id = str(service_request_dict.get("lnsd", {}).get("ns", {}).get("id", "Not found"))
    vendor = str(service_request_dict.get("lnsd", {}).get("ns", {}).get("vendor", "Not found"))
    version = str(service_request_dict.get("lnsd", {}).get("ns", {}).get("descriptor-version", "Not found"))

    logger.info("----")

    # LINEAR HEURISTIC PARTITIONING
    for domain in range(0, domains):

        logger.info("RUN START: " + str(domain))

        # DRONE SITE DOMAIN EDGE
        site_id0 = resources[0].get("site-resources", [])[0].get("site-id-ref", "Not found") if len(resources) > 0 and len(resources[0].get("site-resources", [])) > 0 else "Not found" # site_id0 = "d6g-000" # Update to fetch dynamically from topology
        first_app = service_request_dict.get("lnsd", {}).get("ns", {}).get("application-functions", [])[0] if len(service_request_dict.get("lnsd", {}).get("ns", {}).get("application-functions", [])) > 0 else "Not found" # apps.get("application-functions", [])[0] if len(apps.get("application-functions", [])) > 0 else "Not found" # load af-1 for drone
        sc_1 = service_request_dict.get("lnsd", {}).get("ns", {}).get("site-connections", [])[0] if len(service_request_dict.get("lnsd", {}).get("ns", {}).get("site-connections", [])) > 0 else "Not found" # load sc-1 for drone
        fg_1 = service_request_dict.get("lnsd", {}).get("ns", {}).get("forwarding_graphs", [])[0] if len(service_request_dict.get("lnsd", {}).get("ns", {}).get("forwarding_graphs", [])) > 0 else "Not found" # load fg-1 for drone
        delay_budget_site0 = {"e2e_delay_budget": "5ms"} # set e2e_delay_budget 5ms for drone

        logger.info("site_id0: " + str(site_id0))
        logger.info("first_app: " + str(first_app))
        logger.info("sc_1: " + str(sc_1))
        logger.info("fg_1: " + str(fg_1))
        logger.info("delay_budget_site0: " + str(delay_budget_site0))

        # DOMAIN CORE
        site_id1 = resources[1].get("site-resources", [])[0].get("site-id-ref", "Not found") if len(resources) > 1 and len(resources[1].get("site-resources", [])) > 0 else "Not found" # site_id1 = "d6g-001" # Update to fetch dynamically from topology
        mas_agent_site1 = service_request_dict.get("lnsd", {}).get("ns", {}).get("mas-agent", [])[0] if len(service_request_dict.get("lnsd", {}).get("ns", {}).get("mas-agent", [])) > 0 else "Not found" # load mas-agent "mas-site1-001"
        site_connections = service_request_dict.get("lnsd", {}).get("ns", {}).get("site-connections", [])
        sc_2 = site_connections[1] if len(site_connections) > 1 else "Not found" # load sc-2 "sc1-sc2"
        sc_3 = site_connections[2] if len(site_connections) > 2 else "Not found" # and sc-3 "sc0-sc1"
        fg_2 = service_request_dict.get("lnsd", {}).get("ns", {}).get("forwarding_graphs", [])[1] if len(service_request_dict.get("lnsd", {}).get("ns", {}).get("forwarding_graphs", [])) > 0 else "Not found" # load fg-2
        delay_budget_site1 = {"e2e_delay_budget": "15ms"} # set e2e_delay_budget 15ms for drone

        logger.info("site_id1: " + str(site_id1))
        logger.info("mas_agent_site1: " + str(mas_agent_site1))
        logger.info("sc_2: " + str(sc_2))
        logger.info("sc_3: " + str(sc_3))
        logger.info("fg_2: " + str(fg_2))
        logger.info("delay_budget_site1: " + str(delay_budget_site1))

        # DOMAIN REMOTE
        site_id2 = resources[2].get("site-resources", [])[0].get("site-id-ref", "Not found") if len(resources) > 2 and len(resources[2].get("site-resources", [])) > 0 else "Not found" # site_id2 = "d6g-002" # Update to fetch dynamically from topology
        app_functions = service_request_dict.get("lnsd", {}).get("ns", {}).get("application-functions", [])
        second_app = app_functions[1] if len(app_functions) > 1 else "Not found" # load af-2
        mas_agents = service_request_dict.get("lnsd", {}).get("ns", {}).get("mas-agent", [])
        mas_agent_site2 = mas_agents[1] if len(mas_agents) > 1 else "Not found" # load mas-agent "mas-site2-001"
        sc_4 = site_connections[3] if len(site_connections) > 3 else "Not found" # load sc-4
        fg_3 = service_request_dict.get("lnsd", {}).get("ns", {}).get("forwarding_graphs", [])[2] if len(service_request_dict.get("lnsd", {}).get("ns", {}).get("forwarding_graphs", [])) > 0 else "Not found" # load fg-3
        delay_budget_site2 = {"e2e_delay_budget": "5ms"} # set e2e_delay_budget 5ms
        
        logger.info("site_id2: " + str(site_id2))
        logger.info("second_app: " + str(second_app))
        logger.info("mas_agent_site2: " + str(mas_agent_site2))
        logger.info("sc_4: " + str(sc_4))
        logger.info("fg_3: " + str(fg_3))
        logger.info("delay_budget_site2: " + str(delay_budget_site2))

        logger.info("RUN END: " + str(domain))
    
    logger.info("----")

    # SERVICEGEN
    partitions = []
    
    # Generate partition for site d6g-000 (domain 0)
    partition_0 = {
        "lnsd": {
            "ns-instance-id": ns_instance_id,
            "ns": {
                "name": name,
                "id": parent_service_id,
                "vendor": vendor,
                "descriptor-version": version,
                "site-id": site_id0,
                "application-functions": [first_app] if first_app != "Not found" else [],
                "site-connections": [sc_1] if sc_1 != "Not found" else [],
                "forwarding_graphs": [fg_1] if fg_1 != "Not found" else [],
                "e2e_delay_budget": delay_budget_site0.get("e2e_delay_budget", "5ms")
            }
        }
    }
    partitions.append(partition_0)
    
    # Generate partition for site d6g-001 (domain 1)
    partition_1 = {
        "lnsd": {
            "ns-instance-id": ns_instance_id,
            "ns": {
                "name": name,
                "id": parent_service_id,
                "vendor": vendor,
                "descriptor-version": version,
                "site-id": site_id1,
                "mas-agent": mas_agent_site1 if mas_agent_site1 != "Not found" else {},
                "site-connections": [sc_2, sc_3] if sc_2 != "Not found" and sc_3 != "Not found" else [],
                "forwarding_graphs": [fg_2] if fg_2 != "Not found" else [],
                "e2e_delay_budget": delay_budget_site1.get("e2e_delay_budget", "15ms")
            }
        }
    }
    partitions.append(partition_1)
    
    # Generate partition for site d6g-002 (domain 2)
    partition_2 = {
        "lnsd": {
            "ns-instance-id": ns_instance_id,
            "ns": {
                "name": name,
                "id": parent_service_id,
                "vendor": vendor,
                "descriptor-version": version,
                "site-id": site_id2,
                "application-functions": [second_app] if second_app != "Not found" else [],
                "mas-agent": mas_agent_site2 if mas_agent_site2 != "Not found" else {},
                "site-connections": [sc_4] if sc_4 != "Not found" else [],
                "forwarding_graphs": [fg_3] if fg_3 != "Not found" else [],
                "e2e_delay_budget": delay_budget_site2.get("e2e_delay_budget", "5ms")
            }
        }
    }
    partitions.append(partition_2)
    
    logger.info("Generated " + str(len(partitions)) + " partitions")
    
    return partitions
