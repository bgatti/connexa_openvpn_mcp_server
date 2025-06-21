import os
import sys
import logging
import json
from typing import Any, Dict, List, Optional, Tuple, Callable, Union

from .connexa_api import call_api # Import call_api
from .selected_object import CURRENT_SELECTED_OBJECT # Import the global selected object instance

def normalize_object_type(object_type: str) -> str:
    """Normalizes object type string to lowercase and removes hyphens."""
    return object_type.lower().replace("-", "")

# Configure basic logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers(): # Avoid adding multiple handlers if already configured
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr # Or a file, depending on desired output
    )

# Embedded schema content for update requests
# This bypasses loading from swagger.json at runtime
EMBEDDED_UPDATE_SCHEMAS = {
    "DnsRecordRequest": {"type": "object", "properties": {"domain": {"type": "string"}, "description": {"type": "string"}, "ipv4Addresses": {"type": "array", "items": {"type": "string"}}, "ipv6Addresses": {"type": "array", "items": {"type": "string"}}}},
    "AccessGroupRequest": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"}, "source": {"type": "array", "items": {"$ref": "#/components/schemas/AccessItemSourceRequest"}}, "destination": {"type": "array", "items": {"$ref": "#/components/schemas/AccessItemDestinationRequest"}}}},
    "DevicePostureRequest": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"}, "userGroupsIds": {"type": "array", "items": {"type": "string"}}, "windows": {"$ref": "#/components/schemas/WindowsRequest"}, "macos": {"$ref": "#/components/schemas/MacOSRequest"}, "linux": {"$ref": "#/components/schemas/LinuxRequest"}, "android": {"$ref": "#/components/schemas/AndroidRequest"}, "ios": {"$ref": "#/components/schemas/IOSRequest"}}},
    "NetworkUpdateRequest": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"}, "egress": {"type": "boolean"}, "internetAccess": {"type": "string", "enum": ["SPLIT_TUNNEL_ON", "SPLIT_TUNNEL_OFF", "RESTRICTED_INTERNET"]}, "gatewaysIds": {"type": "array", "items": {"type": "string"}}, "tunnelingProtocol": {"type": "string", "enum": ["OPENVPN", "IPSEC"]}}},
    "UserUpdateRequest": {"type": "object", "properties": {"firstName": {"type": "string"}, "lastName": {"type": "string"}, "email": {"type": "string"}, "groupId": {"type": "string"}, "status": {"type": "string", "enum": ["INVITED", "ACTIVE", "SUSPENDED", "SUSPENDED_IDP"]}, "role": {"type": "string", "enum": ["OWNER", "MEMBER", "ADMIN"]}}},
    "UserGroupRequest": {"type": "object", "properties": {"name": {"type": "string"}, "vpnRegionIds": {"type": "array", "items": {"type": "string"}}, "internetAccess": {"type": "string", "enum": ["SPLIT_TUNNEL_ON", "SPLIT_TUNNEL_OFF", "RESTRICTED_INTERNET"]}, "maxDevice": {"type": "integer", "format": "int32"}, "connectAuth": {"type": "string", "enum": ["NO_AUTH", "ON_PRIOR_AUTH", "EVERY_TIME"]}, "allRegionsIncluded": {"type": "boolean"}, "gatewaysIds": {"type": "array", "items": {"type": "string"}}}},
    "HostUpdateRequest": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"}, "internetAccess": {"type": "string", "enum": ["SPLIT_TUNNEL_ON", "SPLIT_TUNNEL_OFF", "RESTRICTED_INTERNET"]}, "domain": {"type": "string"}, "gatewaysIds": {"type": "array", "items": {"type": "string"}}}},
    "DeviceRequest": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"}, "clientUUID": {"type": "string"}}},
    "NetworkConnectorRequest": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"}, "vpnRegionId": {"type": "string"}, "ipSecConfig": {"$ref": "#/components/schemas/IpSecConfigRequest"}}},
    "HostConnectorRequest": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"}, "vpnRegionId": {"type": "string"}}},
    "LocationContextRequest": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"}, "userGroupsIds": {"type": "array", "items": {"type": "string"}}, "ipCheck": {"$ref": "#/components/schemas/IpCheckRequest"}, "countryCheck": {"$ref": "#/components/schemas/CountryCheckRequest"}, "defaultCheck": {"$ref": "#/components/schemas/DefaultCheckRequest"}}}
    # Note: Nested schemas like AccessItemSourceRequest, WindowsRequest, etc. are not fully included here.
    # This provides the top-level structure for update payloads.
}


