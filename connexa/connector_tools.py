import json
import logging
import sys
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

# Imports from within the 'connexa' package
from .connexa_api import call_api, find_connector_path_by_id
from .config_manager import initialize_config as cm_initialize_config, \
                            BUSINESS_NAME as CM_BUSINESS_NAME, \
                            API_TOKEN as CM_API_TOKEN # For checking if config is loaded in test

# Configure basic logging for standalone testing
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )


class ConnectorAction(str, Enum):
    GET = "get"
    DELETE = "delete"
    POST = "post"
    PUT = "put"


class ManageConnectorArgs(BaseModel):
    action: ConnectorAction = Field(..., description="The action to perform on the connector (get, delete, post, put).")
    network_id: Optional[str] = Field(None, description="The ID of the network the connector belongs to (required for post, and if connector_id is not globally unique for get/put/delete).")
    connector_id: Optional[str] = Field(None, description="The ID of the connector (required for get, delete, put if not using find_by_id logic).")
    payload: Optional[Dict[str, Any]] = Field(None, description="The data payload for post or put actions.")
    # Example: find_globally: bool = Field(False, description="If true, attempt to find connector across all networks for GET/PUT/DELETE if network_id is not provided.")


# This function will be decorated with @tool in server.py
def manage_connector(args: ManageConnectorArgs) -> Dict[str, Any]:
    """
    Manages OpenVPN Connexa connectors.
    Supports GET, DELETE, POST, and PUT actions.
    Connector paths are typically /api/v1/networks/{network_id}/connectors/{connector_id}.
    """
    action = args.action
    network_id = args.network_id
    connector_id = args.connector_id
    payload = args.payload

    api_path_segment = "connectors" # This is a simplified base segment

    # Determine the correct API path
    # For POST, network_id is essential to know where to create the connector.
    # For GET/PUT/DELETE, if connector_id is globally unique and the API supports a direct path,
    # network_id might be optional. Otherwise, network_id is needed.
    # The `find_connector_path_by_id` can be used if connector_id is known but network_id is not.

    path_to_use: Optional[str] = None
    actual_connector_id_for_path: Optional[str] = connector_id

    if action == ConnectorAction.POST:
        if not network_id:
            raise ValueError("network_id is required for POST (create) action.")
        if not payload:
            raise ValueError("payload is required for POST (create) action.")
        # Path for creating a connector within a specific network
        path_to_use = f"/api/v1/networks/{network_id}/{api_path_segment}"
        # connector_id is not used in the path for POST, it's part of the payload or auto-generated
        actual_connector_id_for_path = None
    elif action in [ConnectorAction.GET, ConnectorAction.PUT, ConnectorAction.DELETE]:
        if action == ConnectorAction.GET and not connector_id:
            # If action is GET and no connector_id is provided, list all connectors
            logger.info("Listing all connectors across all networks.")
            all_connectors = []
            # Call API to get all networks
            networks_response = call_api(action="get", path="/api/v1/networks")
            if networks_response.get("status") == 200 and networks_response.get("data") and networks_response["data"].get("content"):
                for network in networks_response["data"]["content"]:
                    # Assuming network object includes a 'connectors' list
                    if network.get("connectors"):
                        all_connectors.extend(network["connectors"])
            
            # Return the list of all connectors
            return {"status": 200, "data": all_connectors, "message": "Successfully retrieved all connectors."}

        # If connector_id is provided or action is not GET, proceed with single connector logic
        if not connector_id:
            raise ValueError(f"connector_id is required for {action.value} action when not listing all.")
        
        # Option 1: If network_id is provided, construct path directly
        if network_id:
            path_to_use = f"/api/v1/networks/{network_id}/{api_path_segment}/{connector_id}"
        # Option 2: If network_id is NOT provided, try to find the connector's full path
        # This assumes connector_id might be unique enough to find, or you have a specific strategy.
        # For simplicity, we'll assume direct path if network_id is missing, but this might need find_connector_path_by_id
        else:
            # Attempt to find the connector if network_id is not given
            # This is a more robust approach for GET/PUT/DELETE if connector_id is known but not its network
            logger.info(f"Network ID not provided for {action.value} on connector {connector_id}. Attempting to find connector path.")
            found_info = find_connector_path_by_id(connector_id)
            if found_info and found_info.get("path"):
                path_to_use = found_info["path"]
                # actual_connector_id_for_path is already set to connector_id, which is part of found_info["path"]
                logger.info(f"Found connector path: {path_to_use}")
            else:
                # Fallback or error if connector cannot be located without network_id
                # Using a simplified path as a last resort, which might not work for all APIs
                # path_to_use = f"/api/v1/{api_path_segment}/{connector_id}"
                # logger.warning(f"Could not find connector {connector_id} across networks. API call might fail.")
                raise ValueError(f"Could not determine path for connector {connector_id}. Network ID not provided and connector not found globally.")

        if action in [ConnectorAction.PUT] and not payload: # Payload needed for PUT
            raise ValueError("payload is required for PUT (update) action.")
    else:
        raise ValueError(f"Unsupported action: {action}")

    if not path_to_use:
        # This case should ideally be caught by earlier checks
        raise ValueError("Could not determine API path for the operation.")

    # Make the API call
    # For POST and PUT, 'value' is the payload. 'id' in call_api is for path substitution like {id}.
    # If path_to_use already contains the final ID (like from find_connector_path_by_id),
    # then actual_connector_id_for_path might be None for call_api's 'id' param.
    # However, call_api's 'id' param is for substituting "{id}" in the path string.
    # Our path_to_use is already resolved.
    
    # If path_to_use is like "/api/v1/networks/net1/connectors/conn1", call_api's id param is not needed.
    # If path_to_use was "/api/v1/networks/net1/connectors/{id}", then call_api's id=connector_id would be used.
    # Since we construct full paths, call_api's 'id' param is likely not needed here.

    api_response = call_api(
        action=action.value,
        path=path_to_use, # The fully resolved path
        id=None, # Set to None as path_to_use should be complete
        value=payload if action in [ConnectorAction.POST, ConnectorAction.PUT] else None
    )

    # Handle specific responses, e.g., 204 No Content for DELETE
    if action == ConnectorAction.DELETE and api_response.get("status") == 204:
        return {"status": "success", "message": f"Connector {connector_id} deleted successfully.", "details": api_response}
    
    return api_response


