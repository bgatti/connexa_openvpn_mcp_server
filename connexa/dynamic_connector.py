# connexa/dynamic_connector.py
from typing import List, Dict, Any

# This module will provide command definitions for 'connector' objects.

def get_connector_command_definitions(connector_id: str, connector_name: str, connector_details: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Returns a list of command definitions available for a connector object.

    Args:
        connector_id (str): The ID of the selected connector.
        connector_name (str): The name of the selected connector.
        connector_details (Dict[str, Any]): The full details of the selected connector.

    Returns:
        List[Dict[str, Any]]: A list of command definitions.
    """
    commands = []
    is_ipsec = connector_details.get("tunnelingProtocol") == "IPSEC"
    # Assuming network connector paths. If host connectors have different paths, logic would need to adapt.
    # The paths here are based on /api/v1/networks/connectors/...
    # If this module should also handle host connectors (e.g. /api/v1/hosts/connectors/...),
    # the path_templates would need to be dynamic based on connector_details.networkItemType or similar.
    # For now, assuming network connectors as per previous context.

    commands.extend([
        {
            "name": "generate_profile",
            "description": f"Generate .ovpn profile for selected connector '{connector_name}'.",
            "method": "post",
            "path_template": f"/api/v1/networks/connectors/{connector_id}/profile",
            "args_schema": {
                "type": "object", "properties": {"vpn_region_id": {"type": "string"}}, "required": ["vpn_region_id"]
            },
            "params_for_call_api": ["vpn_region_id"] 
        },
        {
            "name": "revoke_profile",
            "description": f"Revoke .ovpn profile for selected connector '{connector_name}'.",
            "method": "delete",
            "path_template": f"/api/v1/networks/connectors/{connector_id}/profile",
        },
        {
            "name": "encrypt_profile",
            "description": f"Generate .ovpn profile token for selected connector '{connector_name}'.",
            "method": "post",
            "path_template": f"/api/v1/networks/connectors/{connector_id}/profile/encrypt",
        },
        {
            "name": "get_bundled_app",
            "description": f"Generate an app bundled with profile for selected connector '{connector_name}'.",
            "method": "post",
            "path_template": f"/api/v1/networks/connectors/{connector_id}/profile/bundle",
            "args_schema": {
                "type": "object", "properties": {"type": {"type": "string", "enum": ["DMG", "MSI"]}}, "required": ["type"]
            },
            "params_for_call_api": ["type"] 
        }
    ])

    if is_ipsec:
        commands.extend([
            {
                "name": "ipsec_start",
                "description": f"Start IPsec connection for selected connector '{connector_name}'.",
                "method": "post",
                "path_template": f"/api/v1/networks/connectors/{connector_id}/ipsec/start",
            },
            {
                "name": "ipsec_stop",
                "description": f"Stop IPsec connection for selected connector '{connector_name}'.",
                "method": "post",
                "path_template": f"/api/v1/networks/connectors/{connector_id}/ipsec/stop",
            }
        ])
    
    # Common commands like 'update' and 'delete' are typically added by SelectedObject.get_available_commands()
    # or can be defined here if connector-specific descriptions/handling for update/delete are needed.
    # The 'delete' path for a network connector is /api/v1/networks/connectors/{id}
    # The 'update' path for a network connector is also /api/v1/networks/connectors/{id} with PUT

    return commands

if __name__ == "__main__":
    # Example usage
    mock_conn_id = "conn_xyz789"
    mock_conn_name = "MyVPNConnector"
    mock_conn_details_ovpn = {
        "id": mock_conn_id,
        "name": mock_conn_name,
        "networkItemId": "net_123",
        "networkItemType": "NETWORK",
        "tunnelingProtocol": "OPENVPN",
        "vpnRegionId": "us-west-2"
        # ... other details
    }
    mock_conn_details_ipsec = {
        "id": "conn_ipsec456",
        "name": "MyIPSecConnector",
        "networkItemId": "net_123",
        "networkItemType": "NETWORK",
        "tunnelingProtocol": "IPSEC",
        "vpnRegionId": "eu-central-1"
        # ... other details
    }

    print("--- Commands for OpenVPN Connector ---")
    ovpn_cmds = get_connector_command_definitions(mock_conn_id, mock_conn_name, mock_conn_details_ovpn)
    for cmd_def in ovpn_cmds:
        print(f"  - Command: {cmd_def['name']}, Method: {cmd_def.get('method', 'N/A')}, Path: {cmd_def.get('path_template', 'N/A')}")

    print("\n--- Commands for IPsec Connector ---")
    ipsec_cmds = get_connector_command_definitions("conn_ipsec456", "MyIPSecConnector", mock_conn_details_ipsec)
    for cmd_def in ipsec_cmds:
        print(f"  - Command: {cmd_def['name']}, Method: {cmd_def.get('method', 'N/A')}, Path: {cmd_def.get('path_template', 'N/A')}")