def _get_swagger_content() -> Dict[str, Any]:
    """Returns the embedded update schemas."""
    # Bypass file loading to avoid environment issues
    return {"components": {"schemas": EMBEDDED_UPDATE_SCHEMAS}}


def get_schema_for_object_type(object_type: str, request_type: str = "update") -> Optional[Dict[str, Any]]:
    """
    Retrieves the JSON schema for a given object type from the embedded schemas.
    request_type is currently ignored as only update schemas are embedded.
    """
    if request_type != "update":
        logger.warning(f"Requested schema for request_type='{request_type}', but only 'update' schemas are embedded.")
        return None

    swagger_content = _get_swagger_content()
    schemas = swagger_content.get("components", {}).get("schemas", {})

    # Use normalized_object_type for consistent lookup
    normalized_object_type = normalize_object_type(object_type)

    schema_name = None

    if normalized_object_type == "network":
        schema_name = "NetworkUpdateRequest"
    elif normalized_object_type == "connector":
        schema_name = "NetworkConnectorRequest" # Assuming NetworkConnectorRequest is used for updates of both
    elif normalized_object_type == "user":
        schema_name = "UserUpdateRequest"
    elif normalized_object_type == "usergroup":
        schema_name = "UserGroupRequest"
    elif normalized_object_type == "host":
        schema_name = "HostUpdateRequest"
    elif normalized_object_type == "device":
        schema_name = "DeviceRequest"
    elif normalized_object_type == "dnsrecord":
        schema_name = "DnsRecordRequest"
    elif normalized_object_type == "accessgroup":
        schema_name = "AccessGroupRequest"
    elif normalized_object_type == "locationcontext":
        schema_name = "LocationContextRequest"
    elif normalized_object_type == "deviceposture":
        schema_name = "DevicePostureRequest"
    elif normalized_object_type in ["networkapplication", "hostapplication"]:
        # Network and Host Applications use the same ApplicationRequest schema for updates
        schema_name = "ApplicationRequest"
    # Add other object types here as needed

    if schema_name and schema_name in schemas:
        logger.info(f"Found schema '{schema_name}' for object_type='{object_type}' (normalized to '{normalized_object_type}'), request_type='{request_type}'")
        return schemas.get(schema_name) # Use .get for safety
    else:
        logger.warning(f"Schema not found in embedded schemas for object_type='{object_type}' (normalized to '{normalized_object_type}'), request_type='{request_type}' (derived schema_name='{schema_name}')")
        return None

