import asyncio # Needed for asyncio.to_thread
from mcp.server.fastmcp import FastMCP
from .group_tools import get_user_groups, get_user_group # Import both functions

async def get_user_groups_resource(mcp: FastMCP): # mcp might not be needed if not using tool_manager
    """
    Fetches user groups and returns pertinent information for each group
    by calling the 'get_user_groups' tool internally.
    """
    try:
        # Call the synchronous get_user_groups function from group_tools.py
        # in a separate thread to avoid blocking the asyncio event loop.
        # The get_user_groups function takes 'page' and 'size' as arguments.
        tool_result = await asyncio.to_thread(get_user_groups, page=0, size=100)

        # The original code checked for `tool_result is None`.
        # The get_user_groups function in group_tools.py returns response.json() or raises McpError.
        # It doesn't seem to return None for "no groups found" but might if an API call leads to that.
        # A 404 in get_user_group (singular) returns None, but get_user_groups (plural) doesn't show this.
        # An empty list [] is more likely for "no groups".
        # If an error occurs, McpError is raised, which will be caught by the except block.
        # So, `tool_result is None` might be an unlikely path unless the API itself returns null.
        if tool_result is None: 
            # Consider if the tool might return an empty list for no groups vs. None for an error
            # Based on typical API behavior, an empty list is more common for "no results".
            # If None signifies an error, this check is good.
            # If the tool itself raises an exception on error, this 'if' might not be hit for errors.
            return {"error": "Failed to fetch user groups or no groups found. Tool returned None."}

        # Assuming tool_result is a list of group objects (dictionaries).
        # Example structure of a single group object from the API (as per MCP server docs):
        # {
        #   "id": "group_id_1",
        #   "name": "Developers",
        #   "internetAccess": "SPLIT_TUNNEL_ON",
        #   "maxDevice": 5,
        #   "connectAuth": "NO_AUTH",
        #   ... (other fields)
        # }

        processed_groups = []
        if isinstance(tool_result, list): # Ensure tool_result is a list before iterating
            for group in tool_result:
                if isinstance(group, dict): # Ensure each item is a dictionary
                    processed_groups.append({
                        "id": group.get("id"),
                        "name": group.get("name"),
                        "internet_access": group.get("internetAccess"),
                        "max_devices": group.get("maxDevice"),
                        "connection_auth": group.get("connectAuth")
                    })
                else:
                    # Log or handle items in tool_result that are not dicts
                    pass # Or mcp.logger.warning(f"Skipping non-dict item in group results: {group}")
        else:
            # Log or handle cases where tool_result is not a list
            # This could indicate an unexpected response format from the tool
            return {"error": f"Unexpected data format from get_user_groups tool. Expected list, got {type(tool_result)}."}
            
        return {"user_groups": processed_groups}

    except Exception as e:
        # Log the exception, e.g., using mcp.logger if available and configured
        # For now, just returning the error string
        # Consider using mcp.logger.error(f"Error in get_user_groups_resource: {e}", exc_info=True)
        return {"error": f"An error occurred while fetching user groups: {str(e)}"}

# Next steps:
# 1. Register this resource function in server.py using `app.resource()`. (Done for get_user_groups_resource)
# 2. Implement the "Selected" item concept.
# 3. Implement the user list resource. (Doing this now)

from .user_tools import get_users # For the new resource

async def get_users_with_group_info_resource(mcp: FastMCP): # mcp might not be needed
    """
    Fetches users and their associated group names.
    """
    try:
        # Fetch all users
        # get_users takes 'page' and 'size'
        users_data = await asyncio.to_thread(get_users, page=0, size=100) # Assuming get_users is sync

        if users_data is None:
            return {"error": "Failed to fetch users or no users found. Tool returned None."}

        processed_users = []
        if not isinstance(users_data, list):
            return {"error": f"Unexpected data format from get_users tool. Expected list, got {type(users_data)}."}

        for user in users_data:
            if not isinstance(user, dict):
                continue # Skip non-dict items

            user_id = user.get("id")
            first_name = user.get("firstName", "")
            last_name = user.get("lastName", "")
            email = user.get("email")
            group_id = user.get("groupId")
            
            group_name = "N/A"
            if group_id:
                try:
                    # Fetch group details for this user's group_id
                    # get_user_group is sync and takes group_id
                    group_data = await asyncio.to_thread(get_user_group, group_id=group_id)
                    if group_data and isinstance(group_data, dict) and "name" in group_data:
                        group_name = group_data["name"]
                    elif group_data is None: # get_user_group returns None if group not found (404)
                        group_name = "Unknown/Not Found"
                except Exception as e:
                    # Log this error, e.g., mcp.logger.warning(...)
                    group_name = f"Error fetching group: {str(e)}"
            
            processed_users.append({
                "id": user_id,
                "name": f"{first_name} {last_name}".strip(),
                "email": email,
                "group_id": group_id,
                "group_name": group_name
            })
            
        return {"users_with_group_info": processed_users}

    except Exception as e:
        # mcp.logger.error(f"Error in get_users_with_group_info_resource: {e}", exc_info=True)
        return {"error": f"An error occurred while fetching users with group info: {str(e)}"}

async def get_current_selection_resource(mcp: FastMCP):
    """
    Returns the currently selected item in the MCP server's state.
    """
    try:
        # The 'mcp' instance is the FastMCP app itself.
        # current_selection was added as a dynamic attribute to it.
        if hasattr(mcp, 'current_selection'):
            return mcp.current_selection
        else:
            # This case should ideally not happen if server.py initializes it.
            return {"error": "Current selection state is not initialized on the server."}
    except Exception as e:
        # mcp.logger.error(f"Error in get_current_selection_resource: {e}", exc_info=True)
        return {"error": f"An error occurred while fetching current selection: {str(e)}"}
