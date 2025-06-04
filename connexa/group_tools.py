import sys
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
import httpx # Changed from requests
from . import config_manager # Changed to relative import
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS

# --- Pydantic Models for User Group API ---

class UserGroupRequestModel(BaseModel):
    name: str = Field(description="Name of the user group.")
    internetAccess: Optional[Literal["SPLIT_TUNNEL_ON", "SPLIT_TUNNEL_OFF", "RESTRICTED_INTERNET"]] = Field(default=None, description="Internet access level for the group.")
    maxDevice: Optional[int] = Field(default=None, description="Maximum number of devices allowed per user in this group.")
    connectAuth: Optional[Literal["NO_AUTH", "ON_PRIOR_AUTH", "EVERY_TIME"]] = Field(default=None, description="Authentication mode for connections.")
    allRegionsIncluded: Optional[bool] = Field(default=None, description="Set to true to include all current and future regions by default.")
    vpnRegionIds: Optional[List[str]] = Field(default=None, description="List of VPN Region IDs available to the group. Omit or pass empty list if allRegionsIncluded is true.")
    gatewaysIds: Optional[List[str]] = Field(default=None, description="List of Gateway IDs for internet traffic. Relevant if internetAccess is SPLIT_TUNNEL_OFF.")

class UserGroupResponseModel(BaseModel):
    id: str
    name: str
    allRegionsIncluded: Optional[bool] = None
    internetAccess: Optional[Literal["SPLIT_TUNNEL_ON", "SPLIT_TUNNEL_OFF", "RESTRICTED_INTERNET"]] = None
    maxDevice: Optional[int] = None
    connectAuth: Optional[Literal["NO_AUTH", "ON_PRIOR_AUTH", "EVERY_TIME"]] = None
    vpnRegionIds: Optional[List[str]] = Field(default=None, description="List of VPN Region IDs available to the group.")
    gatewaysIds: Optional[List[str]] = Field(default=None, description="List of Gateway IDs for internet traffic.")
    systemSubnets: Optional[List[str]] = Field(default=None, description="List of system subnets.") # Present in swagger for response

# --- User Group API Tool Handler Functions ---

async def _get_all_vpn_region_ids() -> List[str]: # Made async
    """Retrieves all available VPN region IDs."""
    print("Fetching all VPN region IDs", file=sys.stderr)
    token = config_manager.get_api_token()
    if not token:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for _get_all_vpn_region_ids. Please configure the server."))
    api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/regions"
    headers = {"accept": "*/*", "Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient() as client: # Use httpx.AsyncClient
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
        regions_data = response.json() 
        if not isinstance(regions_data, list):
            print(f"Unexpected response format for regions: {regions_data}", file=sys.stderr)
            return []
        region_ids = [region['id'] for region in regions_data if isinstance(region, dict) and 'id' in region]
        return region_ids
    except httpx.RequestError as e: # Changed from requests.exceptions.RequestException
        print(f"Error calling OpenVPN API for _get_all_vpn_region_ids: {e}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for _get_all_vpn_region_ids: {e}"))
    except httpx.HTTPStatusError as e: # Added for httpx specific status errors
        print(f"HTTP error calling OpenVPN API for _get_all_vpn_region_ids: {e.response.status_code} - {e.response.text}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API HTTP error for _get_all_vpn_region_ids: {e}"))
    except (KeyError, TypeError) as e:
        print(f"Error parsing regions response: {e}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Error parsing regions response for _get_all_vpn_region_ids: {e}"))

async def get_user_groups(page: int = 0, size: int = 10): # Made async
    """Retrieves a page of existing user groups."""
    print(f"Handling get_user_groups with args: page={page}, size={size}", file=sys.stderr)
    token = config_manager.get_api_token()
    if not token:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for get_user_groups. Please configure the server."))
    api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/user-groups?page={page}&size={size}"
    headers = {"accept": "*/*", "Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient() as client: # Use httpx.AsyncClient
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
        return response.json() # Assuming this returns PageUserGroupResponse structure
    except httpx.RequestError as e: # Changed from requests.exceptions.RequestException
        print(f"Error calling OpenVPN API for get_user_groups: {e}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for get_user_groups: {e}"))
    except httpx.HTTPStatusError as e: # Added for httpx specific status errors
        print(f"HTTP error calling OpenVPN API for get_user_groups: {e.response.status_code} - {e.response.text}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API HTTP error for get_user_groups: {e}"))

