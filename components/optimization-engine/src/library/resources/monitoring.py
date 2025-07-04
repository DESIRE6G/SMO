# Mock Infrastructure Monitoring for development
import time
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_resources(merged_functions, site_resources):
    # TODO: THIS NEEDS TO BE UPDATED TO THE NEW merged_functions, site_resources FORMATS
    logger.info("Starting resource check with site_resources type: %s", type(site_resources))
    logger.info("site_resources content: %s", site_resources)

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

    logger.info("Merged functions content: %s", merged_functions)
    for key, func_list in merged_functions.items():
        logger.info("Processing key: %s with functions: %s", key, func_list)
        if not isinstance(func_list, list):
            logger.info("Warning: Expected %s to be a list, got %s. Skipping.", key, type(func_list))
            continue
        for func in func_list:
            if not isinstance(func, dict):
                logger.info("Warning: Expected function info to be dict, got %s. Skipping: %s", type(func), func)
                continue
            total_required_vcpu += int(func.get("nf-vcpu", 0))
            total_required_ram += int(func.get("nf-memory", 0))
            total_required_storage += int(func.get("nf-storage", 0))

    try:
        logger.info("Using site data: %s", site_data)
        
        # Validate required fields in site_data
        required_fields = ["site-available-vcpu", "site-available-ram", "site-available-storage"]
        for field in required_fields:
            if field not in site_data:
                logger.error("Required field '%s' not found in site data. Available fields: %s", field, list(site_data.keys()))
                return False
            if not isinstance(site_data[field], (int, float)):
                logger.error("Field '%s' is not a number: %s", field, type(site_data[field]))
                return False

        total_available_vcpu = site_data["site-available-vcpu"]
        total_available_ram = site_data["site-available-ram"]
        total_available_storage = site_data["site-available-storage"]
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