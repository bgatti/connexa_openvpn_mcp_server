# connexa/dynamic_network.py
from typing import List, Dict, Callable, Any, Optional

from .selected_object import CURRENT_SELECTED_OBJECT, SelectedObject # Import SelectedObject for type hint
from .connexa_api import ConnexaAPI # For type hinting and direct calls if necessary

# This module will provide tools that are dynamically available
# when a 'network' object is selected.

def add_connector_to_selected_network(connector_name: str, vpn_region_id: Optional[str] = None) -> str:
    """
    Adds a connector to the currently selected network.
    The network ID and primary region are taken from the selected object.
    An optional vpn_region_id can be provided if the connector needs to be in a
    specific sub-region of the network.
    Upon successful creation, the new connector becomes the currently selected object.

    Args:
        connector_name (str): The name for the new connector.
        vpn_region_id (Optional[str]): Specific VPN region ID for the connector, if different from network's primary.

    Returns:
        str: A message indicating success (and new selection) or failure.
    """
    if CURRENT_SELECTED_OBJECT.object_type != "network" or not CURRENT_SELECTED_OBJECT.object_id:
        return "Error: A network must be selected first using 'select_object_tool'."

    network_id = CURRENT_SELECTED_OBJECT.object_id
    network_name = CURRENT_SELECTED_OBJECT.object_name
    network_details = CURRENT_SELECTED_OBJECT.details
    
    connector_region_id = vpn_region_id if vpn_region_id else network_details.get('region')

    if not connector_region_id:
        return (f"Error: Could not determine region for connector. "
                f"Network details: {network_details}. Please specify vpn_region_id if needed.")

    api = CURRENT_SELECTED_OBJECT.connexa_api
    try:
        response = api.create_connector(
            network_id=network_id,
            name=connector_name,
            vpn_region_id=connector_region_id
        )
        
        if response and response.get('id'): # Check for a successful response indicator
            new_connector_id = response.get('id')
            new_connector_name = response.get('name', connector_name) # Use returned name or fallback
            new_connector_details = response # Store the full API response as details

            # Select the newly created connector
            CURRENT_SELECTED_OBJECT.select(
                object_type="connector", # New object type
                object_id=new_connector_id,
                object_name=new_connector_name,
                details=new_connector_details
            )
            return (f"Connector '{new_connector_name}' (ID: {new_connector_id}) added successfully to network '{network_name}' "
                    f"and is now the selected object.")
        else:
            error_msg = response.get('error', {}).get('message', 'Failed to add connector. API response did not indicate success.')
            return f"Failed to add connector '{connector_name}' to network '{network_name}'. API Error: {error_msg}"

    except AttributeError as e:
        return f"API integration error for 'add_connector': {str(e)}. Check ConnexaAPI method definitions (e.g., create_connector)."
    except Exception as e:
        return f"Error adding connector '{connector_name}': {str(e)}"


def get_dynamic_network_tools() -> List[Dict[str, Any]]:
    """
    Returns a list of tool definitions that are active when a network is selected.
    """
    tools = []
    if CURRENT_SELECTED_OBJECT.object_type == "network" and CURRENT_SELECTED_OBJECT.object_id:
        tools.append(
            {
                "tool_name": "add_connector_to_selected_network",
                "description": (
                    f"Adds a new connector to the currently selected network: '{CURRENT_SELECTED_OBJECT.object_name}'. "
                    "The connector will be associated with this network and its primary region, "
                    "unless a specific vpn_region_id is provided. "
                    "The new connector becomes the selected object upon creation."
                ),
                "function": add_connector_to_selected_network,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "connector_name": {"type": "string", "description": "The desired name for the new connector."},
                        "vpn_region_id": {"type": "string", "description": "(Optional) Specific VPN region ID for the connector if different from the network's primary region."}
                    },
                    "required": ["connector_name"],
                },
            }
        )
        # Add other network-specific tools here
    return tools

if __name__ == "__main__":
    # Example of how this might be used or tested (requires a selected network)
    
    # Mocking for local test:
    # class MockConnexaAPI:
    #     def create_connector(self, network_id, name, vpn_region_id):
    #         print(f"Mock API: Creating connector '{name}' for network '{network_id}' in region '{vpn_region_id}'")
    #         if name == "FailTest":
    #             return {"error": {"message": "Mock API simulated failure."}}
    #         # Simulate a more complete response for the connector
    #         return {
    #             "id": f"conn_{name.lower()}_123", 
    #             "name": name, 
    #             "status": "pending", 
    #             "network_id": network_id,
    #             "region_id": vpn_region_id,
    #             "type": "NETWORK_CONNECTOR" # Example detail
    #         }

    # global_selected_object_instance = SelectedObject() # Create an instance for testing
    # global_selected_object_instance.connexa_api = MockConnexaAPI()
    
    # # Make CURRENT_SELECTED_OBJECT in this test scope refer to our test instance
    # # This is a bit hacky for __main__ testing; in real use, CURRENT_SELECTED_OBJECT is the shared one.
    # _original_current_selected_object = CURRENT_SELECTED_OBJECT
    # globals()['CURRENT_SELECTED_OBJECT'] = global_selected_object_instance


    # global_selected_object_instance.select(
    #     object_type="network",
    #     object_id="net_abc",
    #     object_name="Test Network West",
    #     details={"id": "net_abc", "name": "Test Network West", "region": "us-west-1"}
    # )

    # print("Dynamic tools available for network:", get_dynamic_network_tools())
    # print(f"Selected before: {global_selected_object_instance.get_selected_object_info()}")
    
    # if global_selected_object_instance.object_type == "network":
    #     print("\nTesting add_connector_to_selected_network:")
    #     result_success = add_connector_to_selected_network(connector_name="MyNewConnector1")
    #     print(f"Result 1: {result_success}")
    #     print(f"Selected after success: {global_selected_object_instance.get_selected_object_info()}")

    #     # Re-select network for next test
    #     global_selected_object_instance.select(
    #         object_type="network",
    #         object_id="net_abc",
    #         object_name="Test Network West",
    #         details={"id": "net_abc", "name": "Test Network West", "region": "us-west-1"}
    #     )
    #     print(f"\nSelected before fail test: {global_selected_object_instance.get_selected_object_info()}")
    #     result_fail = add_connector_to_selected_network(connector_name="FailTest")
    #     print(f"Result 2 (failure test): {result_fail}")
    #     print(f"Selected after failure: {global_selected_object_instance.get_selected_object_info()}") # Should still be the network
        
    # else:
    #     print("No network selected, dynamic tools not available.")

    # # Restore original CURRENT_SELECTED_OBJECT if changed
    # globals()['CURRENT_SELECTED_OBJECT'] = _original_current_selected_object
    pass
