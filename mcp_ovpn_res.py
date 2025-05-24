import sys # Added for sys.stderr
import asyncio # Needed for asyncio.to_thread
from mcp.server.fastmcp import FastMCP
from .group_tools import get_user_groups, get_user_group # Import both functions

async def get_user_groups_resource(): # Removed mcp: FastMCP parameter
    """
    Fetches user groups and returns pertinent information for each group
    by calling the 'get_user_groups' tool internally.
    """
    print("get_user_groups_resource: Entered function", file=sys.stderr)
    try:
        print("get_user_groups_resource: Calling await get_user_groups", file=sys.stderr)
        # Call the now asynchronous get_user_groups function directly
        tool_result = await get_user_groups(page=0, size=100)
        print(f"get_user_groups_resource: get_user_groups returned: {type(tool_result)}", file=sys.stderr)

        # The original code checked for `tool_result is None`.
        # The get_user_groups function in group_tools.py returns response.json() or raises McpError.
        # It doesn't seem to return None for "no groups found" but might if an API call leads to that.
        # A 404 in get_user_group (singular) returns None, but get_user_groups (plural) doesn't show this.
        # An empty list [] is more likely for "no groups".
        # If an error occurs, McpError is raised, which will be caught by the except block.
        # So, `tool_result is None` might be an unlikely path unless the API itself returns null.
        # Directly return the result from the get_user_groups call
        # The get_user_groups function itself returns a dict (JSON response) or raises McpError
        print("get_user_groups_resource: Returning tool_result", file=sys.stderr)
        return tool_result

    except Exception as e:
        print(f"get_user_groups_resource: Exception: {e}", file=sys.stderr)
        # Log the exception, e.g., using mcp.logger if available and configured
        # For now, just returning the error string
        # Consider using mcp.logger.error(f"Error in get_user_groups_resource: {e}", exc_info=True)
        return {"error": f"An error occurred while fetching user groups: {str(e)}"}

# Next steps:
# 1. Register this resource function in server.py using `app.resource()`. (Done for get_user_groups_resource)
# 2. Implement the "Selected" item concept.
# 3. Implement the user list resource. (Doing this now)

import httpx # For making API calls
from mcp.shared.exceptions import McpError # For error handling
from mcp.types import ErrorData, INTERNAL_ERROR # For error handling
from .user_tools import get_users, get_async_client # For the new resource and API client

# Removed: from .region_tools import get_vpn_regions

async def get_users_with_group_info_resource(): # Removed mcp: FastMCP parameter
    """
    Fetches users and their associated group names.
    """
    print("get_users_with_group_info_resource: Entered function", file=sys.stderr)
    try:
        print("get_users_with_group_info_resource: Calling asyncio.to_thread(get_users)", file=sys.stderr)
        # Fetch all users
        # get_users is still synchronous, so it needs to_thread
        # OR user_tools.py also needs to be refactored for get_users to be async
        # For now, assuming get_users in user_tools.py is still sync
        users_data = await asyncio.to_thread(get_users, page=0, size=100) 
        print(f"get_users_with_group_info_resource: get_users returned: {type(users_data)}", file=sys.stderr)

        if users_data is None:
            print("get_users_with_group_info_resource: users_data is None", file=sys.stderr)
            return {"error": "Failed to fetch users or no users found. Tool returned None."}

        processed_users = []
        # users_data from get_users is also a paginated response (dict with 'content')
        if isinstance(users_data, dict) and "content" in users_data and isinstance(users_data["content"], list):
            for user in users_data["content"]: # Iterate over the 'content' list
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
                        # get_user_group is now async
                        print(f"get_users_with_group_info_resource: Calling await get_user_group for group_id {group_id}", file=sys.stderr)
                        group_data = await get_user_group(group_id=group_id)
                        print(f"get_users_with_group_info_resource: get_user_group returned: {type(group_data)} for group_id {group_id}", file=sys.stderr)
                        if group_data and isinstance(group_data, dict) and "name" in group_data:
                            group_name = group_data["name"]
                        elif group_data is None: # get_user_group returns None if group not found (404)
                            group_name = "Unknown/Not Found"
                    except Exception as e:
                        print(f"get_users_with_group_info_resource: Exception in get_user_group call: {e}", file=sys.stderr)
                        # Log this error, e.g., mcp.logger.warning(...)
                        group_name = f"Error fetching group: {str(e)}"
                
                processed_users.append({
                    "id": user_id,
                    "name": f"{first_name} {last_name}".strip(),
                    "email": email,
                    "group_id": group_id,
                    "group_name": group_name
                })
            
        print("get_users_with_group_info_resource: Returning processed_users", file=sys.stderr)
        return {"users_with_group_info": processed_users}

    except Exception as e:
        print(f"get_users_with_group_info_resource: Exception: {e}", file=sys.stderr)
        # mcp.logger.error(f"Error in get_users_with_group_info_resource: {e}", exc_info=True)
        return {"error": f"An error occurred while fetching users with group info: {str(e)}"}