async def get_user_group(group_id: str): # Made async
    """Retrieves a specific user group by its ID."""
    print(f"Handling get_user_group for group_id: {group_id}", file=sys.stderr)
    token = config_manager.get_api_token()
    if not token:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for get_user_group. Please configure the server."))
    api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/user-groups/{group_id}"
    headers = {"accept": "*/*", "Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient() as client: # Use httpx.AsyncClient
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e: # Changed from requests.exceptions.HTTPError
        if e.response.status_code == 404:
            return None
        print(f"HTTP error calling OpenVPN API for get_user_group: {e.response.status_code} - {e.response.text}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API HTTP error for get_user_group: {e}"))
    except httpx.RequestError as e: # Changed from requests.exceptions.RequestException
        print(f"Error calling OpenVPN API for get_user_group: {e}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for get_user_group: {e}"))

async def create_user_group( # Made async
    name: str = Field(description="Name of the user group."),
    internetAccess: Literal["SPLIT_TUNNEL_ON", "SPLIT_TUNNEL_OFF", "RESTRICTED_INTERNET"] = Field(default="SPLIT_TUNNEL_ON", description="Internet access level for the group. Possible values: SPLIT_TUNNEL_ON, SPLIT_TUNNEL_OFF, RESTRICTED_INTERNET."),
    maxDevice: int = Field(default=1, description="Maximum number of devices allowed per user in this group. Must be greater than or equal to 1."),
    connectAuth: Literal["NO_AUTH", "ON_PRIOR_AUTH", "EVERY_TIME"] = Field(default="NO_AUTH", description="Authentication mode for connections. Possible values: NO_AUTH, ON_PRIOR_AUTH, EVERY_TIME."),
    gatewaysIds: Optional[List[str]] = Field(default=None, description="List of Gateway IDs. Required if internetAccess is SPLIT_TUNNEL_OFF.")
):
    """Creates a new user group. By default, allRegionsIncluded is true and all available VPN regions are assigned."""
    
    # Use the provided example structure for the payload
    payload = {
      "name": name, # Use the name from the tool argument
      "vpnRegionIds": [], # Explicitly empty list as in example
      "internetAccess": internetAccess,
      "maxDevice": maxDevice,
      "connectAuth": connectAuth,
      "allRegionsIncluded": True, # Explicitly true as in example
      "gatewaysIds": [] # Explicitly empty list as in example
    }

    # Validate the payload against the Pydantic model (optional but good practice)
    # This helps catch issues before sending to the API
    try:
        UserGroupRequestModel(**payload)
    except Exception as e:
        print(f"Payload validation failed: {e}", file=sys.stderr)
        raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Invalid payload structure: {e}"))


    print(f"Handling create_user_group with data: {payload}", file=sys.stderr)
    token = config_manager.get_api_token()
    if not token:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for create_user_group. Please configure the server."))
    
    api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/user-groups"
    headers = {"accept": "*/*", "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    try:
        async with httpx.AsyncClient() as client: # Use httpx.AsyncClient
            response = await client.post(api_url, headers=headers, json=payload)
            response.raise_for_status()
        created_group_data = response.json()

        # Update the global selected item - Temporarily commented out
        # try:
        #     # Delayed import to avoid circular dependency at module load time
        #     # Using relative import for intra-package access to server.app
        #     from .server import app 
        #     if created_group_data and isinstance(created_group_data, dict):
        #         app.current_selection = {
        #             "type": "group",
        #             "id": created_group_data.get("id"),
        #             "name": created_group_data.get("name"),
        #             "data": created_group_data
        #         }
        #         print(f"Updated current_selection with new group: {created_group_data.get('name')}", file=sys.stderr)
        # except ImportError:
        #     print("Error: Could not import 'app' from mcp_server_demo.server to update selection.", file=sys.stderr)
        # except Exception as e_sel:
        #     print(f"Error updating current_selection: {e_sel}", file=sys.stderr)

        return created_group_data
    except httpx.RequestError as e: # Changed from requests.exceptions.RequestException
        error_message = f"OpenVPN API RequestError for create_user_group: {e}"
        print(error_message, file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=error_message))
    except httpx.HTTPStatusError as e: # Added for httpx specific status errors
        print(f"HTTP error calling OpenVPN API for create_user_group: {e.response.status_code} - {e.response.text}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API HTTP error for create_user_group: {e}"))

