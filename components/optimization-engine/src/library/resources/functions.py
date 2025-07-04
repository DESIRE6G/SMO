# Service Catalog Module Interface
# Anestis Dalgkitsis | v2

import logging
import requests
import yaml
import library.config as config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
    
def service_catalog_snapshot():
    try:
        url = f'http://{config.SERVICE_CATALOG_HOST}:{config.SERVICE_CATALOG_PORT}/retrieve/'
        headers = {'accept': 'application/json'}
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() 

        payload = response.json()
        

        logger.info(f"Received from SC -> {functions_info}")
        return functions_info["file_content"] if "file_content" in functions_info else None
    except requests.RequestException as e:
        logger.error(f"Error making request to service catalog: {e}")
        return None
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML response: {e}")
        return None