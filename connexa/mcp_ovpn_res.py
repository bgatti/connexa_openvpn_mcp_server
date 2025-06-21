import sys # Added for sys.stderr
import asyncio # Needed for asyncio.to_thread
import json # Added for JSON parsing
import os # Added for path manipulation
from mcp.server.fastmcp import FastMCP
# Removed: from .group_tools import get_user_groups, get_user_group
from .connexa_api import call_api # Import call_api
# Import the global selected object instance
from .selected_object import CURRENT_SELECTED_OBJECT # Import swagger loader
from mcp.shared.exceptions import McpError # For error handling
from mcp.types import ErrorData, INTERNAL_ERROR # For error handling
import httpx # For making API calls (used by get_regions_resource)
from typing import Optional # Import Optional


# Move user_tools import to top-level for broader access
# from .. import user_tools # Assuming user_tools.py is in the parent directory of connexa # COMMENTED OUT

# --- Re-implemented group fetching functions using call_api ---
async def get_user_groups(page: int = 0, size: int = 100) -> dict:
    """
    Fetches a paginated list of user groups using call_api.
    """
    print(f"Re-implemented get_user_groups: page={page}, size={size}", file=sys.stderr)
    try:
        # call_api is synchronous, so run it in a thread
        response_data = await asyncio.to_thread(
            call_api,
            action="get",
            path=f"/api/v1/user-groups?page={page}&size={size}"
        )
        # call_api returns the parsed JSON response or raises an exception
        # Ensure it's a dict as expected by callers
        if not isinstance(response_data, dict):
            print(f"Re-implemented get_user_groups: call_api returned non-dict: {type(response_data)}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="API did not return expected dictionary for user groups."))
        return response_data
    except Exception as e:
        print(f"Re-implemented get_user_groups: Error: {e}", file=sys.stderr)
        # Re-raise as McpError or a more specific error if call_api doesn't already do so
        if isinstance(e, McpError):
            raise
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Failed to get user groups: {str(e)}"))

async def get_user_group(group_id: str) -> Optional[dict]:
    """
    Fetches a single user group by its ID using call_api.
    Returns None if the group is not found (e.g., 404).
    """
    print(f"Re-implemented get_user_group: group_id={group_id}", file=sys.stderr)
    try:
        response_data = await asyncio.to_thread(
            call_api,
            action="get",
            path=f"/api/v1/user-groups/{group_id}"
        )
        if not isinstance(response_data, dict):
            print(f"Re-implemented get_user_group: call_api returned non-dict: {type(response_data)}", file=sys.stderr)
            # This might indicate an error that call_api didn't catch as a 404 or similar
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="API did not return expected dictionary for user group."))
        return response_data
    except McpError as e:
        # McpError's first argument is usually the ErrorData object.
        error_data_obj: Optional[ErrorData] = e.args[0] if e.args and isinstance(e.args[0], ErrorData) else None
        
        if error_data_obj and (
            (error_data_obj.message and "404" in error_data_obj.message.lower()) or
            (error_data_obj.data and "404" in str(error_data_obj.data).lower()) # Check 'data' instead of 'details'
        ): # Heuristic for 404
            print(f"Re-implemented get_user_group: Group {group_id} not found (404). McpError details: {error_data_obj}", file=sys.stderr)
            return None # Return None for not found, as per original expectation
        
        print(f"Re-implemented get_user_group: McpError: {error_data_obj if error_data_obj else e}", file=sys.stderr)
        raise # Re-raise other McpErrors
    except Exception as e:
        print(f"Re-implemented get_user_group: Error: {e}", file=sys.stderr)
        # This path might be hit if call_api raises a non-McpError or if asyncio.to_thread fails
        # For robustness, treat other exceptions as an issue and don't return None unless it's a clear "not found"
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Failed to get user group {group_id}: {str(e)}"))


