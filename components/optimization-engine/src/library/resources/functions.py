# Mock Demo2 Service Catalog for development
import time
import logging
import requests
import yaml
import json
import ProcessingSystems.config as config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_service_catalog_info(funtions_graph_name = "apps", data = None):
    try:
        url = f'http://{config.SERVICE_CATALOG_HOST}:{config.SERVICE_CATALOG_PORT}/retrieve/{funtions_graph_name}'
        # headers = {'accept': 'application/json'}
        headers = {'accept': 'application/x-yaml'}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Parse the JSON response into dictionary
        # functions_info = response.json()
        data = yaml.safe_load(response.text)
        json_data = json.dumps(data, indent=2)
        functions_info = json_data
        
        logger.info(f"Application Functions received from SC.") #  -> {functions_info}
        return functions_info
    except requests.RequestException as e:
        logger.error(f"Error making request to service catalog: {e}")
        return None
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML response: {e}")
        return None