async def update_user_group_name(group_id: str, name: str = Field(description="New name for the user group.")): # Made async
    """Updates the name of an existing user group."""
    print(f"Handling update_user_group_name for group_id: {group_id} with name: {name}", file=sys.stderr)
    
    current_group_data = await get_user_group(group_id) # Added await
    if not current_group_data:
        print(f"User group {group_id} not found. Cannot update name.", file=sys.stderr)
        return None

    # Update the name in the fetched data
    current_group_data["name"] = name
    
    # Prepare the payload using UserGroupRequestModel to ensure correct structure
    update_payload = UserGroupRequestModel(
        name=current_group_data.get("name"),
        internetAccess=current_group_data.get("internetAccess"),
        maxDevice=current_group_data.get("maxDevice"),
        connectAuth=current_group_data.get("connectAuth"),
        allRegionsIncluded=current_group_data.get("allRegionsIncluded"),
        vpnRegionIds=current_group_data.get("vpnRegionIds"),
        gatewaysIds=current_group_data.get("gatewaysIds")
    ).model_dump(exclude_none=True)


    token = config_manager.get_api_token()
    if not token:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for update_user_group_name. Please configure the server."))

    api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/user-groups/{group_id}"
    headers = {"accept": "*/*", "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    try:
        async with httpx.AsyncClient() as client: # Use httpx.AsyncClient
            response = await client.put(api_url, headers=headers, json=update_payload)
            response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e: # Changed
        if e.response.status_code == 404: 
            return None
        print(f"HTTP error during OpenVPN API call for update_user_group_name: {e.response.status_code} - {e.response.text}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API HTTP error for update_user_group_name: {e}"))
    except httpx.RequestError as e: # Changed
        print(f"Error calling OpenVPN API for update_user_group_name: {e}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for update_user_group_name: {e}"))

async def update_user_group_internet_access( # Made async
    group_id: str, 
    internetAccess: Literal["SPLIT_TUNNEL_ON", "SPLIT_TUNNEL_OFF", "RESTRICTED_INTERNET"] = Field(description="New internet access level. Possible values: SPLIT_TUNNEL_ON, SPLIT_TUNNEL_OFF, RESTRICTED_INTERNET."),
    gatewaysIds: Optional[List[str]] = Field(default=None, description="List of Gateway IDs. Required if internetAccess is SPLIT_TUNNEL_OFF. If not provided and required, an invented ID will be used for testing.")
):
    """Updates the internet access level of an existing user group."""
    print(f"Handling update_user_group_internet_access for group_id: {group_id} with internetAccess: {internetAccess}", file=sys.stderr)
    
    current_group_data = await get_user_group(group_id) # Added await
    if not current_group_data:
        print(f"User group {group_id} not found. Cannot update internet access.", file=sys.stderr)
        return None

    current_group_data["internetAccess"] = internetAccess
    
    # Handle gatewaysIds based on internetAccess
    gateways_ids_to_use = current_group_data.get("gatewaysIds", []) 
    if internetAccess == "SPLIT_TUNNEL_OFF":
        if gatewaysIds is not None: 
            gateways_ids_to_use = gatewaysIds
        elif not gateways_ids_to_use: 
            print("Using invented gateway ID for SPLIT_TUNNEL_OFF as none were provided.", file=sys.stderr)
            gateways_ids_to_use = ["00000000-0000-0000-0000-000000000000"] 
    else: 
        gateways_ids_to_use = []

    current_group_data["gatewaysIds"] = gateways_ids_to_use
    
    update_payload = UserGroupRequestModel(
        name=current_group_data.get("name"),
        internetAccess=current_group_data.get("internetAccess"),
        maxDevice=current_group_data.get("maxDevice"),
        connectAuth=current_group_data.get("connectAuth"),
        allRegionsIncluded=current_group_data.get("allRegionsIncluded"),
        vpnRegionIds=current_group_data.get("vpnRegionIds"),
        gatewaysIds=gateways_ids_to_use 
    ).model_dump(exclude_none=True)

    token = config_manager.get_api_token()
    if not token:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for update_user_group_internet_access. Please configure the server."))

    api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/user-groups/{group_id}"
    headers = {"accept": "*/*", "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    try:
        async with httpx.AsyncClient() as client: # Use httpx.AsyncClient
            response = await client.put(api_url, headers=headers, json=update_payload)
            response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e: # Changed
        if e.response.status_code == 404:
            return None
        print(f"HTTP error during OpenVPN API call for update_user_group_internet_access: {e.response.status_code} - {e.response.text}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API HTTP error for update_user_group_internet_access: {e}"))
    except httpx.RequestError as e: # Changed
        print(f"Error calling OpenVPN API for update_user_group_internet_access: {e}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for update_user_group_internet_access: {e}"))

