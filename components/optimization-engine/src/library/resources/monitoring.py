# Mock Infrastructure Monitoring for development
import time
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_resources(merged_functions, site_resources):
    logger.info("Starting resource check with site_resources content: %s", site_resources)

    # Handle both formats: single site dict or wrapped in site-resources
    if isinstance(site_resources, dict):
        if "site-resources" in site_resources:
            # Original format: wrapped in site-resources
            site_data = site_resources["site-resources"][0]
        else:
            # New format: single site dictionary
            site_data = site_resources
    else:
        logger.error("site_resources is not a dictionary: %s", type(site_resources))
        return False

    # Calculate total required resources from all functions.
    total_required_vcpu = 0
    total_required_ram = 0
    total_required_storage = 0

    # logger.info("Merged functions content: %s", merged_functions)
    
    # Handle merged_functions as a dictionary where each key maps to a function dict
    for key, func_info in merged_functions.items():
        # logger.info("Processing key: %s with function info: %s", key, func_info)
        if not isinstance(func_info, dict):
            logger.info("Warning: Expected %s to be a dict, got %s. Skipping.", key, type(func_info))
            continue
        
        # Extract resource requirements from the function info
        total_required_vcpu += int(func_info.get("cpu", 0))
        total_required_ram += int(func_info.get("ram", 0))
        total_required_storage += int(func_info.get("storage", 0))

    try:
        # logger.info("Using site data: %s", site_data)
        
        # Handle the nested structure where site_data contains site IDs as keys
        if len(site_data) == 1:
            # Get the first (and likely only) site
            site_id = list(site_data.keys())[0]
            actual_site_data = site_data[site_id]
        else:
            # If multiple sites, use the first one for now
            site_id = list(site_data.keys())[0]
            actual_site_data = site_data[site_id]
        
        logger.info("Using actual site data for %s: %s", site_id, actual_site_data)
        
        # Validate required fields in actual_site_data
        required_fields = ["cpu", "mem", "storage"]
        for field in required_fields:
            if field not in actual_site_data:
                logger.error("Required field '%s' not found in site data. Available fields: %s", field, list(actual_site_data.keys()))
                return False
            if not isinstance(actual_site_data[field], (int, float)):
                logger.error("Field '%s' is not a number: %s", field, type(actual_site_data[field]))
                return False

        total_available_vcpu = actual_site_data["cpu"]
        total_available_ram = actual_site_data["mem"]
        total_available_storage = actual_site_data["storage"]
    except Exception as e:
        logger.error("Error accessing site resources data: %s. Full site_resources: %s", str(e), site_resources)
        return False

    logger.info("Total required vCPU: %s", total_required_vcpu)
    logger.info("Total available vCPU: %s", total_available_vcpu)
    logger.info("Total required RAM: %s", total_required_ram)
    logger.info("Total available RAM: %s", total_available_ram)
    logger.info("Total required Storage: %s", total_required_storage)
    logger.info("Total available Storage: %s", total_available_storage)

    # Check if available resources cover the required resources.
    if (total_required_vcpu <= total_available_vcpu and
        total_required_ram <= total_available_ram and
        total_required_storage <= total_available_storage):
        return True
    else:
        return False