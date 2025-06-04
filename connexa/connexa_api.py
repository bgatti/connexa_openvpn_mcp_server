import json
import os
import sys # Added for logging
import logging # Added for logging
from typing import Optional, Dict, Any, List

import requests

# config_manager.py is now in the same 'connexa' package.
try:
    from .config_manager import get_api_token as cm_get_api_token, \
                                initialize_config as cm_initialize_config, \
                                BUSINESS_NAME as CM_BUSINESS_NAME, \
                                API_TOKEN as CM_API_TOKEN, \
                                CLIENT_ID as CM_CLIENT_ID
except ImportError:
    # This fallback might be needed if the module is run in a way that '.' doesn't work
    # or if there's an issue within config_manager itself.
    print("Failed to import config_manager using relative import '.config_manager'. Ensure structure is correct and config_manager.py is in the 'connexa' directory.", flush=True)
    # Define placeholders if import fails to allow module to load for inspection, but it will be non-functional.
    def cm_get_api_token(): return None
    CM_BUSINESS_NAME = None
    CM_API_TOKEN = None
    CM_CLIENT_ID = None


# Configure basic logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers(): # Avoid adding multiple handlers if already configured
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )

# api.json is now expected to be in the parent directory of 'connexa'
# (i.e., in connexa_openvpn_mcp_server/)
API_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api.json')

# --- Functions moved from server.py ---
def get_connexa_base_url() -> str:
    """
    Returns the base URL for the OpenVPN Connexa API.
    The BUSINESS_NAME is sourced from config_manager.
    """
    if not CM_API_TOKEN and not CM_CLIENT_ID: # Heuristic to check if init ran
        logger.warning("config_manager might not be initialized when calling get_connexa_base_url early.")
    
    if not CM_BUSINESS_NAME:
        logger.error("OVPN_BUSINESS_NAME is not configured in config_manager. Cannot determine base URL.")
        return "https://your_business_name_here.api.openvpn.com" # Placeholder
    return f"https://{CM_BUSINESS_NAME}.api.openvpn.com"

def get_connexa_auth_token() -> str | None:
    """
    Retrieves the current API authentication token.
    This token is managed (fetched and refreshed) by config_manager.
    """
    token = cm_get_api_token()
    if not token:
        logger.error("Failed to retrieve Connexa auth token via config_manager.")
    return token

# --- Functions moved from api_tools.py ---
def schema(api_group: str) -> List[Dict[str, Any]]:
    """
    Retrieves the API entries for a given API group from api.json.

    Args:
        api_group (str): The name of the API group (e.g., "User", "Network").

    Returns:
        List[Dict[str, Any]]: A list of API entries for the specified group, or an empty list if not found.
    """
    if not os.path.exists(API_JSON_PATH):
        logger.error(f"Error: {API_JSON_PATH} not found.")
        return []
    
    try:
        with open(API_JSON_PATH, 'r') as f:
            all_apis: Dict[str, List[Dict[str, Any]]] = json.load(f)
        
        return all_apis.get(api_group, [])
    except json.JSONDecodeError:
        logger.error(f"Error: Could not decode JSON from {API_JSON_PATH}.")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred while reading {API_JSON_PATH}: {e}")
        return []