async def update_user_group_max_device(group_id: str, maxDevice: int = Field(description="New maximum number of devices.")): # Made async
    """Updates the maximum number of devices allowed for users in a group."""
    print(f"Handling update_user_group_max_device for group_id: {group_id} with maxDevice: {maxDevice}", file=sys.stderr)
    
    current_group_data = await get_user_group(group_id) # Added await
    if not current_group_data:
        print(f"User group {group_id} not found. Cannot update max devices.", file=sys.stderr)
        return None

    current_group_data["maxDevice"] = maxDevice
    
    update_payload = UserGroupRequestModel(
        name=current_group_data.get("name"),
        internetAccess=current_group_data.get("internetAccess"),
        maxDevice=current_group_data.get("maxDevice"),
        connectAuth=current_group_data.get("connectAuth"),
        allRegionsIncluded=current_group_data.get("allRegionsIncluded"),
        vpnRegionIds=current_group_data.get("vpnRegionIds"),
        gatewaysIds=current_group_data.get("gatewaysIds")
    ).model_dump(exclude_none=True)

    print(f"updating group object: {update_payload} ", file=sys.stderr)


    token = config_manager.get_api_token()
    if not token:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for update_user_group_max_device. Please configure the server."))

    api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/user-groups/{group_id}"
    headers = {"accept": "*/*", "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    try:
        async with httpx.AsyncClient() as client: # Use httpx.AsyncClient
            response = await client.put(api_url, headers=headers, json=update_payload)
            response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e: # Changed
        if e.response.status_code == 404:
            return None
        print(f"HTTP error during OpenVPN API call for update_user_group_max_device: {e.response.status_code} - {e.response.text}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API HTTP error for update_user_group_max_device: {e}"))
    except httpx.RequestError as e: # Changed
        print(f"Error calling OpenVPN API for update_user_group_max_device: {e}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for update_user_group_max_device: {e}"))

async def update_user_group_connect_auth(group_id: str, connectAuth: Literal["NO_AUTH", "ON_PRIOR_AUTH", "EVERY_TIME"] = Field(description="New authentication mode. Possible values: NO_AUTH, ON_PRIOR_AUTH, EVERY_TIME.")): # Made async
    """Updates the connection authentication mode for a user group."""
    print(f"Handling update_user_group_connect_auth for group_id: {group_id} with connectAuth: {connectAuth}", file=sys.stderr)
    
    current_group_data = await get_user_group(group_id) # Added await
    if not current_group_data:
        print(f"User group {group_id} not found. Cannot update connect auth.", file=sys.stderr)
        return None

    current_group_data["connectAuth"] = connectAuth
    
    update_payload = UserGroupRequestModel(
        name=current_group_data.get("name"),
        internetAccess=current_group_data.get("internetAccess"),
        maxDevice=current_group_data.get("maxDevice"),
        connectAuth=current_group_data.get("connectAuth"),
        allRegionsIncluded=current_group_data.get("allRegionsIncluded"),
        vpnRegionIds=current_group_data.get("vpnRegionIds"),
        gatewaysIds=current_group_data.get("gatewaysIds")
    ).model_dump(exclude_none=True)

    token = config_manager.get_api_token()
    if not token:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for update_user_group_connect_auth. Please configure the server."))

    api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/user-groups/{group_id}"
    headers = {"accept": "*/*", "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    try:
        async with httpx.AsyncClient() as client: # Use httpx.AsyncClient
            response = await client.put(api_url, headers=headers, json=update_payload)
            response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e: # Changed
        if e.response.status_code == 404:
            return None
        print(f"HTTP error during OpenVPN API call for update_user_group_connect_auth: {e.response.status_code} - {e.response.text}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API HTTP error for update_user_group_connect_auth: {e}"))
    except httpx.RequestError as e: # Changed
        print(f"Error calling OpenVPN API for update_user_group_connect_auth: {e}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for update_user_group_connect_auth: {e}"))

