# Optimization Engine Module Core Flow 
# Anestis Dalgkitsis | v6.0

# Python Modules
import json
import logging
import yaml
# Local Modules
import library.translator as translator

# Demo Selector Pool
import library.selector_pool.random_selection as random_selection

# Demo Model Pool
import library.model_pool.partition as partition
import library.model_pool.autologic as autologic
import library.model_pool.greedysplit as greedysplit

# Demo Data
import library.resources.topology as topology
import library.resources.monitoring as monitoring

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model Pool Demo Configuration
algorithms = {
    "partition.py": {"enabled": False},
    "autologic.py": {"enabled": True},
    "greedysplit.py": {"enabled": True},
}

# Model Selector Demo Configuration
selectors = {
    "spinwheel.py (Default)": {"enabled": True},
    "intelligence.py": {"enabled": False},
}

def optimization_engine(data):

    # TOPOLOGY SNAPSHOT
    topologyGraph, domains, site_resources = topology.topology_snapshot()
    if topologyGraph is None:
        logger.info("❌ Error: Failed to fetch topology, check configuration.")
        error_payload = {"Error": "Failed to fetch topology, check configuration."}
        return json.dumps(error_payload).encode('utf-8')
    else:
        logger.info("Topology snapshot loaded successfully from Topology module.")
    if domains is None:
        logger.info("❌ Error: Failed to fetch domains, check configuration.")
        error_payload = {"Error": "Failed to fetch domains, check configuration."}
        return json.dumps(error_payload).encode('utf-8')
    
    # TRANSLATION (External to Internal)
    # Translate NSD to internal structure
    serviceGraph, decorations, function_info = translator.request2graph(data)
    if serviceGraph is None:
        logger.info("❌ Error: Failed to translate service request, check syntax.")
        error_payload = {"Error": "Failed to translate service request, check syntax."}
        return json.dumps(error_payload).encode('utf-8')
    else:
        logger.info("💡 Service request translated to internal graph.")

    # RESOURCE AVAILABILITY CHECK

    # Check for resource availability on all registered Desire6G sites
    if monitoring.check_resources(function_info, site_resources):
        logger.info("💡 There are enough resources to host the service.")
    else:
        logger.info("❌ Failed: Not enough resources to host the service.")
        error_payload = {"Failed": "Not enough resources to host the service."}
        return json.dumps(error_payload).encode('utf-8')
    
    # Check if only one site (partitioning not possible)
    logger.info("Checking if there is only one D6G node in the site...")
    if domains == 1:
        logger.info("✉️ Success: There is only one D6G node in the site. Forwarding request to the Service Orchestrator.")
        if isinstance(data, bytes): # Decode bytes to string if data is in bytes format
            data = data.decode('utf-8')
        return json.dumps(data).encode('utf-8')

    # OPTIMIZATION PIPELINE
    
    # Route autoselector
    pick = random_selection.spinwheel(algorithms)
    logger.info("Model Selector: " + str(pick))

    # Route to selected Model from the Model Pool
    subgraphs = []
    try:
        if pick == "partition.py (Default)":
            subgraphs = partition.partition(serviceGraph, topologyGraph, domains)
        elif pick == "autologic.py":
            subgraphs = autologic.autologic(serviceGraph, topologyGraph, domains)
        elif pick == "greedysplit.py":
            subgraphs = greedysplit.greedysplit(serviceGraph, topologyGraph, domains)
        else:
            logger.info("❌ Error: Unknown model selected, check Model Pool configuration.")
            error_payload = "Error: Unknown model selected, check Model Pool configuration."
            return json.dumps(error_payload).encode('utf-8')
    except Exception as e:
        logger.error("Internal error occurred in selected model: " + str(e))
        error_payload = {"Error": "Internal error occurred in selected model: " + str(e)}
        return json.dumps(error_payload).encode('utf-8')
    
    # Verify if partitioning was successfull
    if subgraphs is None or subgraphs == []:
        logger.info("❌ Error: Unknown partitioning error.")
    elif subgraphs == -1:
        logger.info("Service partitioning has failed, not enough resources to allocate.")
        error_payload = {"Failed": "Service partitioning has failed, not enough resources to allocate."}
        return json.dumps(error_payload).encode('utf-8')
    else:
        logger.info("✅ Partitioning executed successfully. Count: " + str(len(subgraphs)) + " subgraphs: " + str(subgraphs))

    # TRANSLATION (Internal to External)
    # Translate internal structure to YAML for SO
    encoded_subgraphs = []
    for subgraph in subgraphs:
        encoded_subgraph = translator.graph2request(subgraph, data)
        if encoded_subgraph is None:
            logger.info("❌ Error: Failed to encode subgraph, check syntax: " + str(subgraph))
            error_payload = {"Error": "Failed to encode subgraph, check syntax: " + str(subgraph)}
            return json.dumps(error_payload).encode('utf-8')
        else:
            encoded_subgraphs.append(encoded_subgraph)
            logger.info("💡 Subgraph encoded successfully.")
    logger.info("Combined subgraphs encoded successfully.")

    # RETURN OPTIMIZED REQUEST
    # Combine partitioned requests for each site
    try:
        combined_response = []
        for domain in range(0, domains-1):
            combined_response.append({f"s{domain+1}e": encoded_subgraphs[domain], "site_id": f"SITEID{domain+1}"})
        logger.info("💡 Subgraphs combined successfully.")
    except Exception as e:
        logger.exception("❌ Error: An error occurred while combining the response: %s", e)
        error_payload = {"Error": "An error occurred while combining the response: " + str(e)}
        return json.dumps(error_payload).encode('utf-8')

    # Return optimized service request
    logger.info("✉️ Optimized request dispatched to the Service Orchestrator.")
    return json.dumps(combined_response).encode('utf-8')