async def complete_update_selected(updated_payload: Dict[str, Any]) -> str:
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


    # Check for API restriction on updating OWNER users
    if object_type == "user" and CURRENT_SELECTED_OBJECT.details.get("role") == "OWNER":
        return "Error: Updating users with the 'OWNER' role is restricted by the API."

    api_path = None
    params = None # For query parameters like userId for device update

    # Use normalized_object_type for consistent lookup
    normalized_object_type = object_type.lower().replace("-", "")

    if normalized_object_type == "device":
        user_id = CURRENT_SELECTED_OBJECT.details.get("userId")
        if not user_id:
            return "Error: Cannot update device. 'userId' is missing from the selected device details. Please re-select the device, ensuring it's under a user context if necessary, or that the selection details include 'userId'."
        api_path = f"/api/v1/devices/{object_id}?userId={user_id}"
    elif normalized_object_type == "networkapplication":
        # Use the single ID path as per user feedback
        api_path = f"/api/v1/networks/applications/{object_id}"
        # No need to get networkId from details for the update path
    elif normalized_object_type == "hostapplication":
        # Use the single ID path as per user feedback
        api_path = f"/api/v1/hosts/applications/{object_id}"
        # No need to get hostId from details for the update path
    else:
        # Generic update logic for other object types
        update_path_map = {
            "network": f"/api/v1/networks/{object_id}",
            "connector": f"/api/v1/networks/connectors/{object_id}", # Assuming this path is correct for updates
            "user": f"/api/v1/users/{object_id}",
            "usergroup": f"/api/v1/user-groups/{object_id}",
            "host": f"/api/v1/hosts/{object_id}",
            "dnsrecord": f"/api/v1/dns-records/{object_id}",
            "accessgroup": f"/api/v1/access-groups/{object_id}",
            "locationcontext": f"/api/v1/location-contexts/{object_id}",
            "deviceposture": f"/api/v1/device-postures/{object_id}"
        }
        if normalized_object_type not in update_path_map:
            return f"Error: Update functionality not defined for object type '{object_type}'."
        api_path = update_path_map[normalized_object_type]

    # Filter the updated_payload based on the object's update schema
    schema = get_schema_for_object_type(object_type, request_type="update")
    if not schema or "properties" not in schema:
        logger.warning(f"Could not retrieve or parse update schema for object type '{object_type}'. Proceeding with unfiltered payload.")
        filtered_payload = updated_payload # Use original payload if schema is unavailable
    else:
        allowed_properties = schema["properties"].keys()
        filtered_payload = {k: v for k, v in updated_payload.items() if k in allowed_properties}
        logger.info(f"Filtered payload for update of {object_type}: {json.dumps(filtered_payload)}")


    try:
        # Pass params to call_api if they exist (currently only for device update)
        response = await call_api(action="put", path=api_path, value=filtered_payload, params=params)

        # Check if the status is an integer before comparison
        status_code = response.get("status")
        if isinstance(response, dict) and isinstance(status_code, int) and 200 <= status_code < 300:
            # Successfully updated. Re-select the object to refresh details.
            new_details = response.get("data", {})
            # The name might have changed if it was part of the payload
            new_name = new_details.get("name", object_name) if isinstance(new_details, dict) else object_name

            # Update the selected object with the new details
            CURRENT_SELECTED_OBJECT.select(
                object_type=object_type,
                object_id=object_id, # ID should not change on update
                object_name=new_name,
                details=new_details if isinstance(new_details, dict) else {}
            )
            return f"Successfully updated {object_type} '{new_name}'. Details refreshed. API Response: {response}"
        else:
            # API call failed or returned non-2xx status
            return f"Failed to update {object_type} '{object_name}'. API Response: {response}"
    except Exception as e:
        # Handle exceptions during the API call or processing
        logger.error(f"Error during update execution for {object_type} '{object_name}': {str(e)}", exc_info=True)
        return f"Error during update execution: {str(e)}"


async def get_selected_schema_tool() -> Dict[str, Any]:
    """
    Retrieves the update schema for the currently selected object type.

    Returns:
        Dict[str, Any]: The JSON schema for the selected object type, or an error message.
    """
    if not CURRENT_SELECTED_OBJECT.object_type:
        return {"status": "error", "message": "No object is currently selected."}

    object_type = CURRENT_SELECTED_OBJECT.object_type
    schema = get_schema_for_object_type(object_type, request_type="update")

    if schema:
        return {"status": "success", "object_type": object_type, "schema": schema}
    else:
        return {"status": "not_found", "message": f"Update schema not found for object type: {object_type}."}
