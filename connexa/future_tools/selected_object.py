# connexa/selected_object.py
import os
from typing import Any, Dict, List, Optional, Tuple, Callable

from .connexa_api import ConnexaAPI # Assuming ConnexaAPI can be imported

# Environment variables for default region
CONNEXA_REGION = os.getenv("CONNEXA_REGION", "us-west-1")

class SelectedObject:
    """
    Represents the currently selected object in the MCP server.
    This object's state will determine which dynamic tools are available.
    """
    def __init__(self):
        self.object_type: Optional[str] = None
        self.object_id: Optional[str] = None
        self.object_name: Optional[str] = None
        self.details: Dict[str, Any] = {}
        self.connexa_api = ConnexaAPI() # Initialize the API
        self._listeners: List[Callable[[Optional[str]], None]] = [] # Listeners for selection changes

    def register_listener(self, listener: Callable[[Optional[str]], None]):
        """Register a callback function to be notified of selection changes."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def _notify_listeners(self):
        """Notify all registered listeners about the selection change."""
        for listener in self._listeners:
            try:
                listener(self.object_type) # Pass the new object type
            except Exception as e:
                print(f"Error notifying listener {listener}: {e}")

    def select(self, object_type: str, object_id: Optional[str], object_name: Optional[str], details: Dict[str, Any]):
        self.object_type = object_type
        self.object_id = object_id
        self.object_name = object_name
        self.details = details
        print(f"SelectedObject: Selected {object_type} - {object_name} (ID: {object_id})")
        self._notify_listeners()

    def clear(self):
        self.object_type = None
        self.object_id = None
        self.object_name = None
        self.details = {}
        print("SelectedObject: Cleared selection.")
        self._notify_listeners()

    def get_selected_object_info(self) -> Dict[str, Any]:
        return {
            "type": self.object_type,
            "id": self.object_id,
            "name": self.object_name,
            "details": self.details,
        }

# Global instance of the selected object. This will be imported by other modules.
CURRENT_SELECTED_OBJECT = SelectedObject()


def select_object_tool(object_type: str, name_search: Optional[str] = None, **kwargs) -> Tuple[List[str], str]:
    """
    Tool to select an object (e.g., Network, User, Group) by type and optional name search.

    Args:
        object_type (str): The type of object to select (e.g., "network", "user").
        name_search (Optional[str]): A search term to filter objects by name.
                                     If "Default", empty, or multiple matches, selects the default.
        **kwargs: Additional search parameters (e.g., status="connected").

    Returns:
        Tuple[List[str], str]: A list of matching object names and the name of the selected object.
                               Returns an error message if the type is unsupported or an API error occurs.
    """
    api = CURRENT_SELECTED_OBJECT.connexa_api
    found_objects = []
    selected_object_name = "None"
    default_object_name = "Default" # Placeholder for actual default logic

    if object_type.lower() == "network":
        try:
            networks = api.get_networks() # Assuming this method exists and returns a list of network dicts
            
            # Determine default network (e.g., the first one or one marked as default by API)
            # For now, let's assume the API can provide a default or we pick the first one.
            if networks:
                # This is a placeholder. Real default logic would be more robust.
                # E.g., check for a 'default' flag or a specific name.
                # The user mentioned "owner user etc" for default, which implies complex logic.
                # For networks, a common default might be the one in the CONNEXA_REGION.
                default_network_candidates = [n for n in networks if n.get('region') == CONNEXA_REGION]
                if default_network_candidates:
                    default_object_name = default_network_candidates[0].get('name', 'Unknown Default Network')
                    default_object_id = default_network_candidates[0].get('id')
                    default_details = default_network_candidates[0]
                elif networks: # Fallback if no network in default region
                    default_object_name = networks[0].get('name', 'Unknown Default Network')
                    default_object_id = networks[0].get('id')
                    default_details = networks[0]
                else: # No networks at all
                    default_object_name = "No Networks Found"
                    default_object_id = None
                    default_details = {}

            else: # No networks found
                CURRENT_SELECTED_OBJECT.clear()
                return ["No networks found."], "No networks available to select."

            if name_search and name_search.lower() != "default":
                # Filter by name_search (case-insensitive partial match)
                # Also consider kwargs for additional filtering, e.g., status
                # For now, simple name search
                for net in networks:
                    if name_search.lower() in net.get("name", "").lower():
                        # Apply additional filters from kwargs if any
                        match_all_kwargs = True
                        for key, value in kwargs.items():
                            # This is a simple exact match for now.
                            # Could be extended for more complex queries (e.g. status="connected")
                            if str(net.get(key)).lower() != str(value).lower():
                                match_all_kwargs = False
                                break
                        if match_all_kwargs:
                            found_objects.append(net)
            else: # No search term, or "default"
                found_objects = networks # Show all networks if no specific search

            # Prepare list of names for return
            found_object_names = [obj.get("name", "Unnamed") for obj in found_objects]

            if name_search and name_search.lower() != "default" and len(found_objects) == 1:
                # Exactly one match for a specific search term
                selected = found_objects[0]
                CURRENT_SELECTED_OBJECT.select(
                    object_type="network",
                    object_id=selected.get("id"),
                    object_name=selected.get("name"),
                    details=selected
                )
                selected_object_name = selected.get("name", "Unnamed")
            else:
                # Default selection:
                # - name_search is "Default"
                # - name_search is blank
                # - name_search yields 0 or multiple results
                if default_object_id: # Ensure a default was actually found
                    CURRENT_SELECTED_OBJECT.select(
                        object_type="network",
                        object_id=default_object_id,
                        object_name=default_object_name,
                        details=default_details
                    )
                    selected_object_name = default_object_name
                else: # No default could be determined (e.g. no networks at all)
                    CURRENT_SELECTED_OBJECT.clear()
                    selected_object_name = "No default network available."
            
            return found_object_names, f"Selected Object is {selected_object_name}"

        except Exception as e:
            CURRENT_SELECTED_OBJECT.clear()
            return [], f"Error fetching networks: {str(e)}"
            
    # Add other object types (user, group) here later
    # elif object_type.lower() == "user":
    #     pass
    # elif object_type.lower() == "usergroup":
    #     pass
    else:
        CURRENT_SELECTED_OBJECT.clear()
        return [], f"Unsupported object type: {object_type}. Supported types: network."

# Example usage (for testing, not part of the tool itself)
if __name__ == "__main__":
    # This requires ConnexaAPI to be functional and configured
    # print("Attempting to select default network...")
    # names, selection_msg = select_object_tool(object_type="network")
    # print(f"Found: {names}, Message: {selection_msg}")
    # print(f"Current selection: {CURRENT_SELECTED_OBJECT.get_selected_object_info()}")

    # print("\nAttempting to select network 'California'...")
    # names, selection_msg = select_object_tool(object_type="network", name_search="California")
    # print(f"Found: {names}, Message: {selection_msg}")
    # print(f"Current selection: {CURRENT_SELECTED_OBJECT.get_selected_object_info()}")
    
    # print("\nAttempting to select a specific network (if one exists with a unique name)...")
    # This part would need a known unique network name from your Connexa setup
    # For example, if you have a network named "MyUniqueNet"
    # names, selection_msg = select_object_tool(object_type="network", name_search="MyUniqueNet")
    # print(f"Found: {names}, Message: {selection_msg}")
    # print(f"Current selection: {CURRENT_SELECTED_OBJECT.get_selected_object_info()}")
    pass
