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
        Returns a list of available commands for the currently selected object type.
        This will be expanded to fetch commands from dynamic_*.py modules.
        """
        commands = []
        if not self.object_type or not self.object_id:
            return commands

        # Common commands
        commands.append({
            "name": "update",
            "description": f"Initiate update for the selected {self.object_type} '{self.object_name}'. Provides current data and schema.",
            "requires_args": False,
            "special_handling": "update_flow"
        })
        
        delete_path_map = {
            "network": "/api/v1/networks/{id}",
            "connector": "/api/v1/networks/connectors/{id}", # Assuming network connector
            # "user": "/api/v1/users/{id}",
            # "usergroup": "/api/v1/user-groups/{id}",
        }
        if self.object_type in delete_path_map:
            commands.append({
                "name": "delete",
                "description": f"Delete the selected {self.object_type} '{self.object_name}'. This action is permanent.",
                "method": "delete",
                "path_template": delete_path_map[self.object_type],
                "requires_args": False
            })

        # Object-specific commands are now loaded from respective dynamic_*.py modules
        if self.object_type == "network":
            if self.object_id and self.object_name and self.details:
                network_commands = get_network_command_definitions(
                    network_id=self.object_id,
                    network_name=self.object_name,
                    network_details=self.details
                )
                commands.extend(network_commands)
        
        elif self.object_type == "connector":
            if self.object_id and self.object_name and self.details:
                connector_commands = get_connector_command_definitions(
                    connector_id=self.object_id,
                    connector_name=self.object_name,
                    connector_details=self.details
                )
                commands.extend(connector_commands)
        
        # Add elif for other object types (e.g., user, group) here
        # elif self.object_type == "user":
        #     user_commands = get_user_command_definitions(...)
        #     commands.extend(user_commands)

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


def select_object_tool(object_type: str, name_search: Optional[str] = None, kwargs: Optional[str] = None) -> Tuple[List[str], str]:
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
    logger.info(f"select_object_tool called with object_type='{object_type}', name_search='{name_search}', kwargs={kwargs}, using CONNEXA_REGION='{CONNEXA_REGION}'")
    
    found_objects = []
    selected_object_name = "None"
    default_object_name = "Default" # Placeholder for actual default logic
    default_object_id = None # Initialize default_object_id
    default_details = {} # Initialize default_details


    if object_type.lower() == "network":
        try:
            logger.info("Attempting to fetch networks using call_api...")
            networks_response = call_api(action="get", path="/api/v1/networks")
            logger.info(f"call_api response for networks: {networks_response}")
            
            if not isinstance(networks_response, dict) or \
               networks_response.get("status") != 200:
                error_detail = f"API call failed or returned non-200 status. Full response: {networks_response}"
                logger.error(f"Error fetching networks: {error_detail}")
                CURRENT_SELECTED_OBJECT.clear()
                return [], f"Error fetching networks: {networks_response.get('message', 'Unknown API error')}. Details: {error_detail}"

            # Handle potential nested 'content' key in the response data
            response_data = networks_response.get("data", {})
            if isinstance(response_data, dict) and isinstance(response_data.get("content"), list):
                networks: List[Dict[str, Any]] = response_data["content"]
                logger.info(f"Successfully fetched {len(networks)} network(s) from 'data.content'.")
            elif isinstance(response_data, list):
                 networks: List[Dict[str, Any]] = response_data
                 logger.info(f"Successfully fetched {len(networks)} network(s) directly from 'data'.")
            else:
                error_detail = f"API response data is not a list or does not contain a 'content' list. Data type: {type(response_data)}. Full response: {networks_response}"
                logger.error(f"Error fetching networks: {error_detail}")
                CURRENT_SELECTED_OBJECT.clear()
                return [], f"Error fetching networks: Unexpected data format. Details: {error_detail}"


            if not networks:
                logger.warning("No networks found from API.")
                CURRENT_SELECTED_OBJECT.clear()
                return ["No networks found."], "No networks available to select."

            # Determine default network
            logger.info(f"Determining default network. CONNEXA_REGION: {CONNEXA_REGION}")
            default_network_candidates = [n for n in networks if n.get('region') == CONNEXA_REGION]
            if default_network_candidates:
                default_object_name = default_network_candidates[0].get('name', 'Unknown Default Network')
                default_object_id = default_network_candidates[0].get('id')
                default_details = default_network_candidates[0]
                logger.info(f"Default network candidate from region '{CONNEXA_REGION}': {default_object_name} (ID: {default_object_id})")
            elif networks: # Fallback if no network in default region
                default_object_name = networks[0].get('name', 'Unknown Default Network')
                default_object_id = networks[0].get('id')
                default_details = networks[0]
                logger.info(f"Default network fallback (first network): {default_object_name} (ID: {default_object_id})")
            else: # Should not happen if 'if not networks:' check above is hit
                logger.warning("No networks available to determine a default.")
                default_object_name = "No Networks Found"
                # default_object_id and default_details remain None/empty

            # Parse kwargs string into a dictionary
            filter_kwargs: Dict[str, Any] = {}
            if kwargs:
                try:
                    filter_kwargs = json.loads(kwargs)
                    if not isinstance(filter_kwargs, dict):
                        logger.warning(f"kwargs parameter was not a valid JSON object string: {kwargs}")
                        filter_kwargs = {} # Reset if not a dict
                except json.JSONDecodeError:
                    logger.warning(f"Could not decode kwargs JSON string: {kwargs}")
                    filter_kwargs = {} # Reset on decode error

            logger.info(f"Starting network filtering process. Total networks fetched: {len(networks)}")
            logger.info(f"Filtering networks by name_search='{name_search}' and parsed filter_kwargs={filter_kwargs}")

            for net in networks:
                name_match = True
                if name_search and name_search.lower() != "default":
                    if name_search.lower() not in net.get("name", "").lower():
                        name_match = False

                if name_match:
                    # Apply additional filters from filter_kwargs if any
                    match_all_kwargs = True
                    for key, value in filter_kwargs.items():
                        # This is a simple exact match for now.
                        # Could be extended for more complex queries (e.g. status="connected")
                        # Ensure both network attribute value and filter value are strings for comparison
                        net_value = net.get(key)
                        if net_value is None: # Attribute not present in network object
                            match_all_kwargs = False
                            break
                        if str(net_value).lower() != str(value).lower():
                            match_all_kwargs = False
                            break
                    
                    if match_all_kwargs:
                        logger.info(f"Object matched filter criteria: {net.get('name', 'Unnamed')}")
                        found_objects.append(net)

            logger.info(f"Filtering complete. Found {len(found_objects)} network(s) after filtering.")

            # If no name_search was provided, and no kwargs were provided, use all networks
            if not name_search and not filter_kwargs:
                 logger.info("No name_search or kwargs specified, using all fetched networks for potential selection.")
                 found_objects = networks # Show all networks if no specific search
                 logger.info(f"Found objects updated to all networks. Count: {len(found_objects)}")


            # Prepare list of names for return
            found_object_names = [obj.get("name", "Unnamed") for obj in found_objects]
            logger.info(f"Names of found objects: {found_object_names}")

            logger.info(f"Evaluating selection logic. name_search='{name_search}', len(found_objects)={len(found_objects)}")
            if name_search and name_search.lower() != "default" and len(found_objects) == 1:
                selected_item_details = found_objects[0] # This is the dict from API
                selected_item_id = selected_item_details.get("id")
                selected_item_name = selected_item_details.get("name", "Unnamed")
                logger.info(f"Exactly one match found for search '{name_search}': Name='{selected_item_name}', ID='{selected_item_id}'.")
                logger.info(f"Data for matched object '{selected_item_name}': {json.dumps(selected_item_details, indent=2)}")
                
                CURRENT_SELECTED_OBJECT.select(
                    object_type="network",
                    object_id=selected_item_id,
                    object_name=selected_item_name,
                    details=selected_item_details # Pass the full dict
                )
                selected_object_name = selected_item_name
                logger.info(f"Final selected object (single match): {selected_object_name}")
                return found_object_names, f"Selected Object is {selected_object_name}"
            else:
                logger.info(f"Default selection logic: name_search='{name_search}', num_found_objects={len(found_objects)}")
                if name_search and name_search.lower() != "default" and len(found_objects) != 1:
                    logger.info(f"Search for '{name_search}' yielded {len(found_objects)} results (not 1). Selecting default.")
                
                if default_object_id:
                    logger.info(f"Selecting default network: Name='{default_object_name}', ID='{default_object_id}'")
                    logger.info(f"Data for default object '{default_object_name}': {json.dumps(default_details, indent=2)}")
                    CURRENT_SELECTED_OBJECT.select(
                        object_type="network",
                        object_id=default_object_id,
                        object_name=default_object_name,
                        details=default_details # Pass the full dict
                    )
                    selected_object_name = default_object_name
                else:
                    logger.warning("No default network could be determined or selected.")
                    CURRENT_SELECTED_OBJECT.clear()
                    selected_object_name = "No default network available."
            
            logger.info(f"Final selected object: {selected_object_name}")
            logger.info("Returning from default selection block.")
            return found_object_names, f"Selected Object is {selected_object_name}"

        except Exception as e:
            logger.error(f"Exception in select_object_tool (network): {str(e)}", exc_info=True)
            CURRENT_SELECTED_OBJECT.clear()
            # Return the full exception string to provide more details
            return [], f"Error processing network selection: {str(e)}"
            
    # Add other object types (user, group) here later
    # elif object_type.lower() == "user":
    #     pass
    # elif object_type.lower() == "usergroup":
    #     pass
    else:
        logger.warning(f"Unsupported object type: {object_type}. Clearing selection.")
        CURRENT_SELECTED_OBJECT.clear()
        return [], f"Unsupported object type: {object_type}. Supported types: network."

