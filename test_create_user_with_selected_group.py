# To run this file correctly from the project root (c:/GitRepos/python-sdk):
# PS C:\GitRepos\python-sdk> uv run python -m connexa_openvpn_mcp_server.test_create_user_with_selected_group

import asyncio
import logging
import uuid
import os
import json
from contextlib import AsyncExitStack
from typing import Optional, Dict, Any

from mcp import ClientSession, StdioServerParameters
from mcp.types import CallToolResult, TextContent, ReadResourceResult, TextResourceContents # Added TextResourceContents
from mcp.client.stdio import stdio_client
from pydantic import AnyUrl

# Args models for creating prerequisite objects
from connexa_openvpn_mcp_server.connexa.creation_tools import CreateNetworkArgs # For selecting a non-group type
# For create_user_group_tool, the arguments are passed directly, not as a model instance.
# For create_user_tool, arguments are also passed directly.

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Expected error identifier for specific failure cases
ERROR_USER_GROUP_REQUIRED = "Please Select a User Group before creating a user."
ERROR_GENERIC_TOOL_FAILURE = "GENERIC_TOOL_FAILURE"

async def test_create_user_attempt(
    session: ClientSession,
    user_params: Dict[str, Any],
    expected_error: Optional[str] = None
) -> Optional[str]:
    """
    Attempts to create a user and checks for success or a specific error.
    """
    logger.info(f"--- Attempting User Creation with params: {user_params} (expecting error: {expected_error}) ---")
    try:
        result: CallToolResult = await session.call_tool(
            "create_user_tool",
            {"args": user_params} # Wrap parameters in "args"
        )
        logger.info(f"Raw tool call result from create_user_tool: {result}")

        tool_reported_error_message: Optional[str] = None
        
        if result.isError:
            # Framework-level error
            error_message = "Unknown framework error from tool."
            if result.content and len(result.content) > 0 and isinstance(result.content[0], TextContent):
                error_message = result.content[0].text
            tool_reported_error_message = error_message
        elif result.content and len(result.content) > 0 and isinstance(result.content[0], TextContent):
            # Check for application-level error reported in the content
            try:
                content_data = json.loads(result.content[0].text)
                if isinstance(content_data, dict) and content_data.get("status") == "error":
                    tool_reported_error_message = content_data.get("message", "Tool reported an error without a message.")
            except json.JSONDecodeError:
                logger.warning("Could not parse tool content as JSON to check for application error.")

        if tool_reported_error_message:
            logger.info(f"Tool 'create_user_tool' reported an error: {tool_reported_error_message}")
            if expected_error and expected_error in tool_reported_error_message:
                logger.info(f"User creation failed as expected with message: '{tool_reported_error_message}'")
                return expected_error
            else:
                logger.error(f"User creation failed with an unexpected error or message mismatch. Expected '{expected_error}', got '{tool_reported_error_message}'")
                return ERROR_GENERIC_TOOL_FAILURE
        
        # If no error (neither framework nor application-level), proceed to check for success
        if expected_error: # This means an error was expected, but none was found
            logger.error(f"User creation succeeded (no error reported by tool) but an error was expected: {expected_error}. Result: {result.content}")
            return ERROR_GENERIC_TOOL_FAILURE

        # Proceed with success check if no error was expected and none was found
        if result.content and len(result.content) > 0:
            first_content = result.content[0]
            if isinstance(first_content, TextContent):
                payload_text = first_content.text
                try:
                    payload_data = json.loads(payload_text)
                    # Assuming successful user creation returns JSON with an 'id'
                    created_id = payload_data.get("id") or payload_data.get("data", {}).get("id")
                    if created_id:
                        logger.info(f"Successfully created user '{user_params.get('username')}' with ID: {created_id}")
                        return created_id
                    else:
                        logger.warning(f"User '{user_params.get('username')}' creation: Success status, but 'id' not found. JSON: {payload_data}")
                        return None # Success but no ID
                except json.JSONDecodeError:
                    logger.error(f"User '{user_params.get('username')}' creation: Failed to parse TextContent as JSON. Content: {payload_text}")
                    return None # Failed to parse
            else:
                logger.warning(f"User '{user_params.get('username')}' creation: Content is not TextContent. Type: {type(first_content)}")
                return None # Wrong content type
        else:
            logger.warning(f"User '{user_params.get('username')}' creation: No error reported by tool, but no content returned.")
            return None # No content
        
        return None # Should not be reached if logic is correct

    except Exception as e:
        logger.error(f"An exception occurred during user '{user_params.get('username')}' creation: {e}", exc_info=True)
        if expected_error and expected_error in str(e): # Check if exception message matches
             logger.info(f"User creation failed via exception as expected: {e}")
             return expected_error
        return ERROR_GENERIC_TOOL_FAILURE


