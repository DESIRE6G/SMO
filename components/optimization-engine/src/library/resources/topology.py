# Topology Module Interface
# Anestis Dalgkitsis | v3.1

import networkx as nx
import requests
import logging
import numpy
import subprocess
import json
import library.config as config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
    
def fetch_d6g_site_info(d6g_site):

    # Create an empty topology graph to be populated
    G = nx.Graph()

    # Check if d6g_site is a list
    if isinstance(d6g_site, list):
        try:
            site_data = []
            for sitelist_index in range(len(d6g_site)):
                url = f'http://{config.TOPOLOGY_MODULE_HOST}:{config.TOPOLOGY_MODULE_PORT}/nodes/{d6g_site[sitelist_index]}'
                headers = {'accept': 'application/json'}
                
                response = requests.get(url, headers=headers)
                response.raise_for_status()  # Raise an exception for bad status codes
                
                # Parse the JSON response into dictionary
                site_info = response.json()
                
                # Store the values in a dictionary for later processing
                site_data_instance = { "site-resources": [{
                    "site-id-ref": d6g_site[sitelist_index],
                    "site-available-vcpu": site_info.get('cpu', 0),
                    "site-available-ram": site_info.get('mem', 0),
                    "site-available-storage": site_info.get('storage', 0)
                },]}

                site_data.append(site_data_instance)
                
            logger.info(f"Successfully retrieved site info for {d6g_site}") # : {site_data}
            return G, len(d6g_site), site_data
            
        except requests.RequestException as e:
            logger.error(f"Error making request for site {d6g_site}: {e}")
            return None, None, None
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response for site {d6g_site}: {e}")
            return None, None, None
        except Exception as e:
            logger.error(f"Unexpected error getting site info for {d6g_site}: {e}")
            return None, None, None
    elif d6g_site:
        try:
            url = f'http://{config.TOPOLOGY_MODULE_HOST}:{config.TOPOLOGY_MODULE_PORT}/nodes/{d6g_site}'
            headers = {'accept': 'application/json'}
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            # Parse the JSON response into dictionary
            site_info = response.json()
            
            # Store the values in a dictionary for later processing
            site_data = { "site-resources": [{
                "site-id-ref": d6g_site,
                "site-available-vcpu": site_info.get('cpu', 0),
                "site-available-ram": site_info.get('mem', 0),
                "site-available-storage": site_info.get('storage', 0)
            },]}
            
            logger.info(f"Successfully retrieved site info for {d6g_site}: {site_data}")
            return G, 1, site_data
            
        except requests.RequestException as e:
            logger.error(f"Error making request for site {d6g_site}: {e}")
            return None, None, None
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response for site {d6g_site}: {e}")
            return None, None, None
        except Exception as e:
            logger.error(f"Unexpected error getting site info for {d6g_site}: {e}")
            return None, None, None

    return None, None, None