async def get_user_groups_resource(): # Removed mcp: FastMCP parameter
    """
    Fetches user groups and returns pertinent information for each group
    by calling the 'get_user_groups' tool internally.
    """
    print("get_user_groups_resource: Entered function", file=sys.stderr)
    try:
        print("get_user_groups_resource: Calling await get_user_groups", file=sys.stderr)
        # Call the now asynchronous get_user_groups function directly
        tool_result = await get_user_groups(page=0, size=100) # Uses re-implemented version
        print(f"get_user_groups_resource: get_user_groups returned: {type(tool_result)}", file=sys.stderr)

        # The re-implemented get_user_groups should return a dict or raise McpError.
        # An empty list of groups would typically be represented within the dict (e.g., "content": []).
        # It should not return None unless call_api itself returns None, which is not its typical behavior.
        print("get_user_groups_resource: Returning tool_result", file=sys.stderr)
        return tool_result

    except Exception as e: # This will catch McpError from get_user_groups
        print(f"get_user_groups_resource: Exception: {e}", file=sys.stderr)
        return {"error": f"An error occurred while fetching user groups: {str(e)}"}


# Removed: from .region_tools import get_vpn_regions
# Note: user_tools import is further down, check if it's needed here or should be moved up.
# For now, assuming it's correctly placed for get_users_with_group_info_resource.

# async def get_users_with_group_info_resource(): # Removed mcp: FastMCP parameter # COMMENTED OUT
#     """
#     Fetches users and their associated group names.
#     """
#     print("get_users_with_group_info_resource: Entered function", file=sys.stderr)
#     try:
#         print("get_users_with_group_info_resource: Calling asyncio.to_thread(get_users)", file=sys.stderr)
#         # Fetch all users
#         # get_users is still synchronous, so it needs to_thread
#         # user_tools is now imported at the top level.
#         users_data = await asyncio.to_thread(user_tools.get_users, page=0, size=100)
#         print(f"get_users_with_group_info_resource: user_tools.get_users returned: {type(users_data)}", file=sys.stderr)
# 
#         if users_data is None:
#             print("get_users_with_group_info_resource: users_data is None", file=sys.stderr)
#             return {"error": "Failed to fetch users or no users found. Tool returned None."}
# 
#         processed_users = []
#         # users_data from get_users is also a paginated response (dict with 'content')
#         if isinstance(users_data, dict) and "content" in users_data and isinstance(users_data["content"], list):
#             for user in users_data["content"]: # Iterate over the 'content' list
#                 if not isinstance(user, dict):
#                     continue # Skip non-dict items
# 
#                 user_id = user.get("id")
#                 first_name = user.get("firstName", "")
#                 last_name = user.get("lastName", "")
#                 email = user.get("email")
#                 group_id = user.get("groupId")
#                 
#                 group_name = "N/A"
#                 if group_id:
#                     try:
#                         # Fetch group details for this user's group_id
#                         # get_user_group is now async
#                         print(f"get_users_with_group_info_resource: Calling await get_user_group for group_id {group_id}", file=sys.stderr)
#                         group_data = await get_user_group(group_id=group_id)
#                         print(f"get_users_with_group_info_resource: get_user_group returned: {type(group_data)} for group_id {group_id}", file=sys.stderr)
#                         if group_data and isinstance(group_data, dict) and "name" in group_data:
#                             group_name = group_data["name"]
#                         elif group_data is None: # get_user_group returns None if group not found (404)
#                             group_name = "Unknown/Not Found"
#                     except Exception as e:
#                         print(f"get_users_with_group_info_resource: Exception in get_user_group call: {e}", file=sys.stderr)
#                         # Log this error, e.g., mcp.logger.warning(...)
#                         group_name = f"Error fetching group: {str(e)}"
#                 
#                 processed_users.append({
#                     "id": user_id,
#                     "name": f"{first_name} {last_name}".strip(),
#                     "email": email,
#                     "group_id": group_id,
#                     "group_name": group_name
#                 })
#             
#         print("get_users_with_group_info_resource: Returning processed_users", file=sys.stderr)
#         return {"users_with_group_info": processed_users}
# 
#     except Exception as e:
#         print(f"get_users_with_group_info_resource: Exception: {e}", file=sys.stderr)
#         # mcp.logger.error(f"Error in get_users_with_group_info_resource: {e}", exc_info=True)
#         return {"error": f"An error occurred while fetching users with group info: {str(e)}"}

