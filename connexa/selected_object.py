# connexa/selected_object.py
import os
import sys # Added for logging
import logging # Added for logging
import json # Added for json.loads
from typing import Any, Dict, List, Optional, Tuple, Callable, Union

# Import necessary functions from connexa_api
from .connexa_api import call_api # Import call_api
from .dynamic_network import get_network_command_definitions
from .dynamic_connector import get_connector_command_definitions
# Defer import of update_dynamic_tools to break circular dependency
# from .dynamic_tool_manager import update_dynamic_tools 

# Configure basic logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers(): # Avoid adding multiple handlers if already configured
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr # Or a file, depending on desired output
    )

# Cache for swagger.json content
_CACHED_SWAGGER_CONTENT: Optional[Dict[str, Any]] = None # Global cache for swagger content

def _get_swagger_content() -> Dict[str, Any]:
    """Loads and caches swagger.json content. Returns an empty dict on failure."""
    global _CACHED_SWAGGER_CONTENT
    if _CACHED_SWAGGER_CONTENT is None:
        # Initialize to an empty dict; will be populated if loading is successful
        loaded_data: Dict[str, Any] = {} 
        swagger_path = os.path.join(os.path.dirname(__file__), 'swagger.json')
        try:
            with open(swagger_path, 'r') as f:
                loaded_data = json.load(f) # Populate with loaded data
        except Exception as e:
            logger.error(f"Failed to load swagger.json from '{swagger_path}': {e}")
            # loaded_data remains {} if an error occurs
        _CACHED_SWAGGER_CONTENT = loaded_data # Assign to the cache
    
    # By this point, _CACHED_SWAGGER_CONTENT is guaranteed to be a Dict[str, Any]
    # because it's either populated from the file or set to {}
    return _CACHED_SWAGGER_CONTENT

def get_schema_for_object_type(object_type: str, request_type: str = "update") -> Optional[Dict[str, Any]]:
    """
    Retrieves the JSON schema for a given object type from swagger.json.
    request_type can be 'update' or 'create'.
    """
    swagger = _get_swagger_content() # Use the new cached loader
    if not swagger or "components" not in swagger or "schemas" not in swagger: # Check if swagger is empty due to load failure
        logger.error(f"Swagger content malformed, missing components/schemas, or failed to load. Swagger content: {swagger}")
        return None

    schemas = swagger["components"]["schemas"]
    schema_name = None

    if object_type == "network":
        schema_name = "NetworkUpdateRequest" if request_type == "update" else "NetworkCreateRequest"
    elif object_type == "connector": 
        schema_name = "NetworkConnectorRequest" 
    # Add other object types here
    # elif object_type == "user":
    #     schema_name = "UserUpdateRequest" if request_type == "update" else "UserCreateRequest"
    # elif object_type == "usergroup":
    #     schema_name = "UserGroupRequest"

    if schema_name and schema_name in schemas:
        return schemas[schema_name]
    
    logger.warning(f"Schema not found in swagger.json for object_type='{object_type}', request_type='{request_type}' (derived schema_name='{schema_name}')")
    return None