class CreateConnectorArgs(BaseModel):
    name: str = Field(..., description="The name for the new connector.")
    network_id: str = Field(..., description="The ID of the network where the connector will be created.")
    vpn_region_id: str = Field(..., description="The ID of the VPN region for the connector.")
    description: Optional[str] = Field(None, description="An optional description for the connector.")


def create_network_connector(args: CreateConnectorArgs) -> Dict[str, Any]:
    """
    Creates a new network connector with the specified details.
    This tool uses the correct payload structure based on swagger.json.
    """
    logger.info(f"Attempting to create connector '{args.name}' in network '{args.network_id}' for region '{args.vpn_region_id}'.")

    payload: Dict[str, Any] = {
        "name": args.name,
        "vpnRegionId": args.vpn_region_id
    }
    if args.description:
        payload["description"] = args.description

    api_path = f"/api/v1/networks/connectors?networkId={args.network_id}"

    try:
        api_response = call_api(
            action="post",
            path=api_path,
            value=payload
        )
        # Log success or failure based on status
        if api_response.get("status") == 201 or (isinstance(api_response.get("data"), dict) and api_response.get("data", {}).get("id")):
            logger.info(f"Successfully created connector. Response: {json.dumps(api_response, indent=2)}")
        else:
            logger.error(f"Failed to create connector. Path: {api_path}, Payload: {json.dumps(payload)}, Response: {json.dumps(api_response, indent=2)}")
        return api_response
    except Exception as e:
        logger.error(f"Exception during connector creation: {e}. Path: {api_path}, Payload: {json.dumps(payload)}", exc_info=True)
        # Re-raise or return a structured error
        return {"status": "error", "message": f"Exception during connector creation: {str(e)}", "details": str(e)}


