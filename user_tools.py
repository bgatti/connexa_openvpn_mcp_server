import sys
import os
from typing import List, Optional, Literal, Dict, Any # Type import removed
from pydantic import BaseModel, Field # Field imported
import requests
import httpx # Added for async client

# Import from the new config manager
from .connexa import config_manager # Changed to relative import
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS # Assuming these codes are relevant

# --- Async HTTP Client Utility ---
async def get_async_client() -> httpx.AsyncClient:
    """
    Creates and returns an httpx.AsyncClient configured with the API token.
    """
    token = config_manager.get_api_token()
    if not token:
        # This function is called by tools/resources, so raising McpError is appropriate
        raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available. Please configure the server."))
    
    headers = {
        "accept": "*/*",
        "Authorization": f"Bearer {token}"
    }
    # Consider adding timeout configurations here if needed
    return httpx.AsyncClient(headers=headers, base_url=f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com")

# --- Pydantic Models for User API ---
# DeviceRequestModel is used internally by UserCreateRequestModel
class DeviceRequestModel(BaseModel): 
    name: str
    description: Optional[str] = None
    clientUUID: Optional[str] = None
    # No Config.schema_extra needed here as descriptions are for tool inputs

# UserCreateRequestModel is used internally by the create_user tool
class UserCreateRequestModel(BaseModel):
    firstName: str
    lastName: str
    username: str
    email: str
    groupId: str
    role: Literal["OWNER", "MEMBER", "ADMIN"]
    devices: Optional[List[DeviceRequestModel]] = None # This remains for the internal model structure
    # No Config.schema_extra needed here

class UserUpdateRequestModel(BaseModel): 
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[str] = None
    groupId: Optional[str] = None
    status: Optional[Literal["INVITED", "ACTIVE", "SUSPENDED", "SUSPENDED_IDP"]] = None
    role: Optional[Literal["OWNER", "MEMBER", "ADMIN"]] = None
    # devices field removed from UserUpdateRequestModel

# --- User API Tool Handler Functions (to be decorated in server.py) ---

# Note: The @mcp_users.tool() decorators are removed. 
# These functions will be imported into server.py and decorated there.

# It's good practice to ensure config is initialized if these tools are ever called.
# However, the primary initialization should be managed by the main server.py.
# For safety, a check can remain, or be centralized in server.py before tool registration.
# For now, let's assume server.py handles config initialization before registering tools.

def get_users(page: int = 0, size: int = 10):
        print(f"Handling get_users with args: page={page}, size={size}", file=sys.stderr)
        token = config_manager.get_api_token()
        if not token:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for get_users. Please configure the server."))
        api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/users?page={page}&size={size}"
        headers = {"accept": "*/*", "Authorization": f"Bearer {token}"}
        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error calling OpenVPN API for get_users: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for get_users: {e}"))

def get_user(user_id: str):
        print(f"Handling get_user for user_id: {user_id}", file=sys.stderr)
        token = config_manager.get_api_token()
        if not token:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for get_user. Please configure the server."))
        api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/users/{user_id}"
        headers = {"accept": "*/*", "Authorization": f"Bearer {token}"}
        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404: 
                # Returning None is fine if the tool's return type is Optional.
                # Otherwise, raise an McpError for not found.
                # Assuming Optional return for now.
                return None 
            print(f"HTTP error calling OpenVPN API for get_user: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API HTTP error for get_user: {e}"))
        except requests.exceptions.RequestException as e:
            print(f"Error calling OpenVPN API for get_user: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for get_user: {e}"))