async def get_current_selection_resource(): # Removed mcp: FastMCP parameter, Uncommented
    """
    Returns the currently selected item in the MCP server's state.
    """
    print("get_current_selection_resource: Entered function", file=sys.stderr)
    try:
        # The 'mcp' instance is the FastMCP app itself.
        # current_selection was added as a dynamic attribute to it.
        # This will currently fail as 'mcp' is not defined in this scope.
        # This resource needs to be re-thought if app state access is needed without mcp param.
        # For now, to allow server startup, let's return a placeholder or error.
        # if hasattr(mcp, 'current_selection'): 
        #     return mcp.current_selection
        # else:
        print("get_current_selection_resource: Returning placeholder/error", file=sys.stderr)
        return {"error": "Current selection state is not directly accessible in this version of the resource."}
    except Exception as e:
        print(f"get_current_selection_resource: Exception: {e}", file=sys.stderr)
        # mcp.logger.error(f"Error in get_current_selection_resource: {e}", exc_info=True)
        return {"error": f"An error occurred while fetching current selection: {str(e)}"}

async def get_regions_resource():
    """
    Fetches VPN regions directly using the API client.
    """
    print("get_regions_resource: Entered function", file=sys.stderr)
    client: httpx.AsyncClient | None = None
    try:
        client = await get_async_client()
        url = "/api/v1/regions" # Relative URL as base_url is in client
        print(f"get_regions_resource: Requesting URL: {client.base_url}{url}", file=sys.stderr)
        
        response = await client.get(url)
        print(f"get_regions_resource: Response status code: {response.status_code}", file=sys.stderr)
        response.raise_for_status()
        
        regions_data = response.json()
        print(f"get_regions_resource: Successfully fetched regions data: {type(regions_data)}", file=sys.stderr)
        
        # Swagger indicates this returns an array of VpnRegionResponse
        # We'll return it directly as the value for the "regions" key
        if isinstance(regions_data, list):
            return {"regions": regions_data}
        else:
            # This case should ideally not happen if API conforms to swagger
            print(f"get_regions_resource: API returned non-list type: {type(regions_data)}", file=sys.stderr)
            return {"error": "API returned unexpected data format for regions.", "details": regions_data}

    except McpError: # Re-raise McpError from get_async_client
        raise
    except httpx.HTTPStatusError as e:
        print(f"get_regions_resource: HTTPStatusError: {e.response.status_code} - {e.response.text}", file=sys.stderr)
        error_message = f"API request failed with status {e.response.status_code}"
        try:
            error_details = e.response.json()
            error_message += f": {error_details.get('errorMessage', e.response.text)}"
        except Exception:
            error_message += f": {e.response.text}"
        # Return an error dict, as this is a resource function
        return {"error": error_message, "status_code": e.response.status_code}
    except httpx.RequestError as e:
        print(f"get_regions_resource: RequestError: {e}", file=sys.stderr)
        return {"error": f"API request failed: {str(e)}"}
    except Exception as e:
        print(f"get_regions_resource: Unexpected exception: {e}", file=sys.stderr)
        # For unexpected errors, also return an error dict
        return {"error": f"An unexpected error occurred while fetching regions: {str(e)}"}
    finally:
        if client:
            await client.aclose()
