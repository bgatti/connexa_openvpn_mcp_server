import sys
import os
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
import requests

# Import from the config manager
from . import config_manager # Changed to relative import
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR

# --- Pydantic Models for Device Posture API ---
# Based on swagger.json components.schemas
class VersionPolicyModel(BaseModel):
    version: Optional[str] = None
    condition: Optional[Literal["GTE", "LTE", "EQUAL"]] = None

class DiskEncryptionModel(BaseModel):
    type: Optional[Literal["FULL_DISK", "SPECIFIC_VOLUME"]] = None
    volume: Optional[str] = None

class WindowsPolicyModel(BaseModel):
    allowed: bool
    version: Optional[VersionPolicyModel] = None
    antiviruses: Optional[List[Literal[
        "AVAST", "AVG", "AVIRA", "BITDEFENDER", "CROWDSTRIKE_FALCON", 
        "ESET", "MALWAREBYTES", "MCAFEE", "MICROSOFT_DEFENDER", "NORTON", "SENTINEL_ONE"
    ]]] = None
    diskEncryption: Optional[DiskEncryptionModel] = None
    certificate: Optional[str] = None

class MacOSPolicyModel(BaseModel):
    allowed: bool
    version: Optional[VersionPolicyModel] = None
    antiviruses: Optional[List[Literal[
        "AVAST", "AVG", "AVIRA", "BITDEFENDER", "CROWDSTRIKE_FALCON", 
        "ESET", "MALWAREBYTES", "MCAFEE", "MICROSOFT_DEFENDER", "NORTON", "SENTINEL_ONE"
    ]]] = None
    diskEncrypted: Optional[bool] = None # Swagger shows boolean for macOS
    certificate: Optional[str] = None

class LinuxPolicyModel(BaseModel):
    allowed: bool

class AndroidPolicyModel(BaseModel):
    allowed: bool

class IOSPolicyModel(BaseModel):
    allowed: bool

class DevicePostureRequestModel(BaseModel):
    name: str
    description: Optional[str] = None
    userGroupsIds: Optional[List[str]] = None
    windows: Optional[WindowsPolicyModel] = None
    macos: Optional[MacOSPolicyModel] = None
    linux: Optional[LinuxPolicyModel] = None
    android: Optional[AndroidPolicyModel] = None
    ios: Optional[IOSPolicyModel] = None

# --- Device Posture API Tool Handler Functions (to be decorated in server.py) ---

# Note: The @mcp_device_posture.tool() decorators are removed.
# These functions will be imported into server.py and decorated there.
# Assuming server.py handles config initialization.

def get_device_posture_policies(page: int = 0, size: int = 10): # operationId: get_2
        """Get a list of device posture policies."""
        print(f"Handling get_device_posture_policies: page={page}, size={size}", file=sys.stderr)
        token = config_manager.get_api_token()
        if not token:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for get_device_posture_policies. Please configure the server."))
        api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/device-postures"
        params = {"page": page, "size": size}
        headers = {"accept": "*/*", "Authorization": f"Bearer {token}"}
        try:
            response = requests.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error in get_device_posture_policies: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for get_device_posture_policies: {e}"))

def create_device_posture_policy(policy_data: DevicePostureRequestModel): # operationId: create_1
        """Create a new device posture policy."""
        print(f"Handling create_device_posture_policy: data={policy_data.model_dump_json(exclude_none=True)}", file=sys.stderr)
        token = config_manager.get_api_token()
        if not token:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for create_device_posture_policy. Please configure the server."))
        api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/device-postures"
        headers = {"accept": "*/*", "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        try:
            response = requests.post(api_url, headers=headers, json=policy_data.model_dump(mode='json', exclude_none=True))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error in create_device_posture_policy: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for create_device_posture_policy: {e}"))

def get_device_posture_policy_details(policy_id: str): # operationId: get_3 (renamed from id to policy_id for clarity)
        """Get details for a specific device posture policy."""
        print(f"Handling get_device_posture_policy_details for policyId={policy_id}", file=sys.stderr)
        token = config_manager.get_api_token()
        if not token:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for get_device_posture_policy_details. Please configure the server."))
        api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/device-postures/{policy_id}"
        headers = {"accept": "*/*", "Authorization": f"Bearer {token}"}
        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404: return None
            print(f"HTTP error in get_device_posture_policy_details: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API HTTP error for get_device_posture_policy_details: {e}"))
        except requests.exceptions.RequestException as e:
            print(f"Error in get_device_posture_policy_details: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for get_device_posture_policy_details: {e}"))

def update_device_posture_policy_details(policy_id: str, policy_data: DevicePostureRequestModel): # operationId: update_1
        """Update details for a specific device posture policy."""
        print(f"Handling update_device_posture_policy for policyId={policy_id}, data={policy_data.model_dump_json(exclude_none=True)}", file=sys.stderr)
        token = config_manager.get_api_token()
        if not token:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for update_device_posture_policy_details. Please configure the server."))
        api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/device-postures/{policy_id}"
        headers = {"accept": "*/*", "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        try:
            response = requests.put(api_url, headers=headers, json=policy_data.model_dump(mode='json', exclude_none=True))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404: return None
            print(f"HTTP error in update_device_posture_policy: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API HTTP error for update_device_posture_policy_details: {e}"))
        except requests.exceptions.RequestException as e:
            print(f"Error in update_device_posture_policy: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for update_device_posture_policy_details: {e}"))

def delete_device_posture_policy_record(policy_id: str): # operationId: delete_1
        """Delete a specific device posture policy."""
        print(f"Handling delete_device_posture_policy for policyId={policy_id}", file=sys.stderr)
        token = config_manager.get_api_token()
        if not token:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for delete_device_posture_policy_record. Please configure the server."))
        api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/device-postures/{policy_id}"
        headers = {"accept": "*/*", "Authorization": f"Bearer {token}"}
        try:
            response = requests.delete(api_url, headers=headers)
            response.raise_for_status() # Expect 200 OK with body for delete in this case based on swagger
            return response.json() # Swagger indicates 200 OK with a body, not 204
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404: return None
            print(f"HTTP error in delete_device_posture_policy: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API HTTP error for delete_device_posture_policy_record: {e}"))
        except requests.exceptions.RequestException as e:
            print(f"Error in delete_device_posture_policy: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for delete_device_posture_policy_record: {e}"))

# The FastMCP instance (mcp_device_posture) and app_device_posture are no longer defined in this file.
# server.py will handle the FastMCP instance and tool registration.
print("Device Posture tools and models defined. Ready for import by main server.", file=sys.stderr)