# Note: The @mcp.tool() decorator will be applied in server.py
def create_user(
    firstName: str = Field(description="User's first name."),
    lastName: str = Field(description="User's last name."),
    username: str = Field(description="Username for the user. This will be used for login."),
    email: str = Field(description="User's email address."),
    groupId: str = Field(description="ID of the group the user belongs to."),
    role: Literal["OWNER", "MEMBER", "ADMIN"] = Field(description="Role of the user. Must be one of: OWNER, MEMBER, ADMIN.")
    # Devices parameter removed from create_user signature
):
    """Creates a new user with the specified details. Devices must be added separately."""
    
    # Devices are no longer handled at creation time via this function's direct parameters.
    # The UserCreateRequestModel will be instantiated with devices=None.
    user_data_model = UserCreateRequestModel(
        firstName=firstName,
        lastName=lastName,
        username=username,
        email=email,
        groupId=groupId,
        role=role,
        devices=None # Explicitly setting to None as devices are handled by a separate tool
    )

    print(f"Handling create_user with data (devices excluded): {user_data_model.model_dump_json(exclude_none=True)}", file=sys.stderr)
    token = config_manager.get_api_token()
    if not token:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for create_user. Please configure the server."))
    
    api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/users"
    headers = {"accept": "*/*", "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    try:
        payload = user_data_model.model_dump(mode='json', exclude_none=True)
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling OpenVPN API for create_user: {e}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for create_user: {e}"))

def update_user(
    user_id: str,
    firstName: Optional[str] = Field(default=None, description="User's first name."),
    lastName: Optional[str] = Field(default=None, description="User's last name."),
    email: Optional[str] = Field(default=None, description="User's email address."),
    groupId: Optional[str] = Field(default=None, description="ID of the group the user belongs to."),
    status: Optional[Literal["INVITED", "ACTIVE", "SUSPENDED", "SUSPENDED_IDP"]] = Field(default=None, description="Status of the user."),
    role: Optional[Literal["OWNER", "MEMBER", "ADMIN"]] = Field(default=None, description="Role of the user.")
):
    """Updates an existing user with the specified details."""
    print(f"Handling update_user for user_id: {user_id}", file=sys.stderr)

    # Get current user data
    current_user_data = get_user(user_id)
    if not current_user_data:
        print(f"User {user_id} not found. Cannot update.", file=sys.stderr)
        return None

    # Update only the provided fields in the current user data
    update_payload_dict = {}
    if firstName is not None:
        current_user_data["firstName"] = firstName
        update_payload_dict["firstName"] = firstName
    if lastName is not None:
        current_user_data["lastName"] = lastName
        update_payload_dict["lastName"] = lastName
    if email is not None:
        current_user_data["email"] = email
        update_payload_dict["email"] = email
    if groupId is not None:
        current_user_data["groupId"] = groupId
        update_payload_dict["groupId"] = groupId
    if status is not None:
        current_user_data["status"] = status
        update_payload_dict["status"] = status
    if role is not None:
        current_user_data["role"] = role
        update_payload_dict["role"] = role

    if not update_payload_dict:
        print(f"Handling update_user for user_id: {user_id} with no data to update.", file=sys.stderr)
        return {"message": "No update data provided."}

    # Prepare the full user object for the PUT request
    # Exclude 'devices' and 'connectionStatus' as they are not part of the request model
    full_update_payload = {
        "firstName": current_user_data.get("firstName"),
        "lastName": current_user_data.get("lastName"),
        "username": current_user_data.get("username"), # Include username as it's required by the API for PUT
        "email": current_user_data.get("email"),
        "groupId": current_user_data.get("groupId"),
        "status": current_user_data.get("status"),
        "role": current_user_data.get("role")
    }

    # Validate the payload against the Pydantic model (optional but good practice)
    try:
        UserUpdateRequestModel(**full_update_payload) # Use UserUpdateRequestModel for validation
    except Exception as e:
        print(f"Payload validation failed for update_user: {e}", file=sys.stderr)
        raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Invalid payload structure for update_user: {e}"))


    print(f"Handling update_user for user_id: {user_id} with full payload: {full_update_payload}", file=sys.stderr)
    token = config_manager.get_api_token()
    if not token:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for update_user. Please configure the server."))

    api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/users/{user_id}"
    headers = {"accept": "*/*", "Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        response = requests.put(api_url, headers=headers, json=full_update_payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None
        print(f"HTTP error calling OpenVPN API for update_user: {e.response.status_code} - {e.response.text}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API HTTP error for update_user: {e}"))
    except requests.exceptions.RequestException as e:
        print(f"Error calling OpenVPN API for update_user: {e}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for update_user: {e}"))

def delete_user(user_id: str):
        print(f"Handling delete_user for user_id: {user_id}", file=sys.stderr)
        token = config_manager.get_api_token()
        if not token:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for delete_user. Please configure the server."))
        api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/users/{user_id}"
        headers = {"accept": "*/*", "Authorization": f"Bearer {token}"}
        try:
            response = requests.delete(api_url, headers=headers)
            response.raise_for_status()
            return {"status": "deleted", "user_id": user_id}
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # Assuming Optional return or specific error for not found
                return None 
            print(f"HTTP error calling OpenVPN API for delete_user: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API HTTP error for delete_user: {e}"))
        except requests.exceptions.RequestException as e:
            print(f"Error calling OpenVPN API for delete_user: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for delete_user: {e}"))

# The FastMCP instance (mcp_users) and app_users are no longer defined in this file.
# server.py will handle the FastMCP instance and tool registration.
print("User tools, models, and async client utility defined. Ready for import by main server.", file=sys.stderr)