def get_current_selection_data(): # Renamed function, made synchronous
    """
    Returns the currently selected item in the MCP server's state.
    """
    print("get_current_selection_data: Entered function (synchronous)", file=sys.stderr) # Updated print
    try:
        # Access the global CURRENT_SELECTED_OBJECT instance
        selected_info = CURRENT_SELECTED_OBJECT.get_selected_object_info()
        print(f"get_current_selection_data: Returning selected_info: {selected_info}", file=sys.stderr) # Updated print
        return selected_info
    except Exception as e:
        print(f"get_current_selection_data: Exception: {e}", file=sys.stderr) # Updated print
        # Log the exception, e.g., using mcp.logger if available and configured
        # For now, just returning the error string
        # Consider using mcp.logger.error(f"Error in fetch_current_selection_data: {e}", exc_info=True)
        return {"error": f"An error occurred while getting current selection: {str(e)}"}

async def get_regions_resource():
    """
    Fetches VPN regions directly using the API client.
    """

    # This is a simplified interpretation of swagger.json for overview purposes.
    # A more sophisticated approach would involve deeper parsing of schemas and paths.
    overview = {
        "title": "OpenVPN Connexa API Overview",
        "description": "The API manages Users, Devices, User Groups, Networks, Hosts, and Access Controls for a VPN infrastructure.",
        "main_entities": [
            {
                "name": "User",
                "description": "Represents an individual who can connect to the VPN. Users belong to User Groups and can have multiple Devices.",
                "relations": ["User Group (belongs to)", "Device (has many)", "Access Group (source)"],
                "selectable": True,
                "creatable": True
                },
            {
                "name": "Device",
                "description": "A physical or virtual device (computer, phone) associated with a User, used to connect. Device posture policies can apply.",
                "relations": ["User (belongs to)", "Device Posture (policy applies)"],
                "selectable": True,
                "creatable": True,
                "notes": "Requires a parent User to be selected for creation."
            },
            {
                "name": "User Group",
                "description": "A collection of Users, used to manage settings like VPN region access, internet access policies, and max devices per user. Can be a source in Access Groups.",
                "relations": ["User (has many)", "VPN Region (access defined)", "Access Group (source)"],
                "selectable": True,
                "creatable": True
            },
            {
                "name": "Network",
                "description": "Represents a private network (on-prem or cloud) connected to Cloud Connexa. Contains Connectors, Routes, and IP/Application Services. Can be a destination in Access Groups.",
                "relations": ["Connector (has many)", "Route (has many)", "IP Service (has many)", "Application (has many)", "Access Group (destination)"],
                "selectable": True,
                "creatable": True
            },
            {
                "name": "Host",
                "description": "A server within a private network running a Connector. Similar to Network, it can have Connectors and Services. Can be a destination in Access Groups.",
                "relations": ["Connector (has many)", "IP Service (has many)", "Application (has many)", "Access Group (destination)"],
                "selectable": True,
                "creatable": True
            },
            {
                "name": "Connector",
                "description": "A software instance that links a Network or Host to Cloud Connexa. Can be OpenVPN or IPsec type. Profiles can be generated for them.",
                "relations": ["Network (belongs to) or Host (belongs to)"],
                "selectable": True,
                "creatable": True,
                "notes": "Requires a parent Network or Host to be selected for creation."
                },
            {
                "name": "Access Group",
                "description": "Defines access control rules: which 'Sources' (e.g., User Groups, Networks, Hosts) can access which 'Destinations' (e.g., Networks, Hosts, Services). This is central to network segmentation.",
                "relations": ["User Group (source)", "Network (source/destination)", "Host (source/destination)"],
                "selectable": True,
                "creatable": True
            },
            {
                "name": "VPN Region",
                "description": "A geographic point-of-presence for Cloud Connexa servers. User Groups and Connectors are associated with regions.",
                "relations": ["User Group (access defined)", "Connector (connects via)"],
                "selectable": False, # Not directly selectable by select_object_tool
                "creatable": False # No direct creation tool
            },
            {
                "name": "Device Posture",
                "description": "Policies that define security requirements for Devices to connect (e.g., OS version, antivirus). Applied to User Groups.",
                "relations": ["Device (applies to)", "User Group (associated via)"],
                "selectable": True,
                "creatable": True
            },
            {
                "name": "DNS Record",
                "description": "Manages DNS 'A' records within the Cloud Connexa environment.",
                "relations": [],
                "selectable": True,
                "creatable": True
            },
            {
                "name": "Settings",
                "description": "Various global and specific settings for the WPC (Wide-area Private Cloud), user defaults, DNS, and authentication.",
                "relations": [],
                "selectable": False, # Assuming not directly selectable
                "creatable": False # Assuming no direct creation tool
            },
             {
                "name": "Route",
                "description": "Defines network routes within a Network.",
                "relations": ["Network (belongs to)"],
                "selectable": False, # Not directly selectable
                "creatable": False # No direct creation tool
            },
            {
                "name": "IP Service",
                "description": "Represents an IP-based service within a Network or Host.",
                "relations": ["Network (belongs to) or Host (belongs to)"],
                "selectable": False, # Not directly selectable
                "creatable": False # No direct creation tool
            },
            {
                "name": "Application",
                "description": "Represents an application service within a Network or Host.",
                "relations": ["Network (belongs to) or Host (belongs to)"],
                "selectable": False, # Not directly selectable
                "creatable": False # No direct creation tool
            }
        ],
        "key_interactions_dependencies": [
            "Users are assigned to User Groups, which dictate many of their permissions and connection parameters.",
            "Devices are registered to Users. A User can have multiple Devices.",
            "Access Groups are fundamental for controlling traffic flow, linking sources (like User Groups) to destinations (like Networks or specific services within them).",
            "Networks and Hosts require Connectors to establish connectivity with the Cloud Connexa VPN.",
            "Device Posture policies can restrict device connections based on compliance, often applied at the User Group level.",
            "Authentication (OAuth) is required for API interaction. SAML/LDAP can be used for user authentication into the VPN."
        ],
        "inobvious_points": [
            "The distinction between 'Network' and 'Host' allows for different levels of granularity in representing connected resources.",
            "'Internet Access' settings (SPLIT_TUNNEL_ON/OFF, RESTRICTED_INTERNET) for User Groups and Networks significantly impact traffic routing.",
            "Many 'Settings' endpoints allow fine-tuning of default behaviors for new users, devices, or connections.",
            "VPN Regions, Routes, IP Services, and Applications are not directly selectable or creatable as top-level entities via the current MCP tools, but are managed through their parent Network or Host entities."
            ],
        "known_issues": [
            "The `create_host_tool` may return a warning about ID/name not found in the top-level response, although the data is present in a nested field.",
            "The `create_device_tool` may fail due to a 'Device limit is exceeded' error for a user, which is an environment limitation based on user group properties rather than a tool issue."
        ]
    }
    return overview

