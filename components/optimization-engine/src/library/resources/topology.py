# Topology Module Interface
# Anestis Dalgkitsis | v3

import networkx as nx
import requests
import logging
import json
import library.config as config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
    
def topology_snapshot():

    G = nx.Graph()
    site_data = {}
    sites = 0

    try:
        url = f'http://{config.TOPOLOGY_MODULE_HOST}:{config.TOPOLOGY_MODULE_PORT}/nodes/'
        headers = {'accept': 'application/json'}

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() 

        payload = response.json()
        nodes = payload.get("nodes", [])

        for node in nodes:
            site_id = node.get("site_id")
            if not site_id: # skip malformed entries
                continue

            site_data[site_id] = {
                "cpu": node.get("cpu"),
                "mem": node.get("mem"),
                "storage": node.get("storage"),
                "iml_endpoint": node.get("iml_endpoint"),
            }

            G.add_node(site_id, **site_data[site_id])

        sites = len(site_data)
        logger.info("💡 Retrieved %d sites from topology module", sites)
        return G, sites, site_data
    
    # Error handling
    except requests.RequestException as e:
        logger.error("❌ Error calling topology module: %s", e)
    except json.JSONDecodeError as e:
        logger.error("❌ Malformed JSON returned by topology module: %s", e)
    except Exception as e:
        logger.error("❌ Unexpected error while building topology snapshot: %s", e)

    return None, -1, {}