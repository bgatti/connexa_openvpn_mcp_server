import sys
import os
from typing import Optional
from pydantic import BaseModel, Field # Field might not be needed here but good practice
import requests

# Import from the config manager
from . import config_manager # Changed to relative import
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR

# --- DNS Log API Tool Handler Functions (to be decorated in server.py) ---

# Note: The @mcp_dns_log.tool() decorators are removed.
# These functions will be imported into server.py and decorated there.
# Assuming server.py handles config initialization.

def enable_dns_log():
        """Enable DNS Log feature."""
        print("Handling enable_dns_log", file=sys.stderr)
        token = config_manager.get_api_token()
        if not token:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for enable_dns_log. Please configure the server."))
        
        api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/dns-log/user-dns-resolutions/enable"
        headers = {"accept": "*/*", "Authorization": f"Bearer {token}"}
        try:
            response = requests.put(api_url, headers=headers)
            response.raise_for_status()
            # This endpoint returns 200 OK with empty body or simple status
            return {"status": "DNS Log enabled successfully"} if response.ok else response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error in enable_dns_log: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for enable_dns_log: {e}"))

def disable_dns_log():
        """Disable DNS Log feature."""
        print("Handling disable_dns_log", file=sys.stderr)
        token = config_manager.get_api_token()
        if not token:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for disable_dns_log. Please configure the server."))
        
        api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/dns-log/user-dns-resolutions/disable"
        headers = {"accept": "*/*", "Authorization": f"Bearer {token}"}
        try:
            response = requests.put(api_url, headers=headers)
            response.raise_for_status()
            return {"status": "DNS Log disabled successfully"} if response.ok else response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error in disable_dns_log: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for disable_dns_log: {e}"))

def get_user_dns_resolutions(start_hour: str, hours_back: Optional[int] = 1, page: Optional[int] = 0, size: Optional[int] = 500):
        """Get DNS requests sent by user."""
        print(f"Handling get_user_dns_resolutions: startHour={start_hour}, hoursBack={hours_back}, page={page}, size={size}", file=sys.stderr)
        token = config_manager.get_api_token()
        if not token:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="API Token not available for get_user_dns_resolutions. Please configure the server."))
        
        api_url = f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com/api/v1/dns-log/user-dns-resolutions/page"
        params = {
            "startHour": start_hour,
            "hoursBack": hours_back,
            "page": page,
            "size": size
        }
        # Filter out None values from params, as API might not like them
        params = {k: v for k, v in params.items() if v is not None}

        headers = {"accept": "*/*", "Authorization": f"Bearer {token}"}
        try:
            response = requests.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error in get_user_dns_resolutions: {e}", file=sys.stderr)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenVPN API error for get_user_dns_resolutions: {e}"))

# The FastMCP instance (mcp_dns_log) and app_dns_log are no longer defined in this file.
# server.py will handle the FastMCP instance and tool registration.
print("DNS Log tools defined. Ready for import by main server.", file=sys.stderr)
# Note: This file does not define any Pydantic models itself, but uses config_manager.