# Determine the absolute path to the directory containing this script
# This helps in reliably locating api.json and schema.json
# __file__ is the path to the current script (mcp_ovpn_res.py)
# os.path.dirname(__file__) gives the directory of mcp_ovpn_res.py
# which is connexa_openvpn_mcp_server/
SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
API_JSON_PATH = os.path.join(SERVER_DIR, "api.json")
SCHEMA_JSON_PATH = os.path.join(SERVER_DIR, "schema.json")

async def get_api_commands_resource():
    """
    Reads and returns the content of api.json.
    """
    print("get_api_commands_resource: Entered function", file=sys.stderr)
    try:
        print(f"get_api_commands_resource: Attempting to read {API_JSON_PATH}", file=sys.stderr)
        def read_file_sync():
            with open(API_JSON_PATH, 'r') as f:
                return json.load(f)
        
        data = await asyncio.to_thread(read_file_sync)
        print("get_api_commands_resource: Successfully read and parsed api.json", file=sys.stderr)
        return data
    except FileNotFoundError:
        print(f"get_api_commands_resource: Error - api.json not found at {API_JSON_PATH}", file=sys.stderr)
        return {"error": f"api.json not found at {API_JSON_PATH}"}
    except json.JSONDecodeError as e:
        print(f"get_api_commands_resource: Error decoding api.json: {e}", file=sys.stderr)
        return {"error": f"Error decoding api.json: {str(e)}"}
    except Exception as e:
        print(f"get_api_commands_resource: Unexpected exception: {e}", file=sys.stderr)
        return {"error": f"An unexpected error occurred while reading api.json: {str(e)}"}

