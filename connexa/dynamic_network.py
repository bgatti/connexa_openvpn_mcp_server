# connexa/dynamic_network.py
from typing import List, Dict, Callable, Any, Optional

# No longer need CURRENT_SELECTED_OBJECT here as command definitions will be context-agnostic
# and act_on_selected_object will use the currently selected one.
# from .selected_object import CURRENT_SELECTED_OBJECT, SelectedObject 
# from .connexa_api import call_api # call_api is used by act_on_selected_object

# This module will provide command definitions for 'network' objects.

def get_network_command_definitions(network_id: str, network_name: str, network_details: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Returns a list of command definitions available for a network object.

    Args:
        network_id (str): The ID of the selected network.
        network_name (str): The name of the selected network.
        network_details (Dict[str, Any]): The full details of the selected network.

    Returns:
        List[Dict[str, Any]]: A list of command definitions.
    """
    commands = []

    # Command to add a connector to this network
    # This definition was previously in SelectedObject.get_available_commands
    commands.append({
        "name": "add_connector",
        "description": f"Add a new connector to the selected network '{network_name}'.",
        "method": "post",
        "path_template": f"/api/v1/networks/{network_id}/connectors", # Path uses the provided network_id
        "args_schema": { # Arguments for the 'add_connector' command itself
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name for the new connector."},
                "vpn_region_id": {"type": "string", "description": "VPN region ID for the connector."},
                # Optional: "description": {"type": "string"},
                # Optional: "ipSecConfig": {"type": "object", "description": "IPSec configuration if creating an IPsec connector"}
            },
            "required": ["name", "vpn_region_id"]
        },
        # This tells act_on_selected_object that the command_args for this command
        # should be used as the JSON body for the POST request.
        # It also implies that the command_args should match the schema for NetworkConnectorRequest.
        "payload_schema_ref": "NetworkConnectorRequest" 
    })

    # Add other network-specific command definitions here.
    # For example, commands to manage network routes, IP services, applications associated with this network.
    # Example: list_network_routes, add_network_route, etc.
    # These would have their own "method", "path_template", "args_schema", etc.

    # Common commands like 'update' and 'delete' are added by SelectedObject.get_available_commands()
    # if their path_templates are defined there.
    # Alternatively, they can also be defined here if more specific descriptions or handling is needed for networks.

    return commands

if __name__ == "__main__":
    # Example of how this might be used or tested
    # This module now primarily provides data (command definitions)
    # and doesn't execute logic itself directly in the same way as before.
    
    # Mock network data for testing get_network_command_definitions
    mock_net_id = "net_123"
    mock_net_name = "My Test Network"
    mock_net_details = {
        "id": mock_net_id,
        "name": mock_net_name,
        "region": "us-east-1",
        "connectors": [] 
        # ... other details
    }

    network_cmds = get_network_command_definitions(mock_net_id, mock_net_name, mock_net_details)
    print(f"Commands for network '{mock_net_name}':")
    for cmd_def in network_cmds:
        print(f"  - Command: {cmd_def['name']}")
        print(f"    Description: {cmd_def['description']}")
        if cmd_def.get('args_schema'):
            print(f"    Args Schema: {cmd_def['args_schema']}")
        print("-" * 20)
    
    # The actual execution of these commands would be handled by 
    # 'act_on_selected_object' using these definitions.
    pass