def call_api(action: str, path: str, id: Optional[str] = None, value: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Calls an API endpoint.

    Args:
        action (str): The HTTP action (e.g., "get", "post", "put", "delete").
        path (str): The API path, potentially with an {id} placeholder.
        id (Optional[str]): The ID to substitute into the path if present. Defaults to None.
        value (Optional[Dict[str, Any]]): The JSON payload for "post" or "put" requests. Defaults to None.

    Returns:
        Dict[str, Any]: A dictionary containing the API response status and data, or an error message.
    """
    processed_path = path

    if "{id}" in path:
        if id:
            processed_path = path.replace("{id}", id)
        else:
            error_message = "Error: Path expects an {id} but no id was provided."
            logger.error(error_message)
            return {"status": "error", "message": error_message}

    action = action.lower()
    if action in ["post", "put"]:
        if value is None:
            error_message = f"Error: Action '{action}' requires a value/payload, but none was provided."
            logger.error(error_message)
            return {"status": "error", "message": error_message}
    
    base_url = get_connexa_base_url()
    auth_token = get_connexa_auth_token()

    if not base_url or base_url == "https://your_business_name_here.api.openvpn.com": # Check for placeholder
        error_message = "Error: API base URL is not configured."
        logger.error(error_message)
        return {"status": "error", "message": error_message}
    
    if not auth_token:
        error_message = "Error: API authentication token is not available."
        logger.error(error_message)
        return {"status": "error", "message": error_message}

    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Accept": "application/json", 
    }
    if action in ["post", "put"]:
        headers["Content-Type"] = "application/json"

    full_url = f"{base_url}{processed_path}"
    response_data: Optional[Any] = None
    
    logger.info(f"Attempting API call (from connexa_api.py): Action: {action.upper()}, URL: {full_url}")
    if value:
        logger.info(f"  Payload: {json.dumps(value)}")

    try:
        http_response: Optional[requests.Response] = None
        if action == "get":
            http_response = requests.get(full_url, headers=headers)
        elif action == "post":
            http_response = requests.post(full_url, json=value, headers=headers)
        elif action == "put":
            http_response = requests.put(full_url, json=value, headers=headers)
        elif action == "delete":
            http_response = requests.delete(full_url, headers=headers)
        else:
            error_message = f"Error: Unsupported action '{action}'."
            logger.error(error_message)
            return {"status": "error", "message": error_message}

        http_response.raise_for_status()
        
        if http_response.content:
            try:
                response_data = http_response.json()
            except json.JSONDecodeError:
                response_data = http_response.text 
        else:
            response_data = None

        return {"status": http_response.status_code, "data": response_data}

    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP error occurred: {e} - {e.response.status_code} - {e.response.text}"
        logger.error(error_message)
        return {"status": "error", "http_status_code": e.response.status_code, "message": error_message, "details": e.response.text}
    except requests.exceptions.RequestException as e:
        error_message = f"Request failed: {e}"
        logger.error(error_message)
        return {"status": "error", "message": error_message}
    except Exception as e: 
        error_message = f"An unexpected error occurred during API call: {e}"
        logger.error(error_message)
        return {"status": "error", "message": error_message}

def find_connector_path_by_id(connector_id_to_find: str) -> Optional[Dict[str, str]]:
    """
    Finds a connector by its ID by searching through all networks and their connectors.

    Args:
        connector_id_to_find (str): The ID of the connector to find.

    Returns:
        Optional[Dict[str, str]]: A dictionary containing 'network_id', 'connector_id', 
                                   and 'path' if found, otherwise None.
                                   Example: {"network_id": "net-xxxx", 
                                             "connector_id": "conn-yyyy", 
                                             "path": "/api/v1/networks/net-xxxx/connectors/conn-yyyy"}
    """
    logger.info(f"Attempting to find connector with ID: {connector_id_to_find}")

    # 1. Get all networks
    networks_response = call_api(action="get", path="/api/v1/networks")
    if networks_response.get("status") != 200 or not isinstance(networks_response.get("data"), list):
        logger.error(f"Failed to retrieve networks or unexpected format. Response: {networks_response}")
        return None
    
    networks: List[Dict[str, Any]] = networks_response["data"]
    if not networks:
        logger.info("No networks found.")
        return None

    logger.info(f"Found {len(networks)} network(s). Iterating to find connectors...")

    for network in networks:
        network_id = network.get("id")
        network_name = network.get("name", "N/A") # For logging
        if not network_id:
            logger.warning(f"Network found without an ID. Skipping. Network data: {network}")
            continue

        logger.info(f"Checking network '{network_name}' (ID: {network_id}) for connectors...")
        
        # 2. Get connectors for the current network
        # Assuming the API path for network connectors is /api/v1/networks/{network_id}/connectors
        connectors_path = f"/api/v1/networks/{network_id}/connectors"
        connectors_response = call_api(action="get", path=connectors_path) # No ID needed for listing

        if connectors_response.get("status") != 200 or not isinstance(connectors_response.get("data"), list):
            logger.warning(f"Failed to retrieve connectors for network ID {network_id} or unexpected format. Response: {connectors_response}")
            continue # Try next network

        network_connectors: List[Dict[str, Any]] = connectors_response["data"]
        if not network_connectors:
            logger.info(f"No connectors found in network ID {network_id}.")
            continue

        logger.info(f"Found {len(network_connectors)} connector(s) in network ID {network_id}. Searching for target ID...")
        for connector in network_connectors:
            current_connector_id = connector.get("id")
            # The actual field name for connector ID might vary, e.g., 'connectorId', 'id', 'uuid'
            # Assuming 'id' for now based on typical API design.
            if current_connector_id == connector_id_to_find:
                found_path = f"/api/v1/networks/{network_id}/connectors/{current_connector_id}"
                logger.info(f"Connector FOUND: ID {connector_id_to_find} in Network ID {network_id}. Path: {found_path}")
                return {
                    "network_id": network_id,
                    "connector_id": current_connector_id,
                    "path": found_path,
                    "connector_details": connector # Include full connector details
                }
            
    logger.info(f"Connector with ID {connector_id_to_find} NOT FOUND in any network.")
    return None

if __name__ == '__main__':
    # This main block is for basic testing of connexa_api.py.
    # For this to work, config_manager must be initialized.
    # This typically happens in server.py. If running this standalone,
    # you might need to call cm_initialize_config() first.
    
    logger.info("--- Testing connexa/connexa_api.py ---")
    
    # Attempt to initialize config if not already (basic check)
    if not CM_API_TOKEN and not CM_CLIENT_ID:
        logger.info("Attempting to initialize config_manager from connexa_api.py test block...")
        try:
            # This import is tricky for standalone execution.
            # It assumes connexa_openvpn_mcp_server is in sys.path
            from . import config_manager # Try to get the module itself
            if not config_manager.cm_initialize_config(): # Call its init
                 logger.warning("Standalone test: Failed to initialize shared configuration.")
            else:
                 logger.info("Standalone test: config_manager initialized.")
                 # Re-fetch potentially updated config values if init was successful
                 CM_BUSINESS_NAME = config_manager.BUSINESS_NAME
                 # cm_get_api_token will now use the initialized state
        except ImportError:
            logger.error("Standalone test: Could not import config_manager to initialize for test.")
        except Exception as e_cfg:
            logger.error(f"Standalone test: Error initializing config_manager: {e_cfg}")


    logger.info("\n--- Testing schema function (from connexa_api.py) ---")
    user_api_info = schema("User")
    if user_api_info:
        logger.info("User APIs:")
        for api_entry in user_api_info:
            logger.info(f"  Path: {api_entry['api']}, Actions: {api_entry['actions']}, Hint: {api_entry.get('hint', 'N/A')}")
    else:
        logger.info("User group not found or api.json is missing/invalid.")

    logger.info("\n--- Testing call_api function (from connexa_api.py, will attempt live calls if config is set) ---")
    
    logger.info("\nTest call_api with path expecting {id} but no id provided (error case):")
    logger.info(json.dumps(call_api(action="get", path="/api/v1/users/{id}"), indent=2))

    logger.info("\nTest call_api with POST action without value (error case):")
    logger.info(json.dumps(call_api(action="post", path="/api/v1/users"), indent=2))
    
    # Example of a GET call (uncomment to test if your config is set up)
    # logger.info("\nTest GET /api/v1/users (requires valid config):")
    # result = call_api(action="get", path="/api/v1/users")
    # logger.info(json.dumps(result, indent=2))

    logger.info("\n--- Testing find_connector_path_by_id (requires valid config and existing connector) ---")
    # Replace 'your_target_connector_id_here' with an actual connector ID from your OpenVPN Connexa setup
    # target_connector_id_to_test = "your_target_connector_id_here" 
    # if target_connector_id_to_test != "your_target_connector_id_here":
    #     logger.info(f"Attempting to find connector: {target_connector_id_to_test}")
    #     connector_info = find_connector_path_by_id(target_connector_id_to_test)
    #     if connector_info:
    #         logger.info(f"Found connector: {json.dumps(connector_info, indent=2)}")
    #     else:
    #         logger.info(f"Connector {target_connector_id_to_test} not found or error occurred.")
    # else:
    #     logger.info("Skipping find_connector_path_by_id test as no target_connector_id_to_test was provided.")
    
    logger.info("\n--- End of connexa_api.py tests ---")