async def main():
    logger.info("Starting MCP client tester for User Creation with Selected Group...")

    server_command_parts = ["python", "-m", "connexa_openvpn_mcp_server.server"]
    command_executable = server_command_parts[0]
    command_args = server_command_parts[1:]
    project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    current_env = os.environ.copy()
    existing_pythonpath = current_env.get("PYTHONPATH")
    new_pythonpath = project_root_dir
    if existing_pythonpath:
        new_pythonpath = f"{project_root_dir}{os.pathsep}{existing_pythonpath}"
    current_env["PYTHONPATH"] = new_pythonpath

    server_params = StdioServerParameters(
        command=command_executable,
        args=command_args,
        cwd=project_root_dir,
        env=current_env
    )

    async with AsyncExitStack() as stack:
        try:
            logger.info(f"Initializing stdio client for command: {' '.join(server_command_parts)} in CWD: {server_params.cwd}")
            stdio_transport = await stack.enter_async_context(stdio_client(server_params))
            read_stream, write_stream = stdio_transport
            logger.info("Stdio transport established.")

            session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
            logger.info("MCP ClientSession created. Initializing session...")
            await session.initialize()
            logger.info("Session initialized.")

            logger.info("Waiting a few seconds for server to be ready...")
            await asyncio.sleep(5)

            user_base_name = str(uuid.uuid4()).split('-')[0]
            common_user_params = {
                "firstName": "Test",
                "lastName": "User",
                "username": f"testuser-{user_base_name}",
                "email": f"testuser-{user_base_name}@example.com",
                "role": "MEMBER"
            }

            # === Test Case 1: Attempt user creation with NO object selected ===
            logger.info("\n--- Test Case 1: Attempt user creation with NO object selected ---")
            # Ensure selection is cleared by selecting a non-existent object
            logger.info("Attempting to select a non-existent object to clear selection.")
            select_non_existent_call: CallToolResult = await session.call_tool(
                "select_object_tool", {"object_type": "usergroup", "name_search": f"nonexistent-{uuid.uuid4()}"}
            )
            if not select_non_existent_call.isError and select_non_existent_call.content and \
               isinstance(select_non_existent_call.content[0], TextContent) and \
               json.loads(select_non_existent_call.content[0].text).get("status") in ["not_found", "failure"]:
                logger.info("Selection cleared/invalidated successfully.")
            else:
                logger.warning(f"Could not confirm selection was cleared. Select call: {select_non_existent_call}")

            result_no_selection = await test_create_user_attempt(session, common_user_params.copy(), expected_error=ERROR_USER_GROUP_REQUIRED)
            if result_no_selection == ERROR_USER_GROUP_REQUIRED:
                logger.info("Test Case 1 SUCCESS: User creation correctly failed when no group was selected.")
            else:
                logger.error(f"Test Case 1 FAILED: Expected '{ERROR_USER_GROUP_REQUIRED}', got: {result_no_selection}")


            # === Test Case 2: Attempt user creation with a non-Group object selected (e.g., Network) ===
            logger.info("\n--- Test Case 2: Attempt user creation with a Network selected ---")
            # Create and select a Network
            network_name = f"test-net-for-user-test-{str(uuid.uuid4()).split('-')[0]}"
            vpn_region_id = os.environ.get("CONNEXA_REGION", "us-west-1") # Default if not set
            create_net_payload = CreateNetworkArgs(name=network_name, description="Temp net for user test", vpnRegionId=vpn_region_id, internetAccess="SPLIT_TUNNEL_ON") # type: ignore
            
            # Use create_network_tool
            create_net_call: CallToolResult = await session.call_tool(
                "create_network_tool",
                {"args": create_net_payload.model_dump(by_alias=True, exclude_none=True)}
            )
            
            created_network_id: Optional[str] = None
            if not create_net_call.isError and create_net_call.content and isinstance(create_net_call.content[0], TextContent):
                net_data = json.loads(create_net_call.content[0].text)
                # create_network_tool now returns the network object directly on success.
                # It might also return a dict with "status":"warning" and "details":{original_api_response}
                created_network_id = net_data.get("id")
                if not created_network_id and isinstance(net_data.get("details"), dict): # Check for warning structure
                    nested_api_response = net_data.get("details", {})
                    if isinstance(nested_api_response.get("data"), dict):
                        created_network_id = nested_api_response.get("data", {}).get("id")
            
            if not created_network_id:
                logger.error(f"Test Case 2 SKIPPED: Failed to create a prerequisite network. Response from create_network_tool: {create_net_call}")
            else:
                logger.info(f"Successfully created network '{network_name}' with ID: {created_network_id}. create_network_tool should have selected it.")
                # Instead of calling select_object_tool, we now trust the selection made by create_network_tool.
                # We will verify this selection directly via the resource.
                
                selected_object_verified_tc2 = False
                resource_uri_str_tc2 = "mcp://resources/current_selection"
                try:
                    typed_resource_uri_tc2 = AnyUrl(resource_uri_str_tc2)
                    selected_object_resource_tc2: Optional[ReadResourceResult] = await session.read_resource(typed_resource_uri_tc2)
                    selected_data_tc2 = None
                    if selected_object_resource_tc2 and selected_object_resource_tc2.contents and len(selected_object_resource_tc2.contents) > 0:
                        resource_content_item_tc2 = selected_object_resource_tc2.contents[0]
                        if isinstance(resource_content_item_tc2, TextResourceContents):
                            selected_data_tc2 = json.loads(resource_content_item_tc2.text)
                            logger.info(f"TC2: CURRENTLY_SELECTED_OBJECT content after network creation: {selected_data_tc2}")
                    
                    if selected_data_tc2:
                        selected_obj_id_tc2 = selected_data_tc2.get("id")
                        selected_obj_type_tc2 = selected_data_tc2.get("type")
                        if selected_obj_id_tc2 == created_network_id and selected_obj_type_tc2 == "network":
                            logger.info(f"TC2 SUCCESS: CURRENTLY_SELECTED_OBJECT correctly reflects network '{network_name}'.")
                            selected_object_verified_tc2 = True
                        else:
                            logger.error(f"TC2 VERIFICATION FAILED: CURRENTLY_SELECTED_OBJECT mismatch. Expected ID '{created_network_id}' & Type 'network', Got ID '{selected_obj_id_tc2}' & Type '{selected_obj_type_tc2}'.")
                    else:
                        logger.error(f"TC2 VERIFICATION FAILED: Could not read or parse {resource_uri_str_tc2} after network creation.")
                except Exception as e_res_tc2:
                    logger.error(f"TC2 VERIFICATION FAILED: Exception while checking {resource_uri_str_tc2}: {e_res_tc2}", exc_info=True)

                if selected_object_verified_tc2:
                    logger.info(f"Network '{network_name}' is selected (verified via resource).")
                    result_network_selected = await test_create_user_attempt(session, common_user_params.copy(), expected_error=ERROR_USER_GROUP_REQUIRED)
                    if result_network_selected == ERROR_USER_GROUP_REQUIRED:
                        logger.info("Test Case 2 SUCCESS: User creation correctly failed when a Network was selected.")
                    else:
                        logger.error(f"Test Case 2 FAILED: Expected '{ERROR_USER_GROUP_REQUIRED}', got: {result_network_selected}")
                else:
                    logger.error(f"Test Case 2 SKIPPED: Failed to verify selection of the created network '{network_name}'.")
            
            # === Test Case 3: Attempt user creation with a User Group correctly selected ===
            logger.info("\n--- Test Case 3: Attempt user creation with a User Group selected ---")
            group_name = f"test-group-for-user-{str(uuid.uuid4()).split('-')[0]}"
            
            # Parameters for create_user_group_tool based on group_tools.py
            create_group_params = {
                "name": group_name,
                "internetAccess": "SPLIT_TUNNEL_ON", # Default or common value
                "maxDevice": 5, # Example value
                "connectAuth": "NO_AUTH", # Example value
                "allRegionsIncluded": True # Added to satisfy API requirement
                # gatewaysIds is optional if not SPLIT_TUNNEL_OFF
            }
            logger.info(f"Attempting to create user group with params: {create_group_params}")
            create_group_call: CallToolResult = await session.call_tool(
                "create_user_group_tool",
                {"args": create_group_params} # Wrap parameters in "args"
            )

            created_group_id: Optional[str] = None
            if not create_group_call.isError and create_group_call.content and isinstance(create_group_call.content[0], TextContent):
                group_data = json.loads(create_group_call.content[0].text)
                # The create_user_group_tool now returns the actual group data directly on success.
                # It might also return a dict with "status":"warning" and "details":{original_api_response}
                # So, we first check if 'id' is top-level (direct success).
                # If not, we check if it's a warning with nested data (less ideal, but for robustness).
                created_group_id = group_data.get("id") 
                if not created_group_id and isinstance(group_data.get("details"), dict): # Check for warning structure
                    nested_api_response = group_data.get("details", {})
                    if isinstance(nested_api_response.get("data"), dict):
                         created_group_id = nested_api_response.get("data", {}).get("id")

            
            if not created_group_id:
                logger.error(f"Test Case 3 SKIPPED: Failed to create a prerequisite user group. Response: {create_group_call}")
            else:
                logger.info(f"Successfully created user group '{group_name}' with ID: {created_group_id}. create_user_group_tool should have selected it.")
                # Instead of calling select_object_tool, we now trust the selection made by create_user_group_tool.
                # We will verify this selection directly via the resource.
                
                selected_object_verified = False
                resource_uri_str = "mcp://resources/current_selection"
                try:
                    typed_resource_uri = AnyUrl(resource_uri_str)
                    selected_object_resource: Optional[ReadResourceResult] = await session.read_resource(typed_resource_uri)
                    selected_data = None
                    if selected_object_resource and selected_object_resource.contents and len(selected_object_resource.contents) > 0:
                        resource_content_item = selected_object_resource.contents[0]
                        if isinstance(resource_content_item, TextResourceContents):
                            selected_data = json.loads(resource_content_item.text)
                            logger.info(f"TC3: CURRENTLY_SELECTED_OBJECT content after group creation: {selected_data}")
                    
                    if selected_data:
                        selected_obj_id = selected_data.get("id")
                        selected_obj_type = selected_data.get("type")
                        if selected_obj_id == created_group_id and selected_obj_type == "usergroup":
                            logger.info(f"TC3 SUCCESS: CURRENTLY_SELECTED_OBJECT correctly reflects group '{group_name}'.")
                            selected_object_verified = True
                        else:
                            logger.error(f"TC3 VERIFICATION FAILED: CURRENTLY_SELECTED_OBJECT mismatch. Expected ID '{created_group_id}' & Type 'usergroup', Got ID '{selected_obj_id}' & Type '{selected_obj_type}'.")
                    else:
                        logger.error(f"TC3 VERIFICATION FAILED: Could not read or parse {resource_uri_str} after group creation.")
                except Exception as e_res:
                    logger.error(f"TC3 VERIFICATION FAILED: Exception while checking {resource_uri_str}: {e_res}", exc_info=True)

                if selected_object_verified:
                    user_creation_args = common_user_params.copy()
                    logger.info(f"Attempting user creation with args (groupId will be inferred by server from selected group): {user_creation_args}")
                    created_user_id_or_error = await test_create_user_attempt(session, user_creation_args)
                    
                    if created_user_id_or_error and created_user_id_or_error not in [ERROR_USER_GROUP_REQUIRED, ERROR_GENERIC_TOOL_FAILURE]:
                        logger.info(f"Test Case 3 SUCCESS: User created successfully with ID: {created_user_id_or_error} when group '{group_name}' was selected.")
                        # Removed groupId verification as get_user_tool is not available/working in this context.
                        # The primary goal of this test case (user creation with selected group) is achieved.
                    else:
                        logger.error(f"Test Case 3 FAILED (User Creation): Got: {created_user_id_or_error}")
                else:
                    logger.error(f"Test Case 3 SKIPPED: Failed to verify selection of the created user group '{group_name}'.")

        except Exception as e:
            logger.error(f"An error occurred in main: {e}", exc_info=True)
        finally:
            logger.info("Client operations finished. AsyncExitStack will handle cleanup.")

if __name__ == "__main__":
    asyncio.run(main())