if __name__ == "__main__":
    logger.info("--- Testing connector_tools.py ---")

    # Initialize configuration - crucial for call_api to work
    if not cm_initialize_config():
        logger.error("Failed to initialize configuration. API calls in tests will likely fail.")
        # sys.exit(1) # Optionally exit if config is critical for tests

    if not CM_API_TOKEN or not CM_BUSINESS_NAME:
        logger.warning("API Token or Business Name is not loaded. Live API calls will fail.")

    # --- Test Data ---
    # Replace with actual IDs from your OpenVPN Connexa environment for live testing
    test_network_id = "net-xxxxxxxxxxxxxxxxx"  # Replace with a real Network ID
    test_connector_id_to_create = "test-connector-py" # Name for new connector
    # Payload for creating a connector (structure depends on your API)
    # This is a guess based on typical API patterns. Consult swagger.json.
    # The API might expect 'name', 'vpnRegionIds', 'networkItemType', 'networkItemId', etc.
    # From swagger: POST /api/v1/networks/{networkId}/connectors
    # Request body: ConnectorPostRequest (name, description, internetAccess, networkItemType, networkItemId, ipServices)
    create_payload = {
        "name": test_connector_id_to_create,
        "description": "Test connector created via Python MCP tool",
        "networkItemType": "HOST", # Example, adjust as needed. Could be NETWORK, HOST, VPN_REGION
        # "networkItemId": "some-host-id-or-network-id", # Required if type is HOST or NETWORK
        "vpnRegionIds": ["reg-xxxxxxxxxxxxxxxxx"], # Replace with actual VPN Region ID(s)
        "internetAccess": "LOCAL" # Or "BLOCKED" or "GLOBAL_INTERNET"
    }
    
    created_connector_id: Optional[str] = None

    # --- Test POST (Create Connector) ---
    logger.info(f"\n--- Test POST: Create Connector in Network {test_network_id} ---")
    if CM_API_TOKEN and CM_BUSINESS_NAME and test_network_id != "net-xxxxxxxxxxxxxxxxx":
        try:
            post_args = ManageConnectorArgs(action=ConnectorAction.POST, network_id=test_network_id, connector_id=None, payload=create_payload)
            create_result = manage_connector(post_args)
            logger.info(f"Create result: {json.dumps(create_result, indent=2)}")
            if create_result.get("status") == 200 or create_result.get("status") == 201: # 201 Created is common
                if isinstance(create_result.get("data"), dict):
                    created_connector_id = create_result["data"].get("id")
                    logger.info(f"Connector created successfully. ID: {created_connector_id}")
                else:
                    logger.warning("Connector creation reported success, but ID not found in response data.")
            else:
                logger.error(f"Connector creation failed. Status: {create_result.get('status')}, Message: {create_result.get('message')}")
        except Exception as e:
            logger.error(f"Exception during POST test: {e}", exc_info=True)
    else:
        logger.warning("Skipping POST test: API token/business name missing or test_network_id not set.")

    # --- Test GET (List Connectors in Network - if create was successful or use existing) ---
    # This specific tool is for managing a single connector, not listing all.
    # To list, you'd typically call_api directly: call_api("get", f"/api/v1/networks/{test_network_id}/connectors")
    
    # --- Test GET (Specific Connector - if one was created or use existing) ---
    test_existing_connector_id = created_connector_id or "conn-xxxxxxxxxxxxxxxxx" # Use created one or a known existing one
    logger.info(f"\n--- Test GET: Get Connector {test_existing_connector_id} (Network ID: {test_network_id if test_network_id != 'net-xxxxxxxxxxxxxxxxx' else 'not specified, will try to find'}) ---")
    if CM_API_TOKEN and CM_BUSINESS_NAME and test_existing_connector_id != "conn-xxxxxxxxxxxxxxxxx":
        try:
            # If network_id is known:
            # get_args = ManageConnectorArgs(action=ConnectorAction.GET, network_id=test_network_id, connector_id=test_existing_connector_id, payload=None)
            # If network_id is not known (will use find_connector_path_by_id):
            get_args = ManageConnectorArgs(action=ConnectorAction.GET, network_id=None, connector_id=test_existing_connector_id, payload=None)
            get_result = manage_connector(get_args)
            logger.info(f"Get result: {json.dumps(get_result, indent=2)}")
        except Exception as e:
            logger.error(f"Exception during GET test: {e}", exc_info=True)
    else:
        logger.warning("Skipping GET test: API token/business name missing or test_existing_connector_id not set.")

    # --- Test PUT (Update Connector - if one was created or use existing) ---
    if created_connector_id and CM_API_TOKEN and CM_BUSINESS_NAME: # Only if we successfully created one
        logger.info(f"\n--- Test PUT: Update Connector {created_connector_id} ---")
        update_payload = {"description": "Updated description for test connector."}
        try:
            # Assuming we know the network_id from creation, or find_connector_path_by_id will be used if network_id=None
            put_args = ManageConnectorArgs(action=ConnectorAction.PUT, network_id=None, connector_id=created_connector_id, payload=update_payload)
            put_result = manage_connector(put_args)
            logger.info(f"Put result: {json.dumps(put_result, indent=2)}")
        except Exception as e:
            logger.error(f"Exception during PUT test: {e}", exc_info=True)
    else:
        logger.warning(f"Skipping PUT test: No connector was created in this session or API token/business name missing. (created_connector_id: {created_connector_id})")
        
    # --- Test DELETE (Delete Connector - if one was created) ---
    if created_connector_id and CM_API_TOKEN and CM_BUSINESS_NAME: # Only if we successfully created one
        logger.info(f"\n--- Test DELETE: Delete Connector {created_connector_id} ---")
        try:
            # Assuming we know the network_id from creation, or find_connector_path_by_id will be used if network_id=None
            delete_args = ManageConnectorArgs(action=ConnectorAction.DELETE, network_id=None, connector_id=created_connector_id, payload=None)
            delete_result = manage_connector(delete_args)
            logger.info(f"Delete result: {json.dumps(delete_result, indent=2)}")
        except Exception as e:
            logger.error(f"Exception during DELETE test: {e}", exc_info=True)
    else:
        logger.warning(f"Skipping DELETE test: No connector was created in this session or API token/business name missing. (created_connector_id: {created_connector_id})")

    logger.info("\n--- End of connector_tools.py tests ---")
    logger.info("To run these tests: python -m connexa_openvpn_mcp_server.connexa.connector_tools")
