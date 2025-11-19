# Two-way JSON/YAML to NetworkX translation
# Anestis Dalgkitsis | v3.1

import networkx as nx
import yaml
import json
import logging
import base64
import binascii

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# def service2dict(service: bytes | str):
#     data = ""
#     if isinstance(service, bytes):
#         data = service.decode('utf-8')
#     elif isinstance(service, str):
#         data = service
#     try:
#         data = base64.b64decode(data).decode('utf-8')
#     except (binascii.Error, UnicodeDecodeError):
#         logger.info("Data is not base64 encoded")
#     if data == "":
#         raise ValueError("service variable is not str or bytes type.")
#     try:
#         return json.loads(data)
#     except (json.JSONDecodeError, UnicodeDecodeError):
#         pass
#     try:
#         return yaml.safe_load(data)
#     except (yaml.YAMLError, UnicodeDecodeError):
#         pass
#     raise ValueError("Data is not valid JSON or YAML format.")
    
# def _extract_nsd(payload: dict) -> dict:
#     # 1. Common wrappers used by different APIs/versions.
#     for wrapper_key in ("lnsd", "local-nsd"):
#         if wrapper_key in payload:
#             payload = payload[wrapper_key]
#             break

#     # 2. Some payloads add an extra 'ns' layer (your example does).
#     if "ns" in payload:
#         payload = payload["ns"]

#     return payload


def request2graph(service, functions):
    try:
        # service = service2dict(service)          # caller-supplied helper
        # logger.info("Service content: %s", service)

        # --------- Locate the NSD we need to parse ---------- #
        # nsd = _extract_nsd(service)

        # UPDATED FUNCTION 

        if isinstance(service, bytes):
            service = json.loads(service.decode('utf-8'))
        
        # Extract lnsd.
        logger.info("Service content: %s", service)
        nsd = service.get("lnsd", service)
        
        # Create an empty undirected graph.
        G = nx.Graph()

        # Extract nodes from network-functions and application-functions.
        network_functions = nsd.get("network-functions", [])
        application_functions = nsd.get("application-functions", [])

        # Function info Lookups.
        # additional_nf = {
        #     nf.get("nf-instance-id"): nf 
        #     for nf in functions.get("network-functions", []) if nf.get("nf-instance-id")
        # }
        # additional_af = {
        #     af.get("af-instance-id"): af 
        #     for af in functions.get("application-functions", []) if af.get("af-instance-id")
        # }

        # Add network function nodes.
        for nf in network_functions:
            node_id = nf.get("nf-instance-id")
            if node_id:
                # node_data = nf.copy()
                # if node_id in additional_nf:
                #     node_data = merge_missing(node_data, additional_nf[node_id])
                # G.add_node(node_id, **node_data)
                G.add_node(node_id, **nf)
                logger.info("nf node added in graph:': %s", node_id)
                # logger.info("nf node added in graph:': %s: %s", node_id, node_data)
            else:
                logger.info("Network function missing 'nf-instance-id': %s", nf)
        
        # Add application function nodes.
        for af in application_functions:
            node_id = af.get("af-instance-id")
            if node_id:
                # node_data = af.copy()
                # if node_id in additional_af:
                #     node_data = merge_missing(node_data, additional_af[node_id])
                # G.add_node(node_id, **node_data)
                G.add_node(node_id, **af)
                logger.info("af node added in graph:': %s", node_id)
                # logger.info("af node added in graph:': %s: %s", node_id, node_data)
            else:
                logger.info("Application function missing 'af-instance-id': %s", af)
        
        # Process forwarding_graphs to add edges between nodes.
        forwarding_graphs = nsd.get("forwarding_graphs", [])
        for fg in forwarding_graphs:
            links = fg.get("links", [])
            for link in links:
                connection_points = link.get("connection-points", [])
                if len(connection_points) < 2:
                    logger.info("Link '%s' has less than 2 connection points.", link.get("link-id", "unknown"))
                    continue
                # Extract the first two connection points.
                cp1 = connection_points[0]
                cp2 = connection_points[1]
                # Extract node identifiers by splitting on ':'.
                ref1 = cp1.get("member-if-id-ref", "")
                ref2 = cp2.get("member-if-id-ref", "")
                node1_id = ref1.split(":")[0] if ref1 else None
                node2_id = ref2.split(":")[0] if ref2 else None
                
                # Check if both nodes exist in the graph before adding the edge.
                if node1_id in G.nodes and node2_id in G.nodes:
                    G.add_edge(node1_id, node2_id, link_id=link.get("link-id"))
                else:
                    logger.info("Skipping edge for link '%s': Node '%s' or '%s' not found in functions.", link.get("link-id", "unknown"), node1_id, node2_id)
        
        # Store the rest of the information as decorations.
        decorations = {key: value for key, value in nsd.items() if key not in ["network-functions", "application-functions", "forwarding_graphs"]}

        return G, decorations

    except Exception as e:
        logger.exception("Error in request2graph: %s", e)
        return None, None, None
    
def graph2request(graph, data={}):
    nsd = None
    try:
        # If data is bytes, decode and convert it to a dictionary.
        if isinstance(data, bytes):
            try:
                # Assuming the bytes object contains JSON data:
                data = json.loads(data.decode("utf-8"))
            except json.JSONDecodeError as json_err:
                logger.info("Data provided is not valid JSON: %s", json_err)
                return None

        # Check if graph has descriptor-version "1.0"
        if isinstance(graph, dict):
            descriptor_version = graph.get("lnsd", {}).get("ns", {}).get("descriptor-version", "")
            if descriptor_version == "1.0":
                logger.info("Descriptor version is 1.0.")
                return graph

        if "local-nsd" in data:
            service = data.copy()
        else:
            service = {"local-nsd": {}}
            service["local-nsd"].update(data)

        nsd = service["local-nsd"]

        # Initialize lists for network-functions and application-functions.
        nsd["network-functions"] = []
        nsd["application-functions"] = []

        # Process each node in the graph.
        for node, attrs in graph.nodes(data=True):
            if "nf-instance-id" in attrs:
                # Append the full attribute dict for network functions.
                nsd["network-functions"].append(attrs)
            elif "af-instance-id" in attrs:
                # Append the full attribute dict for application functions.
                nsd["application-functions"].append(attrs)
            else:
                logger.info("Node '%s' does not have a valid function identifier.", node)

        # Process graph edges into a single forwarding graph.
        links = []
        for u, v, edge_attrs in graph.edges(data=True):
            # Use the provided link_id or generate a default one.
            link_id = edge_attrs.get("link_id", f"{u}-{v}")
            # Build a link with two connection points.
            link = {
                "link-id": link_id,
                "connection-points": [
                    {"member-connection-point-index": 1, "member-if-id-ref": u},
                    {"member-connection-point-index": 2, "member-if-id-ref": v}
                ]
            }
            links.append(link)

        # Create a default forwarding graph segment.
        nsd["forwarding_graphs"] = [{
            "member-graph-index": 1,
            "graph-name": "default",
            "links": links,
            "site-delay-budget": "0ms"
        }]

        return service

    except Exception as e:
        logger.info("Error in graph2request: %s", e)
        if nsd is not None  :
            logger.info("nsd content: %s", nsd)
        return None

#  Helper Function

# Merge extra details into base dictionary only if keys are missing.
def merge_missing(base, extra):
    for key, value in extra.items():
        if key not in base:
            base[key] = value
    return base