async def update_user_group_all_regions_included(group_id: str, allRegionsIncluded: bool = Field(default=False, description="New value for all regions included. Defaults to False if not provided.")): # Made async
    """Updates whether all regions are included for a user group."""
    print(f"Handling update_user_group_all_regions_included for group_id: {group_id} with allRegionsIncluded: {allRegionsIncluded}", file=sys.stderr)
    
    current_group_data = await get_user_group(group_id) # Added await
    if not current_group_data:
        print(f"User group {group_id} not found. Cannot update all regions included.", file=sys.stderr)
        return None

    payload_dict = {
        "name": current_group_data.get("name"),
        "internetAccess": current_group_data.get("internetAccess"),
        "maxDevice": current_group_data.get("maxDevice"),
        "connectAuth": current_group_data.get("connectAuth"),
        "allRegionsIncluded": allRegionsIncluded, 
        "vpnRegionIds": current_group_data.get("vpnRegionIds"), 
        "gatewaysIds": current_group_data.get("gatewaysIds")
    }
    
    try:
        request_model_instance = UserGroupRequestModel(**payload_dict)
        update_payload = request_model_instance.model_dump(exclude_none=True)
    except Exception as e: 
        print(f"Error creating payload for update_user_group_all_regions_included: {e}", file=sys.stderr)
        raise

    token = config_manager.get_api_token()
    if not token:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for update_user_group_all_regions_included. Please configure the server."))

    api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/user-groups/{group_id}"
    headers = {"accept": "*/*", "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    try:
        async with httpx.AsyncClient() as client: # Use httpx.AsyncClient
            response = await client.put(api_url, headers=headers, json=update_payload)
            response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e: # Changed
        if e.response.status_code == 404:
            return None
        print(f"HTTP error during OpenVPN API call for update_user_group_all_regions_included: {e.response.status_code} - {e.response.text}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API HTTP error for update_user_group_all_regions_included: {e}"))
    except httpx.RequestError as e: # Changed
        print(f"Error calling OpenVPN API for update_user_group_all_regions_included: {e}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for update_user_group_all_regions_included: {e}"))

async def delete_user_group(group_id: str): # Made async
    """Deletes an existing user group by its ID."""
    print(f"Handling delete_user_group for group_id: {group_id}", file=sys.stderr)
    token = config_manager.get_api_token()
    if not token:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for delete_user_group. Please configure the server."))
    api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/user-groups/{group_id}"
    headers = {"accept": "*/*", "Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient() as client: # Use httpx.AsyncClient
            response = await client.delete(api_url, headers=headers)
            response.raise_for_status()
        return {"status": "deleted", "group_id": group_id}
    except httpx.HTTPStatusError as e: # Changed
        if e.response.status_code == 404:
            return None 
        print(f"HTTP error calling OpenVPN API for delete_user_group: {e.response.status_code} - {e.response.text}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API HTTP error for delete_user_group: {e}"))
    except httpx.RequestError as e: # Changed
        print(f"Error calling OpenVPN API for delete_user_group: {e}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for delete_user_group: {e}"))

print("User group tools and models defined. Ready for import by main server.", file=sys.stderr)
