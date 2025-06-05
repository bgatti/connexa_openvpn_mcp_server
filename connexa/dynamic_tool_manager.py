# connexa/dynamic_tool_manager.py
import logging
from typing import List, Dict, Optional, Any

# This module is being refactored.
# The old concept of dynamically registering/unregistering specific tools
# is replaced by generic tools (act_on_selected_object) that internally
# adapt based on the selected object type by using command definitions.

# Functions like get_dynamic_network_tools are replaced by 
# get_network_command_definitions in dynamic_network.py, etc.
# These are consumed by SelectedObject.get_available_commands().

logger = logging.getLogger(__name__)

# _active_dynamic_tools is no longer the primary way to manage tools.
# The main tools (select_object_tool, act_on_selected_object, complete_update_selected)
# will be registered statically by the server.
# This list might be used by a hypothetical MCP client feature to *update tool descriptions*,
# but not for adding/removing tools themselves.
_current_dynamic_tool_descriptions: List[Dict[str, Any]] = []


def update_tool_descriptions_for_selection(object_type: Optional[str], selected_object_details: Optional[Dict[str, Any]] = None):
    """
    Placeholder: Updates descriptions for generic tools based on selection.
    This function's utility depends on whether the MCP client supports dynamic updates
    to tool descriptions or schemas.
    For now, it logs the selection change.
    """
    global _current_dynamic_tool_descriptions
    _current_dynamic_tool_descriptions = [] # Clear previous

    logger.info(f"Selection changed. Object type: {object_type}")
    if object_type and selected_object_details:
        logger.info(f"Selected object name: {selected_object_details.get('name', 'N/A')}")
        # Example: If act_on_selected_object tool's description could be updated:
        # new_description = f"Acts on the currently selected {object_type}: {selected_object_details.get('name')}. Use 'list_available_commands' for options."
        # _current_dynamic_tool_descriptions.append({"tool_name": "act_on_selected_object", "new_description": new_description})
        # The MCP server would then need a mechanism to push this updated description to the client.
    else:
        logger.info("Selection cleared or no specific object type.")
    
    # This function doesn't return tools to be registered/unregistered anymore.
    # It would interact with an MCP client mechanism if available.


def get_updated_tool_descriptions() -> List[Dict[str, Any]]:
    """
    Placeholder: Returns descriptions that might need updating on the client.
    """
    return _current_dynamic_tool_descriptions


def register_selection_listener(selected_object_instance):
    """
    Registers a listener for selection changes.
    This listener will call update_tool_descriptions_for_selection.
    """
    
    def selection_change_listener(object_type: Optional[str]):
        from .selected_object import CURRENT_SELECTED_OBJECT # Local import
        
        current_details = None
        if object_type and CURRENT_SELECTED_OBJECT.object_type == object_type:
            current_details = CURRENT_SELECTED_OBJECT.details
            
        update_tool_descriptions_for_selection(object_type, current_details)

    selected_object_instance.register_listener(selection_change_listener)
    logger.info("Selection change listener registered with SelectedObject (for dynamic_tool_manager).")

# The main server will be responsible for registering the core tools from selected_object.py:
# - select_object_tool
# - act_on_selected_object
# - complete_update_selected
# These are now considered static tools whose internal behavior (commands) is dynamic.
