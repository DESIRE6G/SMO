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
    
    # Handle both 'nsd' and 'lnsd' input formats
    if "nsd" in service_request_dict:
        nsd_root = service_request_dict.get("nsd", {})
    else:
        nsd_root = service_request_dict.get("lnsd", {})
    
    # logger.info("NSD_TEST: " + str(nsd_root.get("ns-instance-id", "Not found")))
    ns_instance_id = str(nsd_root.get("ns-instance-id", "Not found"))
    name = str(nsd_root.get("ns", {}).get("name", "Not found"))
    parent_service_id = str(nsd_root.get("ns", {}).get("id", "Not found"))
    vendor = str(nsd_root.get("ns", {}).get("vendor", "Not found"))
    version = str(nsd_root.get("ns", {}).get("descriptor-version", "Not found"))
    location_id = nsd_root.get("ns", {}).get("location-id", "Not found")
    default_service_id = str(nsd_root.get("ns", {}).get("default-service-id", "Not found"))
    default_nfrouter_mode = str(nsd_root.get("ns", {}).get("default-nfrouter-mode", "Not found"))
    default_interpod_mode = str(nsd_root.get("ns", {}).get("default-interpod-mode", "Not found"))
    
    # Get all application-functions and forwarding_graphs
    app_functions = nsd_root.get("ns", {}).get("application-functions", [])
    forwarding_graphs = nsd_root.get("ns", {}).get("forwarding_graphs", [])
    infra_nfs = nsd_root.get("ns", {}).get("infra-nfs", [])
    network_functions = nsd_root.get("ns", {}).get("network-functions", [])

    logger.info("----")

    # ARVR DEMO PARTITIONING
    # Classify application-functions by type
    src_apps = []  # UE/source apps -> site0
    ran_apps = []  # RAN apps -> site1
    edge_apps = []  # Edge apps -> site2
    
    for app in app_functions:
        instance_id = app.get("instance-id", "")
        domain = app.get("domain", "")
        is_ue = app.get("is-ue", False)
        
        if instance_id == "src" or (is_ue and domain == "external"):
            src_apps.append(app)
        elif instance_id == "ran" or (is_ue and domain == "internal"):
            ran_apps.append(app)
        elif instance_id == "edge" or domain == "external":
            edge_apps.append(app)
    
    # logger.info("src_apps: " + str(src_apps))
    # logger.info("ran_apps: " + str(ran_apps))
    # logger.info("edge_apps: " + str(edge_apps))

    # LINEAR HEURISTIC PARTITIONING
    for domain in range(0, domains):

        logger.info("RUN START: " + str(domain))

        # SITE0 - UE/SOURCE DOMAIN
        site_id0 = resources[0].get("site-resources", [])[0].get("site-id-ref", "site0") if len(resources) > 0 and len(resources[0].get("site-resources", [])) > 0 else "site0"
        
        # logger.info("site_id0: " + str(site_id0))
        # logger.info("src_apps for site0: " + str(src_apps))

        # SITE1 - RAN DOMAIN
        site_id1 = resources[1].get("site-resources", [])[0].get("site-id-ref", "site1") if len(resources) > 1 and len(resources[1].get("site-resources", [])) > 0 else "site1"
        
        # logger.info("site_id1: " + str(site_id1))
        # logger.info("ran_apps for site1: " + str(ran_apps))

        # SITE2 - EDGE DOMAIN
        site_id2 = resources[2].get("site-resources", [])[0].get("site-id-ref", "site2") if len(resources) > 2 and len(resources[2].get("site-resources", [])) > 0 else "site2"
        
        # logger.info("site_id2: " + str(site_id2))
        # logger.info("edge_apps for site2: " + str(edge_apps))

        logger.info("RUN END: " + str(domain))
    
    logger.info("----")

    # SERVICEGEN
    partitions = []
    
    # Generate partition for site0 (UE/source domain)
    partition_0 = {
        "lnsd": {
            "ns-instance-id": ns_instance_id,
            "ns": {
                "name": name + "1",
                "id": parent_service_id,
                "vendor": vendor,
                "descriptor-version": version,
                "site-id": site_id0,
                "location-id": location_id,
                "default-service-id": default_service_id,
                "default-nfrouter-mode": default_nfrouter_mode,
                "default-interpod-mode": default_interpod_mode,
                "infra-nfs": [],
                "network-functions": [],
                "application-functions": src_apps if src_apps else [],
                "site-connections": [],
                "forwarding_graphs": []
            }
        }
    }
    partitions.append(partition_0)
    
    # Build site-connection for site1 referencing edge apps on site2
    site1_site_connections = []
    if edge_apps:
        edge_app_refs = []
        for edge_app in edge_apps:
            edge_ref = {
                "instance-id": edge_app.get("instance-id", ""),
                "static-nfids": edge_app.get("static-nfids", [])
            }
            edge_app_refs.append(edge_ref)
        site1_site_connections.append({
            "id": site_id2,
            "application-functions": edge_app_refs,
            "network-functions": []
        })
    
    # Generate partition for site1 (RAN domain)
    partition_1 = {
        "lnsd": {
            "ns-instance-id": ns_instance_id,
            "ns": {
                "name": name + "1",
                "id": parent_service_id,
                "vendor": vendor,
                "descriptor-version": version,
                "site-id": site_id1,
                "location-id": location_id,
                "default-service-id": default_service_id,
                "default-nfrouter-mode": default_nfrouter_mode,
                "default-interpod-mode": default_interpod_mode,
                "infra-nfs": [],
                "network-functions": [],
                "application-functions": ran_apps if ran_apps else [],
                "site-connections": site1_site_connections,
                "forwarding_graphs": forwarding_graphs if forwarding_graphs else []
            }
        }
    }
    partitions.append(partition_1)
    
    # Build site-connection for site2 referencing ran apps on site1
    site2_site_connections = []
    if ran_apps:
        ran_app_refs = []
        for ran_app in ran_apps:
            ran_ref = {
                "instance-id": ran_app.get("instance-id", ""),
                "static-nfids": ran_app.get("static-nfids", []),
                "static-ips": ran_app.get("static-ips", []),
                "is-ue": ran_app.get("is-ue", False)
            }
            ran_app_refs.append(ran_ref)
        site2_site_connections.append({
            "id": site_id1,
            "application-functions": ran_app_refs,
            "network-functions": []
        })
    
    # Build forwarding_graphs for site2 with src:0 instead of ran:0
    site2_forwarding_graphs = []
    for fg in forwarding_graphs:
        fg_copy = {
            "graph-name": fg.get("graph-name", ""),
            "direction": fg.get("direction", ""),
            "links": []
        }
        for link in fg.get("links", []):
            link_copy = {
                "id": link.get("id", ""),
                "connection-points": []
            }
            for cp in link.get("connection-points", []):
                if_id_ref = cp.get("if-id-ref", "")
                # Replace ran:0 with src:0 for site2
                if "ran:" in if_id_ref:
                    if_id_ref = if_id_ref.replace("ran:", "src:")
                link_copy["connection-points"].append({"if-id-ref": if_id_ref})
            fg_copy["links"].append(link_copy)
        site2_forwarding_graphs.append(fg_copy)
    
    # Generate partition for site2 (edge domain)
    partition_2 = {
        "lnsd": {
            "ns-instance-id": "55667788",
            "ns": {
                "name": name + "1",
                "id": "ccccdddd",
                "vendor": vendor,
                "descriptor-version": version,
                "site-id": site_id2,
                "location-id": location_id,
                "default-service-id": default_service_id,
                "default-nfrouter-mode": default_nfrouter_mode,
                "default-interpod-mode": default_interpod_mode,
                "infra-nfs": [],
                "network-functions": [],
                "site-connections": site2_site_connections,
                "application-functions": edge_apps if edge_apps else [],
                "forwarding_graphs": site2_forwarding_graphs if site2_forwarding_graphs else []
            }
        }
    }
    partitions.append(partition_2)
    
    logger.info("Generated " + str(len(partitions)) + " partitions")
    
    return partitions