class SelectedObject:
    """
    Represents the currently selected object in the MCP server.
    This object's state will determine which dynamic tools are available.
    """
    def __init__(self):
        self.object_type: Optional[str] = None
        self.object_id: Optional[str] = None
        self.object_name: Optional[str] = None
        self.details: Dict[str, Any] = {}
        # No need to initialize ConnexaAPI instance here, use call_api function directly
        self._listeners: List[Callable[[Optional[str]], None]] = [] # Listeners for selection changes

    def register_listener(self, listener: Callable[[Optional[str]], None]):
        """Register a callback function to be notified of selection changes."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def _notify_listeners(self):
        """Notify all registered listeners about the selection change."""
        for listener in self._listeners:
            try:
                listener(self.object_type) # Pass the new object type
            except Exception as e:
                logger.error(f"Error notifying listener {listener}: {e}", exc_info=True) # Use logger

    def select(self, object_type: str, object_id: Optional[str], object_name: Optional[str], details: Dict[str, Any]):
        logger.info(f"SelectedObject.select called with: type='{object_type}', id='{object_id}', name='{object_name}'")
        logger.info(f"SelectedObject.select storing details: {json.dumps(details, indent=2)}") # Log the details being stored
        self.object_type = object_type
        self.object_id = object_id
        self.object_name = object_name
        self.details = details
        # print(f"SelectedObject: Selected {object_type} - {object_name} (ID: {object_id})") # Replaced by logger
        logger.info(f"SelectedObject: Successfully selected {object_type} - {object_name} (ID: {object_id})")
        # dynamic_tool_manager and update_dynamic_tools are being refactored/removed.
        # The new approach uses generic tools that internally adapt to the selected object.
        self._notify_listeners()

    def clear(self):
        self.object_type = None
        self.object_id = None
        self.object_name = None
        self.details = {}
        print("SelectedObject: Cleared selection.")
        # dynamic_tool_manager and update_dynamic_tools are being refactored/removed.
        self._notify_listeners()

    def get_selected_object_info(self) -> Dict[str, Any]:
        return {
            "type": self.object_type,
            "id": self.object_id,
            "name": self.object_name,
            "details": self.details,
        }

    def get_available_commands(self) -> List[Dict[str, Any]]:
        """
        Returns a list of available commands for the currently selected object type,
        or global creation commands if no object is selected.
        """
        commands = []

        # Global "Create" commands if nothing is selected
        if not self.object_type:
            commands.extend([
                {
                    "name": "create_network",
                    "description": "Create a new Network.",
                    "tool_name": "create_network_tool", # Assumes tool is registered with this name
                    "requires_args": True # Indicates that the tool needs arguments
                },
                {
                    "name": "create_host",
                    "description": "Create a new Host.",
                    "tool_name": "create_host_tool",
                    "requires_args": True
                },
                {
                    "name": "create_user_group",
                    "description": "Create a new User Group.",
                    "tool_name": "create_user_group_tool",
                    "requires_args": True
                },
                {
                    "name": "create_dns_record",
                    "description": "Create a new DNS Record.",
                    "tool_name": "create_dns_record_tool",
                    "requires_args": True
                },
                {
                    "name": "create_access_group",
                    "description": "Create a new Access Group.",
                    "tool_name": "create_access_group_tool",
                    "requires_args": True
                },
                {
                    "name": "create_location_context_policy",
                    "description": "Create a new Location Context Policy.",
                    "tool_name": "create_location_context_tool",
                    "requires_args": True
                },
                {
                    "name": "create_device_posture_policy",
                    "description": "Create a new Device Posture Policy.",
                    "tool_name": "create_device_posture_tool",
                    "requires_args": True
                }
                # Note: create_user is not added here as it's typically part of user_tools.py
                # and might have a different flow (e.g. inviting vs direct creation).
                # The existing create_user tool in user_tools.py can be used.
            ])
            return commands

        # Commands for when an object IS selected
        if not self.object_id: # Should not happen if object_type is set, but as a safeguard
            return commands
            
        # Common commands for selected objects
        commands.append({
            "name": "update",
            "description": f"Initiate update for the selected {self.object_type} '{self.object_name}'. Provides current data and schema.",
            "requires_args": False, # This command itself doesn't take args, it starts a flow
            "special_handling": "update_flow" # Indicates special handling by act_on_selected_object
        })
        
        # Define delete paths more comprehensively
        # TODO: Ensure these paths are accurate and cover host connectors too.
        # Connector delete path might depend on whether it's a network or host connector.
        # The current find_connector_path_by_id in connexa_api.py might help resolve this.
        # For now, this is a simplified map.
        delete_path_map = {
            "network": "/api/v1/networks/{id}",
            "connector": "/api/v1/networks/connectors/{id}", # Defaulting to network connector path
            "user": "/api/v1/users/{id}",
            "usergroup": "/api/v1/user-groups/{id}",
            "host": "/api/v1/hosts/{id}",
            "dns-record": "/api/v1/dns-records/{id}",
            "access-group": "/api/v1/access-groups/{id}",
            "location-context": "/api/v1/location-contexts/{id}",
            "device-posture": "/api/v1/device-postures/{id}",
            # Device delete needs userId as a query param: /api/v1/devices/{id}?userId={userId}
            # This simple map won't handle that directly without more logic.
        }
        if self.object_type in delete_path_map and self.object_type != "device": # Device delete is special
            commands.append({
                "name": "delete",
                "description": f"Delete the selected {self.object_type} '{self.object_name}'. This action is permanent.",
                "method": "delete", # HTTP method
                "path_template": delete_path_map[self.object_type], # Path template for call_api
                "requires_args": False # Delete usually doesn't take a request body
            })
        elif self.object_type == "device" and self.details.get("userId"):
             # Special handling for device delete if userId is available in details
            commands.append({
                "name": "delete_device", # More specific name
                "description": f"Delete the selected device '{self.object_name}'. This action is permanent.",
                "tool_name": "delete_device_record", # Assumes a tool like this exists or will be created
                                                     # from existing MCP server tools (it does)
                "requires_args": True, # Will need device_id (from self.object_id) and user_id
                "pre_filled_args": {
                    "device_id": self.object_id,
                    "user_id": self.details.get("userId")
                }
            })


        # Object-specific "get" commands (from dynamic_*.py) and "Create" sub-object commands
        if self.object_type == "network":
            if self.object_id and self.object_name and self.details:
                network_commands = get_network_command_definitions(
                    network_id=self.object_id,
                    network_name=self.object_name,
                    network_details=self.details
                )
                commands.extend(network_commands)
                # Add command to create a connector within this network
                commands.append({
                    "name": "create_network_connector",
                    "description": f"Create a new connector in the selected network '{self.object_name}'.",
                    "tool_name": "create_network_connector_tool",
                    "requires_args": True, # name, vpn_region_id, etc.
                    "pre_filled_args": {"network_id": self.object_id}
                })
        
        elif self.object_type == "connector":
            # Connectors have their own specific commands (profile, etc.)
            if self.object_id and self.object_name and self.details:
                connector_commands = get_connector_command_definitions(
                    connector_id=self.object_id,
                    connector_name=self.object_name,
                    connector_details=self.details
                )
                commands.extend(connector_commands)
                # Note: The delete path for a connector might need to know if it's a host or network connector.
                # The generic delete_path_map uses /api/v1/networks/connectors/{id}.
                # If it's a host connector, this would be wrong.
                # This might require enhancing the delete command definition or how it's processed.
                # For now, relying on find_connector_path_by_id if manage_connector tool is used for delete.
        
        elif self.object_type == "host":
            # Add command to create a connector within this host
            commands.append({
                "name": "create_host_connector",
                "description": f"Create a new connector for the selected host '{self.object_name}'.",
                "tool_name": "create_host_connector_tool",
                "requires_args": True, # name, vpn_region_id, etc.
                "pre_filled_args": {"host_id": self.object_id}
            })
            # Potentially add other host-specific commands if a dynamic_host.py existed

        elif self.object_type == "user":
            # Add command to create a device for this user
            commands.append({
                "name": "create_device_for_user",
                "description": f"Create a new device for the selected user '{self.object_name}'.",
                "tool_name": "create_device_tool",
                "requires_args": True, # name, description, clientUUID
                "pre_filled_args": {"user_id": self.object_id}
            })
            # Potentially add other user-specific commands (e.g., from a dynamic_user.py)
            # The existing user_tools.py already provides get_user, create_user, update_user, delete_user.
            # We might want to integrate them here or ensure they are discoverable.
            # For example, the 'delete' command for a user is already covered by the generic delete_path_map.

        # Fallback for other types, or if more specific commands are needed.
        # This is where one might load commands from other dynamic_*.py modules.
        # For example, if self.object_type == "usergroup":
        #   group_commands = get_usergroup_command_definitions(...)
        #   commands.extend(group_commands)

        return commands

# Global instance of the selected object. This will be imported by other modules.
CURRENT_SELECTED_OBJECT = SelectedObject()


def act_on_selected_object(command_name: str, command_args: Optional[Dict[str, Any]] = None) -> Union[str, Dict[str, Any]]:
    """
    Performs an action (command) on the currently selected object.
    Available commands depend on the selected object's type.
    Use the 'list_available_commands' command to see options.

    Args:
        command_name (str): The name of the command to execute.
        command_args (Optional[Dict[str, Any]]): Arguments for the command, if any.

    Returns:
        Union[str, Dict[str, Any]]: Result of the command, or an error message/update guidance.
    """
    if not CURRENT_SELECTED_OBJECT.object_type or not CURRENT_SELECTED_OBJECT.object_id:
        return "Error: No object selected. Use 'select_object_tool' first."

    if command_name == "list_available_commands":
        cmds = CURRENT_SELECTED_OBJECT.get_available_commands()
        return {
            "message": f"Available commands for selected {CURRENT_SELECTED_OBJECT.object_type} '{CURRENT_SELECTED_OBJECT.object_name}':",
            "commands": cmds
        }

    available_commands = CURRENT_SELECTED_OBJECT.get_available_commands()
    command_def = next((cmd for cmd in available_commands if cmd["name"] == command_name), None)

    if not command_def:
        return f"Error: Command '{command_name}' is not available for the selected {CURRENT_SELECTED_OBJECT.object_type}."

    # Handle special 'update' flow
    if command_def.get("special_handling") == "update_flow":
        schema = get_schema_for_object_type(CURRENT_SELECTED_OBJECT.object_type, "update")
        if not schema:
            return f"Error: Could not retrieve update schema for {CURRENT_SELECTED_OBJECT.object_type}."
        return {
            "message": f"To update the selected {CURRENT_SELECTED_OBJECT.object_type} '{CURRENT_SELECTED_OBJECT.object_name}', "
                       f"provide the modified payload to the 'complete_update_selected' tool.",
            "current_payload": CURRENT_SELECTED_OBJECT.details,
            "update_schema": schema
        }

    # Standard command execution via call_api
    api_method = command_def.get("method")
    api_path_template = command_def.get("path_template")

    if not api_method or not api_path_template:
        return f"Error: Command '{command_name}' is not correctly defined (missing method or path)."

    api_path = api_path_template.format(id=CURRENT_SELECTED_OBJECT.object_id)
    
    payload = None
    query_params = None

    if command_args:
        if command_def.get("payload_schema_ref"): # If command expects a body based on a schema
            # Here, command_args should conform to the schema referenced by payload_schema_ref
            # For simplicity, assume command_args is the payload if payload_schema_ref exists
            payload = command_args
        elif command_def.get("params_for_call_api"): # If command args are for query params
            query_params = {k: v for k, v in command_args.items() if k in command_def["params_for_call_api"]}


    try:
        response = call_api(action=api_method, path=api_path, value=payload, params=query_params)
        
        # After successful DELETE, clear selection
        if api_method.lower() == "delete" and response.get("status", 0) >= 200 and response.get("status", 0) < 300 :
            object_name_deleted = CURRENT_SELECTED_OBJECT.object_name
            CURRENT_SELECTED_OBJECT.clear()
            return f"Successfully deleted {object_name_deleted}. Selection cleared. API Response: {response}"
            
        return response # Return the full API response dictionary
    except Exception as e:
        logger.error(f"Error executing command '{command_name}' for {CURRENT_SELECTED_OBJECT.object_type} '{CURRENT_SELECTED_OBJECT.object_name}': {e}", exc_info=True)
        return f"Error during command execution: {str(e)}"


def complete_update_selected(updated_payload: Dict[str, Any]) -> str:
    """
    Completes the update process for the currently selected object
    using the provided payload.

    Args:
        updated_payload (Dict[str, Any]): The new data for the object.

    Returns:
        str: A message indicating success or failure of the update.
    """
    if not CURRENT_SELECTED_OBJECT.object_type or not CURRENT_SELECTED_OBJECT.object_id:
        return "Error: No object selected to update. Use 'select_object_tool' and then 'act_on_selected_object' with command 'update'."

    object_type = CURRENT_SELECTED_OBJECT.object_type
    object_id = CURRENT_SELECTED_OBJECT.object_id
    object_name = CURRENT_SELECTED_OBJECT.object_name # For messages

    update_path_map = {
        "network": f"/api/v1/networks/{object_id}",
        "connector": f"/api/v1/networks/connectors/{object_id}",
        # "user": f"/api/v1/users/{object_id}",
        # "usergroup": f"/api/v1/user-groups/{object_id}",
    }

    if object_type not in update_path_map:
        return f"Error: Update functionality not defined for object type '{object_type}'."

    api_path = update_path_map[object_type]

    try:
        response = call_api(action="put", path=api_path, value=updated_payload)

        if isinstance(response, dict) and response.get("status", 0) >= 200 and response.get("status", 0) < 300:
            # Successfully updated. Re-select the object to refresh details.
            new_details = response.get("data", {})
            # The name might have changed if it was part of the payload
            new_name = new_details.get("name", object_name) if isinstance(new_details, dict) else object_name
            
            CURRENT_SELECTED_OBJECT.select(
                object_type=object_type,
                object_id=object_id, # ID should not change on update
                object_name=new_name,
                details=new_details if isinstance(new_details, dict) else {}
            )
            return f"Successfully updated {object_type} '{new_name}'. Details refreshed. API Response: {response}"
        else:
            return f"Failed to update {object_type} '{object_name}'. API Response: {response}"
    except Exception as e:
        logger.error(f"Error completing update for {object_type} '{object_name}': {e}", exc_info=True)
        return f"Error during update execution: {str(e)}"


def select_object_tool(object_type: str, name_search: Optional[str] = None, kwargs: Optional[str] = None) -> Dict[str, Any]:
    """
    Tool to select an object (e.g., Network, User, Group) by type and optional name search.

    Args:
        object_type (str): The type of object to select (e.g., "network", "user").
        name_search (Optional[str]): A search term to filter objects by name.
                                    If "Default", empty, or multiple matches, selects the default.
        kwargs (Optional[str]): A JSON string representing additional search parameters (e.g., '{"status": "connected"}').

    Returns:
        Tuple[List[str], str]: A list of matching object names and the name of the selected object.
                               Returns an error message if the type is unsupported or an API error occurs.
    """
    # Read CONNEXA_REGION inside the function so it can be patched for tests
    CONNEXA_REGION = os.getenv("CONNEXA_REGION", "us-west-1")
    logger.info(f"select_object_tool called with object_type='{object_type}', name_search='{name_search}', kwargs='{kwargs}', using CONNEXA_REGION='{CONNEXA_REGION}'")

    OBJECT_TYPE_CONFIG = {
        "network": {
            "path": "/api/v1/networks",
            "parent_type": None,
            "parent_id_param_name": None,
            "default_criteria_key": "region", # Field in the item to check against CONNEXA_REGION
            "id_field": "id",
            "name_field": "name"
        },
        "user": {
            "path": "/api/v1/users",
            "parent_type": None,
            "parent_id_param_name": None,
            "id_field": "id",
            "name_field": "username" # Users often use 'username' or 'email' as a primary display name
        },
        "usergroup": {
            "path": "/api/v1/user-groups",
            "parent_type": None,
            "parent_id_param_name": None,
            "id_field": "id",
            "name_field": "name"
        },
        "connector": { # Network Connectors
            "path": "/api/v1/networks/connectors",
            "parent_type": "network",
            "parent_id_param_name": "networkId", # Query parameter
            "id_field": "id",
            "name_field": "name"
        },
        "device": {
            "path": "/api/v1/devices",
            "parent_type": "user", # Optional parent for filtering
            "parent_id_param_name": "userId", # Query parameter
            "id_field": "id",
            "name_field": "name"
        },
        "host": {
            "path": "/api/v1/hosts",
            "parent_type": None,
            "parent_id_param_name": None,
            "id_field": "id",
            "name_field": "name"
        },
        "dns-record": {
            "path": "/api/v1/dns-records",
            "parent_type": None,
            "parent_id_param_name": None,
            "id_field": "id",
            "name_field": "domain"
        }
        # Add other types like 'access-group', 'location-context', etc. as needed
    }

    obj_type_lower = object_type.lower()
    if obj_type_lower not in OBJECT_TYPE_CONFIG:
        logger.warning(f"Unsupported object type: {object_type}. Clearing selection.")
        CURRENT_SELECTED_OBJECT.clear()
        supported_types = ", ".join(OBJECT_TYPE_CONFIG.keys())
        return {
            "status": "failure",
            "message": f"Unsupported object type: {object_type}. Supported types: {supported_types}.",
            "object_type": obj_type_lower,
            "search_matches": []
        }

    config = OBJECT_TYPE_CONFIG[obj_type_lower]
    api_path = config["path"]
    api_params: Dict[str, Any] = {} # For query parameters

    found_objects: List[Dict[str, Any]] = []
    selected_object_name_final = "None" # Renamed to avoid conflict
    default_object_name = "Default"
    default_object_id = None
    default_details: Dict[str, Any] = {}
    
    id_field = config["id_field"]
    name_field = config["name_field"]

    try:
        # Handle parent object dependency
        if config["parent_type"]:
            parent_type_expected = config["parent_type"]
            parent_id_param_name = config["parent_id_param_name"]
            if not CURRENT_SELECTED_OBJECT.object_type or \
               CURRENT_SELECTED_OBJECT.object_type.lower() != parent_type_expected or \
               not CURRENT_SELECTED_OBJECT.object_id:
                CURRENT_SELECTED_OBJECT.clear() # Clear selection if context is invalid for this search
                return {
                    "status": "failure",
                    "message": f"Must select a {parent_type_expected} before searching for a {obj_type_lower}.",
                    "object_type": obj_type_lower,
                    "search_matches": []
                }
            
            if parent_id_param_name: # Should always be true if parent_type is set
                 api_params[parent_id_param_name] = CURRENT_SELECTED_OBJECT.object_id
            logger.info(f"Searching for {obj_type_lower} under selected {parent_type_expected} ID: {CURRENT_SELECTED_OBJECT.object_id} using param {parent_id_param_name}")


        logger.info(f"Attempting to fetch {obj_type_lower}(s) using call_api with path='{api_path}' and params='{api_params}'...")
        api_response = call_api(action="get", path=api_path, params=api_params if api_params else None)
        logger.info(f"call_api response for {obj_type_lower}(s): {api_response}")

        if not isinstance(api_response, dict) or api_response.get("status") != 200:
            error_detail = f"API call failed or returned non-200 status. Full response: {api_response}"
            logger.error(f"Error fetching {obj_type_lower}(s): {error_detail}")
            # Do not clear selection here, as the previous selection might still be valid
            return {
                "status": "error",
                "message": f"Error fetching {obj_type_lower}(s): {api_response.get('message', 'Unknown API error')}. Details: {error_detail}",
                "object_type": obj_type_lower,
                "search_matches": []
            }

        response_data = api_response.get("data", {})
        items_list: List[Dict[str, Any]] = []
        if isinstance(response_data, dict) and isinstance(response_data.get("content"), list):
            items_list = response_data["content"]
            logger.info(f"Successfully fetched {len(items_list)} {obj_type_lower}(s) from 'data.content'.")
        elif isinstance(response_data, list): # For APIs that return a list directly in 'data' (e.g. /api/v1/regions)
            items_list = response_data
            logger.info(f"Successfully fetched {len(items_list)} {obj_type_lower}(s) directly from 'data'.")
        else:
            error_detail = f"API response data for {obj_type_lower}(s) is not a list or does not contain a 'content' list. Data type: {type(response_data)}. Full response: {api_response}"
            logger.error(f"Error fetching {obj_type_lower}(s): {error_detail}")
            return {
                "status": "error",
                "message": f"Error fetching {obj_type_lower}(s): Unexpected data format. Details: {error_detail}",
                "object_type": obj_type_lower,
                "search_matches": []
            }

        if not items_list:
            logger.warning(f"No {obj_type_lower}(s) found from API.")
            # Don't clear selection, just report no items of this type found
            return {
                "status": "not_found",
                "message": f"No {obj_type_lower}(s) available to select.",
                "object_type": obj_type_lower,
                "search_matches": [f"No {obj_type_lower}(s) found."] # Keep original list-like structure for this key if needed
            }

        # Determine default object
        if obj_type_lower == "network" and config.get("default_criteria_key"):
            default_criteria_key = config["default_criteria_key"]
            logger.info(f"Determining default {obj_type_lower} using criteria key '{default_criteria_key}' and CONNEXA_REGION: {CONNEXA_REGION}")
            default_candidates = [item for item in items_list if item.get(default_criteria_key) == CONNEXA_REGION]
            if default_candidates:
                default_details = default_candidates[0]
            elif items_list: # Fallback if no item in default region
                default_details = items_list[0]
        elif items_list: # General default: first item
             default_details = items_list[0]
        
        if default_details:
            default_object_name = default_details.get(name_field, f'Unknown Default {obj_type_lower.capitalize()}')
            default_object_id = default_details.get(id_field)
            logger.info(f"Default {obj_type_lower} determined: {default_object_name} (ID: {default_object_id})")
        else:
            logger.warning(f"No {obj_type_lower}(s) available to determine a default.")
            default_object_name = f"No {obj_type_lower.capitalize()}s Found"
            # default_object_id remains None, default_details remains empty

        filter_kwargs: Dict[str, Any] = {}
        if kwargs:
            try:
                filter_kwargs = json.loads(kwargs)
                if not isinstance(filter_kwargs, dict):
                    logger.warning(f"kwargs parameter was not a valid JSON object string: {kwargs}")
                    filter_kwargs = {}
            except json.JSONDecodeError:
                logger.warning(f"Could not decode kwargs JSON string: {kwargs}")
                filter_kwargs = {}

        logger.info(f"Starting {obj_type_lower} filtering. Total fetched: {len(items_list)}")
        logger.info(f"Filtering by name_search='{name_search}' and parsed filter_kwargs={filter_kwargs}")

        for item in items_list:
            item_name_str = str(item.get(name_field, "")).lower()
            name_match = True
            if name_search and name_search.lower() != "default":
                # Filter items by whether their name starts with the search term
                if not item_name_str.startswith(name_search.lower()):
                    name_match = False
            
            if name_match:
                match_all_kwargs = True
                for key, value in filter_kwargs.items():
                    item_value = item.get(key)
                    if item_value is None:
                        match_all_kwargs = False
                        break
                    if str(item_value).lower() != str(value).lower():
                        match_all_kwargs = False
                        break
                
                if match_all_kwargs:
                    logger.info(f"{obj_type_lower.capitalize()} matched filter criteria: {item.get(name_field, 'Unnamed')}")
                    found_objects.append(item)
        
        logger.info(f"Filtering complete. Found {len(found_objects)} {obj_type_lower}(s) after filtering.")

        if not name_search and not filter_kwargs:
            logger.info(f"No name_search or kwargs specified, using all fetched {obj_type_lower}(s) for potential selection.")
            found_objects = items_list
            logger.info(f"Found objects updated to all {obj_type_lower}(s). Count: {len(found_objects)}")

        found_object_names = [obj.get(name_field, "Unnamed") for obj in found_objects]
        logger.info(f"Names of found {obj_type_lower}(s): {found_object_names}")

        # --- Selection Logic ---
        selected_item_details = None
        
        # Try to find a specific item if name_search is provided and not "default"
        if name_search and name_search.lower() != "default":
            logger.info(f"Attempting to find specific {obj_type_lower} matching '{name_search}'. Filtered 'found_objects' count: {len(found_objects)}")
            # Check for exact match first within 'found_objects' (which are already 'startswith' filtered)
            for item_detail in found_objects:
                if str(item_detail.get(name_field, "")).lower() == name_search.lower():
                    selected_item_details = item_detail
                    logger.info(f"Exact match found for '{name_search}': {selected_item_details.get(name_field, 'Unnamed')}")
                    break
            
            if not selected_item_details and len(found_objects) == 1:
                # If no exact match, but 'startswith' filter yielded a unique result, use that.
                selected_item_details = found_objects[0]
                logger.info(f"Single unique 'startswith' match for '{name_search}': {selected_item_details.get(name_field, 'Unnamed')}")

        # Case 1: A specific item was successfully identified by name_search
        if selected_item_details:
            selected_item_id = selected_item_details.get(id_field)
            selected_item_name = selected_item_details.get(name_field, "Unnamed")

            if selected_item_id is None: # Should be rare if item is from API
                logger.error(f"CRITICAL: Matched item '{selected_item_name}' is missing its ID. Details: {json.dumps(selected_item_details, indent=2)}")
                CURRENT_SELECTED_OBJECT.clear()
                return {"status": "failure", "message": f"Error: Matched {obj_type_lower} '{selected_item_name}' is missing ID.", "object_type": obj_type_lower, "search_matches": found_object_names}
            
            logger.info(f"Selecting specific {obj_type_lower}: Name='{selected_item_name}', ID='{selected_item_id}'.")
            CURRENT_SELECTED_OBJECT.select(object_type=obj_type_lower, object_id=selected_item_id, object_name=selected_item_name, details=selected_item_details)
            return {"status": "success", "message": f"Selected Object is {CURRENT_SELECTED_OBJECT.object_name}", "object_type": obj_type_lower, "object_id": selected_item_id, "object_name": selected_item_name, "details": selected_item_details, "search_matches": found_object_names}

        # Case 2: A specific name_search was given, but no item was found (selected_item_details is still None)
        elif name_search and name_search.lower() != "default":
            logger.warning(f"Specific search for {obj_type_lower} '{name_search}' did not find a match. Clearing selection.")
            CURRENT_SELECTED_OBJECT.clear()
            return {
                "status": "not_found",
                "message": f"No {obj_type_lower} found matching the specific name '{name_search}'. Selection cleared.",
                "object_type": obj_type_lower,
                "search_matches": found_object_names # Names that might have 'started with' but weren't exact/unique
            }

        # Case 3: No name_search, or name_search was "default". Attempt to select the default object.
        else:
            logger.info(f"No specific name search or 'default' requested. Attempting to select default {obj_type_lower}.")
            if default_object_id and default_details.get(id_field) is not None:
                logger.info(f"Selecting default {obj_type_lower}: Name='{default_object_name}', ID='{default_object_id}'")
                CURRENT_SELECTED_OBJECT.select(object_type=obj_type_lower, object_id=default_object_id, object_name=default_object_name, details=default_details)
                return {"status": "success", "message": f"Selected Object is {CURRENT_SELECTED_OBJECT.object_name}", "object_type": obj_type_lower, "object_id": default_object_id, "object_name": default_object_name, "details": default_details, "search_matches": found_object_names}
            else:
                logger.warning(f"No default {obj_type_lower} could be determined or its ID is missing. Clearing selection.")
                CURRENT_SELECTED_OBJECT.clear()
                return {
                    "status": "not_found",
                    "message": f"No default {obj_type_lower} available to select, or default item is invalid. Selection cleared.",
                    "object_type": obj_type_lower,
                    "search_matches": found_object_names
                }

    except Exception as e:
        logger.error(f"Exception in select_object_tool ({obj_type_lower}): {str(e)}", exc_info=True)
        # Do not clear selection on general error, previous selection might be valid.
        return {
            "status": "error",
            "message": f"Error processing {obj_type_lower} selection: {str(e)}",
            "object_type": obj_type_lower,
            "search_matches": [] # Or potentially found_objects if available and relevant
        }
