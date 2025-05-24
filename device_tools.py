import sys
import os
from typing import List, Optional, Literal, Dict, Any # Added Dict, Any
from pydantic import BaseModel, Field
import requests

# Import from the config manager
from . import config_manager # Changed to relative import
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR # Assuming INTERNAL_ERROR is the main code needed

# --- Pydantic Models for Device API ---
class DeviceRequestModel(BaseModel): # Moved from server.py
    name: str
    description: Optional[str] = None
    clientUUID: Optional[str] = None

# --- Device API Tool Handler Functions (to be decorated in server.py) ---

# Note: The @mcp_devices.tool() decorators are removed.
# These functions will be imported into server.py and decorated there.
# Assuming server.py handles config initialization.

def get_devices(user_id: Optional[str] = None, page: int = 0, size: int = 10):
        """Get a list of devices, optionally filtered by user_id."""
        print(f"Handling get_devices: userId={user_id}, page={page}, size={size}", file=sys.stderr)
        token = config_manager.get_api_token()
        if not token:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for get_devices. Please configure the server."))
        
        api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/devices"
        # Explicitly type params as Dict[str, Any]
        params: Dict[str, Any] = {"page": page, "size": size}
        if user_id:
            params["userId"] = user_id
        
        headers = {"accept": "*/*", "Authorization": f"Bearer {token}"}
        try:
            response = requests.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error in get_devices: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for get_devices: {e}"))

def create_device(user_id: str, device_data: DeviceRequestModel):
        """Create a new device for a user."""
        print(f"Handling create_device for userId={user_id}, data={device_data.model_dump_json(exclude_none=True)}", file=sys.stderr)
        token = config_manager.get_api_token()
        if not token:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for create_device. Please configure the server."))
        
        api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/devices"
        params = {"userId": user_id}
        headers = {"accept": "*/*", "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        try:
            response = requests.post(api_url, headers=headers, params=params, json=device_data.model_dump(mode='json', exclude_none=True))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error in create_device: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for create_device: {e}"))

def get_device_details(device_id: str, user_id: str): # operationId: getDevice
        """Get details for a specific device."""
        print(f"Handling get_device_details for deviceId={device_id}, userId={user_id}", file=sys.stderr)
        token = config_manager.get_api_token()
        if not token:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for get_device_details. Please configure the server."))
        
        api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/devices/{device_id}"
        params = {"userId": user_id}
        headers = {"accept": "*/*", "Authorization": f"Bearer {token}"}
        try:
            response = requests.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404: return None
            print(f"HTTP error in get_device_details: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API HTTP error for get_device_details: {e}"))
        except requests.exceptions.RequestException as e:
            print(f"Error in get_device_details: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for get_device_details: {e}"))

def update_device_details(device_id: str, user_id: str, device_data: DeviceRequestModel): # operationId: updateDevice
        """Update details for a specific device."""
        print(f"Handling update_device_details for deviceId={device_id}, userId={user_id}, data={device_data.model_dump_json(exclude_none=True)}", file=sys.stderr)
        token = config_manager.get_api_token()
        if not token:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for update_device_details. Please configure the server."))
        
        api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/devices/{device_id}"
        params = {"userId": user_id}
        headers = {"accept": "*/*", "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        try:
            response = requests.put(api_url, headers=headers, params=params, json=device_data.model_dump(mode='json', exclude_none=True))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404: return None
            print(f"HTTP error in update_device_details: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API HTTP error for update_device_details: {e}"))
        except requests.exceptions.RequestException as e:
            print(f"Error in update_device_details: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for update_device_details: {e}"))

def delete_device_record(device_id: str, user_id: str): # operationId: deleteDevice
        """Delete a specific device."""
        print(f"Handling delete_device_record for deviceId={device_id}, userId={user_id}", file=sys.stderr)
        token = config_manager.get_api_token()
        if not token:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for delete_device_record. Please configure the server."))
        
        api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/devices/{device_id}"
        params = {"userId": user_id}
        headers = {"accept": "*/*", "Authorization": f"Bearer {token}"}
        try:
            response = requests.delete(api_url, headers=headers, params=params)
            response.raise_for_status() # Expect 204 No Content
            return {"status": "deleted", "device_id": device_id, "user_id": user_id}
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404: return None
            print(f"HTTP error in delete_device_record: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API HTTP error for delete_device_record: {e}"))
        except requests.exceptions.RequestException as e:
            print(f"Error in delete_device_record: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for delete_device_record: {e}"))

def generate_device_profile(device_id: str, user_id: str, region_id: str):
        """Generate .ovpn profile for an existing device."""
        print(f"Handling generate_device_profile for deviceId={device_id}, userId={user_id}, regionId={region_id}", file=sys.stderr)
        token = config_manager.get_api_token()
        if not token:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for generate_device_profile. Please configure the server."))

        api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/devices/{device_id}/profile"
        params = {"userId": user_id, "regionId": region_id}
        headers = {"accept": "*/*", "Authorization": f"Bearer {token}"}
        try:
            response = requests.post(api_url, headers=headers, params=params)
            response.raise_for_status()
            # The response is typically the profile content as a string, not JSON
            return response.text 
        except requests.exceptions.RequestException as e:
            print(f"Error in generate_device_profile: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for generate_device_profile: {e}"))

def revoke_device_profile(device_id: str, user_id: str):
        """Revoke profile for an existing device."""
        print(f"Handling revoke_device_profile for deviceId={device_id}, userId={user_id}", file=sys.stderr)
        token = config_manager.get_api_token()
        if not token:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for revoke_device_profile. Please configure the server."))

        api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/devices/{device_id}/profile"
        params = {"userId": user_id}
        headers = {"accept": "*/*", "Authorization": f"Bearer {token}"}
        try:
            response = requests.delete(api_url, headers=headers, params=params)
            response.raise_for_status()
             # The response is typically a string (e.g. "true" or "false") or 200 OK with simple body
            return response.text # Or response.json() if it returns JSON
        except requests.exceptions.RequestException as e:
            print(f"Error in revoke_device_profile: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for revoke_device_profile: {e}"))

# The FastMCP instance (mcp_devices) and app_devices are no longer defined in this file.
# server.py will handle the FastMCP instance and tool registration.
print("Device tools and models defined. Ready for import by main server.", file=sys.stderr)
