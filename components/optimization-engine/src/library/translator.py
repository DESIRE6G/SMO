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

def service2dict(service: bytes | str):
    data = ""
    if isinstance(service, bytes):
        data = service.decode('utf-8')
    elif isinstance(service, str):
        data = service
    try:
        data = base64.b64decode(data).decode('utf-8')
    except (binascii.Error, UnicodeDecodeError):
        logger.info("Data is not base64 encoded")
    if data == "":
        raise ValueError("service variable is not str or bytes type.")
    try:
        return json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    try:
        return yaml.safe_load(data)
    except (yaml.YAMLError, UnicodeDecodeError):
        pass
    raise ValueError("Data is not valid JSON or YAML format.")
    
def _extract_nsd(payload: dict) -> dict:
    # 1. Common wrappers used by different APIs/versions.
    for wrapper_key in ("lnsd", "local-nsd"):
        if wrapper_key in payload:
            payload = payload[wrapper_key]
            break

    # 2. Some payloads add an extra 'ns' layer (your example does).
    if "ns" in payload:
        payload = payload["ns"]

    return payload


def request2graph(service):
    try:
        service = service2dict(service)          # caller-supplied helper
        # logger.info("Service content: %s", service)

        # --------- Locate the NSD we need to parse ---------- #
        nsd = _extract_nsd(service)

        G = nx.Graph()
        function_info = {}

        # ---------- Network-function nodes ------------------ #
        for nf in nsd.get("network-functions", []):
            node_id = nf.get("nf-instance-id")
            if not node_id:
                logger.info("Network function missing 'nf-instance-id': %s", nf)
                continue

            G.add_node(node_id, **nf)
            function_info[node_id] = {
                "cpu":     nf.get("nf-vcpu"),
                "ram":     nf.get("nf-memory"),
                "storage": nf.get("nf-storage"),
                "type":    "network",
            }

        # ---------- Application-function nodes -------------- #
        for af in nsd.get("application-functions", []):
            node_id = af.get("af-instance-id")
            if not node_id:
                logger.info("Application function missing 'af-instance-id': %s", af)
                continue

            G.add_node(node_id, **af)
            function_info[node_id] = {
                "cpu":     af.get("af-vcpu"),
                "ram":     af.get("af-memory"),
                "storage": af.get("af-storage"),
                "type":    "application",
            }

        # ------------- Edges from forwarding graphs --------- #
        for fg in nsd.get("forwarding_graphs", []):
            for link in fg.get("links", []):
                cps = link.get("connection-points", [])
                if len(cps) < 2:
                    logger.info("Link '%s' has fewer than 2 CPs.", link.get("id", "unknown"))
                    continue

                node1_id = (cps[0].get("member-if-id-ref", "").split(":") or [None])[0]
                node2_id = (cps[1].get("member-if-id-ref", "").split(":") or [None])[0]

                if node1_id in G and node2_id in G:
                    G.add_edge(node1_id, node2_id, link_id=link.get("id"))
                # else:
                #     logger.info(
                #         "Skipping edge for link '%s': '%s' or '%s' not found.",
                #         link.get("id", "unknown"), node1_id, node2_id
                #     )

        # ------------- Decorations (everything else) -------- #
        decorations = {
            k: v for k, v in nsd.items()
            if k not in ("network-functions", "application-functions", "forwarding_graphs")
        }

        # logger.info("function_info collected: %s", function_info)
        return G, decorations, function_info

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