async def get_schema_json_resource():
    """
    Reads and returns the content of schema.json.
    """
    print("get_schema_json_resource: Entered function", file=sys.stderr)
    try:
        print(f"get_schema_json_resource: Attempting to read {SCHEMA_JSON_PATH}", file=sys.stderr)
        def read_file_sync():
            with open(SCHEMA_JSON_PATH, 'r') as f:
                return json.load(f)

        data = await asyncio.to_thread(read_file_sync)
        print("get_schema_json_resource: Successfully read and parsed schema.json", file=sys.stderr)
        return data
    except FileNotFoundError:
        print(f"get_schema_json_resource: Error - schema.json not found at {SCHEMA_JSON_PATH}", file=sys.stderr)
        return {"error": f"schema.json not found at {SCHEMA_JSON_PATH}"}
    except json.JSONDecodeError as e:
        print(f"get_schema_json_resource: Error decoding schema.json: {e}", file=sys.stderr)
        return {"error": f"Error decoding schema.json: {str(e)}"}
    except Exception as e:
        print(f"get_schema_json_resource: Unexpected exception: {e}", file=sys.stderr)
        return {"error": f"An unexpected error occurred while reading schema.json: {str(e)}"}

async def get_creation_schema_resource(object_type: str | None = None):
    """
    Retrieves the JSON schema for creating a given object type from swagger.json.
    The object_type should correspond to the entity being created, e.g., "Network", "UserGroup".
    If object_type is None, it indicates an issue or a request for general schema info.
    """
    print(f"get_creation_schema_resource: Entered for object_type='{object_type}'", file=sys.stderr)

    # Mapping from a simplified object_type to the specific CreateRequest schema name in swagger.json
    # This needs to be maintained and match the object types used by the client/agent.
    schema_name_map = {
        "Network": "NetworkCreateRequest",
        "NetworkConnector": "NetworkConnectorRequest", # Used for POST /api/v1/networks/connectors
        "UserGroup": "UserGroupRequest",             # Used for POST /api/v1/user-groups
        "Host": "HostCreateRequest",
        "HostConnector": "HostConnectorRequest",       # Used for POST /api/v1/hosts/connectors
        "Device": "DeviceRequest",                   # Used for POST /api/v1/devices
        "DnsRecord": "DnsRecordRequest",             # Used for POST /api/v1/dns-records
        "AccessGroup": "AccessGroupRequest",
        "LocationContext": "LocationContextRequest",
        "DevicePosture": "DevicePostureRequest",
        # Add other mappings as needed, e.g., "User": "UserCreateRequest"
    }

    if object_type is None:
        error_msg = "An 'object_type' must be specified to retrieve a creation schema."
        print(f"get_creation_schema_resource: {error_msg}", file=sys.stderr)
        return {"error": error_msg, "available_object_types": list(schema_name_map.keys())}

    # Placeholder for hardcoded schemas
    hardcoded_schemas = {
        "User": {
            "type": "object",
            "properties": {
                "firstName": {
                    "description": "User's first name.",
                    "title": "Firstname",
                    "type": "string"
                },
                "lastName": {
                    "description": "User's last name.",
                    "title": "Lastname",
                    "type": "string"
                },
                "username": {
                    "description": "Username for the user. This will be used for login.",
                    "title": "Username",
                    "type": "string"
                },
                "email": {
                    "description": "User's email address.",
                    "title": "Email",
                    "type": "string"
                },
                "groupId": {
                    "type": "string",
                    "description": "ID of the group the user belongs to.",
                    "title": "Groupid"
                },
                "role": {
                    "description": "Role of the user. Must be one of: OWNER, MEMBER, ADMIN.",
                    "enum": [
                        "OWNER",
                        "MEMBER",
                        "ADMIN"
                    ],
                    "title": "Role",
                    "type": "string"
                }
            },
            "required": [
                "firstName",
                "lastName",
                "username",
                "email",
                "groupId", # Made required
                "role"
            ],
            "title": "CreateUserArgs",
            "type": "object"
        },
        "LocationContext": {
            "type": "object",
            "properties": {
                "name": {
                    "description": "Name for the new location context policy.",
                    "title": "Name",
                    "type": "string"
                },
                "description": {
                    "anyOf": [
                        {
                            "type": "string"
                        },
                        {
                            "type": "None"
                        }
                    ],
                    "default": None,
                    "description": "Optional description.",
                    "title": "Description"
                },
                "userGroupsIds": {
                    "anyOf": [
                        {
                            "items": {
                                "type": "string"
                            },
                            "type": "array"
                        },
                        {
                            "type": "None"
                        }
                    ],
                    "default": None,
                    "description": "List of user group IDs associated with this policy.",
                    "title": "Usergroupsids"
                },
                "ipCheck": {
                    "type": "object", # Made required
                    "properties": {
                        "allowed": {
                            "title": "Allowed",
                            "type": "boolean"
                        },
                        "ips": {
                            "anyOf": [
                                {
                                    "items": {
                                        "type": "string"
                                    },
                                    "type": "array"
                                },
                                {
                                    "type": "None"
                                }
                            ],
                            "default": None,
                            "description": "List of IP addresses for the record (CIDR format, e.g., '192.168.1.1/32').", # Added note
                            "title": "Ips"
                        }
                    },
                    "required": [
                        "allowed"
                    ],
                    "title": "IpCheckRequestModel",
                    "type": "object"
                },
                "countryCheck": {
                    "type": "object", # Made required
                    "properties": {
                        "countries": {
                            "anyOf": [
                                {
                                    "items": {
                                        "type": "string"
                                    },
                                    "type": "array"
                                },
                                {
                                    "type": "None"
                                }
                            ],
                            "default": None,
                            "title": "Countries"
                        },
                        "allowed": {
                            "title": "Allowed",
                            "type": "boolean"
                        }
                    },
                    "required": [
                        "allowed"
                    ],
                    "title": "CountryCheckRequestModel",
                    "type": "object"
                },
                "defaultCheck": {
                    "anyOf": [
                        {
                            "type": "object",
                            "properties": {
                                "allowed": {
                                    "title": "Allowed",
                                    "type": "boolean"
                                }
                            },
                            "required": [
                                "allowed"
                            ],
                            "title": "DefaultCheckRequestModel",
                            "type": "object"
                        },
                        {
                            "type": "None"
                        }
                    ],
                    "default": None,
                    "description": "Default check criteria for access."
                }
            },
            "required": [
                "name",
                "ipCheck", # Made required
                "countryCheck" # Made required
            ],
            "title": "CreateLocationContextArgs",
            "type": "object"
        },
        "Device": {
            "type": "object",
            "properties": {
                "userId": {
                    "description": "ID of the User to associate the device with.",
                    "title": "Userid",
                    "type": "string"
                },
                "name": {
                    "description": "Name for the new device.",
                    "title": "Name",
                    "type": "string"
                },
                "description": {
                    "anyOf": [
                        {
                            "type": "string"
                        },
                        {
                            "type": "None"
                        }
                    ],
                    "default": None,
                    "description": "Optional description for the device.",
                    "title": "Description"
                },
                "clientUUID": {
                    "type": "string", # Made required
                    "description": "Client UUID of the device. Note: Device limits are based on user group properties.", # Added note
                    "title": "Clientuuid"
                }
            },
            "required": [
                "userId",
                "name",
                "clientUUID" # Made required
            ],
            "title": "CreateDeviceArgs",
            "type": "object"
        }
    }


    if object_type in hardcoded_schemas:
        print(f"get_creation_schema_resource: Returning hardcoded schema for object_type '{object_type}'.", file=sys.stderr)
        return {"object_type": object_type, "schema_name": f"Create{object_type}Args", "schema": hardcoded_schemas[object_type]}
    else:
        # Fallback or error if schema is not hardcoded
        error_msg = f"No hardcoded creation schema found for object_type: '{object_type}'. Available hardcoded types: {list(hardcoded_schemas.keys())}"
        print(f"get_creation_schema_resource: {error_msg}", file=sys.stderr)
        return {"error": error_msg, "available_types": list(hardcoded_schemas.keys())}


async def get_creation_schema_resource_base():
    """
    Handler for the creation_schema resource when no object_type is specified in the URI.
    Delegates to get_creation_schema_resource with object_type=None.
    """
    print("get_creation_schema_resource_base: Entered, calling get_creation_schema_resource(object_type=None)", file=sys.stderr)
    return await get_creation_schema_resource(object_type=None)

def get_connexa_overview_resource(mcp: FastMCP):
    """
    Provides an overview of registered tools and Connexa VPN object types and their relationships.
    """
    print("get_connexa_overview_resource: Entered function", file=sys.stderr)
    try:
        # Fetch registered tools and resources
        tool_names = [tool.name for tool in mcp._tool_manager.list_tools()]
        resource_uris = [resource.uri for resource in mcp._resource_manager.list_resources()]

        # Include the condensed information about Connexa VPN objects and relationships
        connexa_objects_overview = {
            "title": "OpenVPN Connexa API Overview",
            "description": "The API manages Users, Devices, User Groups, Networks, Hosts, and Access Controls for a VPN infrastructure.",
            "main_entities": [
                {
                    "name": "User",
                    "description": "Represents an individual who can connect to the VPN. Users belong to User Groups and can have multiple Devices.",
                    "relations": ["User Group (belongs to)", "Device (has many)", "Access Group (source)"],
                    "selectable": True,
                    "creatable": True
                },
                {
                    "name": "Device",
                    "description": "A physical or virtual device (computer, phone) associated with a User, used to connect. Device posture policies can apply.",
                    "relations": ["User (belongs to)", "Device Posture (policy applies)"],
                    "selectable": True,
                    "creatable": True,
                    "notes": "Requires a parent User to be selected for creation."
                },
                {
                    "name": "User Group",
                    "description": "A collection of Users, used to manage settings like VPN region access, internet access policies, and max devices per user. Can be a source in Access Groups.",
                    "relations": ["User (has many)", "VPN Region (access defined)", "Access Group (source)"],
                    "selectable": True,
                    "creatable": True
                },
                {
                    "name": "Network",
                    "description": "Represents a private network (on-prem or cloud) connected to Cloud Connexa. Contains Connectors, Routes, and IP/Application Services. Can be a destination in Access Groups.",
                    "relations": ["Connector (has many)", "Route (has many)", "IP Service (has many)", "Application (has many)", "Access Group (destination)"],
                    "selectable": True,
                    "creatable": True
                },
                {
                    "name": "Host",
                    "description": "A server within a private network running a Connector. Similar to Network, it can have Connectors and Services. Can be a destination in Access Groups.",
                    "relations": ["Connector (has many)", "IP Service (has many)", "Application (has many)", "Access Group (destination)"],
                    "selectable": True,
                    "creatable": True
                },
                {
                    "name": "Connector",
                    "description": "A software instance that links a Network or Host to Cloud Connexa. Can be OpenVPN or IPsec type. Profiles can be generated for them.",
                    "relations": ["Network (belongs to) or Host (belongs to)"],
                    "selectable": True,
                    "creatable": True,
                    "notes": "Requires a parent Network or Host to be selected for creation."
                },
                {
                    "name": "Access Group",
                    "description": "Defines access control rules: which 'Sources' (e.g., User Groups, Networks, Hosts) can access which 'Destinations' (e.g., Networks, Hosts, Services). This is central to network segmentation.",
                    "relations": ["User Group (source)", "Network (source/destination)", "Host (source/destination)"],
                    "selectable": True,
                    "creatable": True
                },
                {
                    "name": "VPN Region",
                    "description": "A geographic point-of-presence for Cloud Connexa servers. User Groups and Connectors are associated with regions.",
                    "relations": ["User Group (access defined)", "Connector (connects via)"],
                    "selectable": False, # Not directly selectable by select_object_tool
                    "creatable": False # No direct creation tool
                },
                {
                    "name": "Device Posture",
                    "description": "Policies that define security requirements for Devices to connect (e.g., OS version, antivirus). Applied to User Groups.",
                    "relations": ["Device (applies to)", "User Group (associated via)"],
                    "selectable": True,
                    "creatable": True
                },
                {
                    "name": "DNS Record",
                    "description": "Manages DNS 'A' records within the Cloud Connexa environment.",
                    "relations": [],
                    "selectable": True,
                    "creatable": True
                },
                {
                    "name": "Settings",
                    "description": "Various global and specific settings for the WPC (Wide-area Private Cloud), user defaults, DNS, and authentication.",
                    "relations": [],
                    "selectable": False, # Assuming not directly selectable
                    "creatable": False # Assuming no direct creation tool
                },
                 {
                    "name": "Route",
                    "description": "Defines network routes within a Network.",
                    "relations": ["Network (belongs to)"],
                    "selectable": False, # Not directly selectable
                    "creatable": False # No direct creation tool
                },
                {
                    "name": "IP Service",
                    "description": "Represents an IP-based service within a Network or Host.",
                    "relations": ["Network (belongs to) or Host (belongs to)"],
                    "selectable": False, # Not directly selectable
                    "creatable": False # No direct creation tool
                },
                {
                    "name": "Application",
                    "description": "Represents an application service within a Network or Host.",
                    "relations": ["Network (belongs to) or Host (belongs to)"],
                    "selectable": False, # Not directly selectable
                    "creatable": False # No direct creation tool
                }
            ],
            "key_interactions_dependencies": [
                "Users are assigned to User Groups, which dictate many of their permissions and connection parameters.",
                "Devices are registered to Users. A User can have multiple Devices.",
                "Access Groups are fundamental for controlling traffic flow, linking sources (like User Groups) to destinations (like Networks or specific services within them).",
                "Networks and Hosts require Connectors to establish connectivity with the Cloud Connexa VPN.",
                "Device Posture policies can restrict device connections based on compliance, often applied at the User Group level.",
                "Authentication (OAuth) is required for API interaction. SAML/LDAP can be used for user authentication into the VPN."
            ],
            "inobvious_points": [
                "The distinction between 'Network' and 'Host' allows for different levels of granularity in representing connected resources.",
                "'Internet Access' settings (SPLIT_TUNNEL_ON/OFF, RESTRICTED_INTERNET) for User Groups and Networks significantly impact traffic routing.",
                "Many 'Settings' endpoints allow fine-tuning of default behaviors for new users, devices, or connections.",
                "VPN Regions, Routes, IP Services, and Applications are not directly selectable or creatable as top-level entities via the current MCP tools, but are managed through their parent Network or Host entities."
            ],
            "known_issues": [
                "The `create_host_tool` may return a warning about ID/name not found in the top-level response, although the data is present in a nested field.",
                "The `create_device_tool` may fail due to a 'Device limit is exceeded' error for a user, which is an environment limitation based on user group properties rather than a tool issue."
            ]
        }

        overview_data = {
            "registered_tools": tool_names,
            "registered_resources": resource_uris, # Add registered resources
            "connexa_objects_overview": connexa_objects_overview
        }

        print("get_connexa_overview_resource: Returning overview data", file=sys.stderr)
        return overview_data

    except Exception as e:
        print(f"get_connexa_overview_resource: Exception: {e}", file=sys.stderr)
        return {"error": f"An error occurred while generating the overview: {str(e)}"}

# Synchronous wrappers for asynchronous resource providers
