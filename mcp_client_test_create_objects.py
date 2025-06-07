import asyncio
import logging
import uuid
import os # Added for path operations
import json # Added for parsing JSON in TextContent
from contextlib import AsyncExitStack # Added for session management
from typing import Any, Dict

# Corrected imports based on mcp_client_tester.py
from mcp import ClientSession, StdioServerParameters
from mcp.types import CallToolResult, TextContent # Added TextContent
from mcp.client.stdio import stdio_client # Corrected import
from pydantic import AnyUrl # Added for type casting URI

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Use a logger instance
# init_fastmcp_logging = lambda: None # Placeholder removed, using standard logging

# Import creation tool argument models and user creation args
# These imports are assumed to be correct for the project structure,
# Pylance errors for these might be path configuration issues.
from connexa_openvpn_mcp_server.connexa.creation_tools import (
    CreateUserGroupArgs,
    CreateUserArgs, # Moved import here
    # Add other *Args models as we implement tests
)
# from connexa_openvpn_mcp_server.user_tools import CreateUserArgs # Removed from here

# SERVER_NAME is not used when calling tools on an established session
# SERVER_NAME = "OpenVPN-Connexa-Server"

async def test_create_user_group(session: ClientSession, region_id_to_use: str) -> str | None:
    """Tests creating a user group."""
    logger.info("\n--- Testing User Group Creation ---")
    group_name = f"test-group-{str(uuid.uuid4()).split('-')[0]}"
    try:
        args = CreateUserGroupArgs(name=group_name, vpn_region_ids=[region_id_to_use])
        logger.info(f"Attempting to create user group: {group_name} with region {region_id_to_use}")
        
        result: CallToolResult = await session.call_tool(
            "create_user_group_tool", 
            {"args": args.model_dump(exclude_none=True)},
        )
        logger.info(f"Raw tool call result from create_user_group_tool: {result}")

        if not result.isError:
            if result.content and len(result.content) > 0:
                first_content = result.content[0]
                if isinstance(first_content, TextContent):
                    payload_text = first_content.text
                    try:
                        payload_data = json.loads(payload_text)
                        # Check for API-level error even if tool call itself didn't error
                        if isinstance(payload_data, dict) and payload_data.get("status") == "error":
                            logger.error(f"API returned an error for user group '{group_name}': {payload_data.get('message', 'No message')}")
                            logger.error(f"API error details: {payload_data.get('details', 'No details')}")
                            return None
                        
                        if isinstance(payload_data, dict) and "id" in payload_data:
                            created_id = payload_data["id"]
                            logger.info(f"Successfully created user group '{group_name}' with ID: {created_id}")
                            return created_id
                        else:
                            logger.warning(f"User group '{group_name}' creation: TextContent received, but 'id' not in parsed JSON or not a dict, or API error not caught.")
                            logger.warning(f"Parsed JSON: {payload_data}")
                            return None
                    except json.JSONDecodeError:
                        logger.error(f"User group '{group_name}' creation: Failed to parse TextContent as JSON. Content: {payload_text}")
                        return None
                else:
                    logger.warning(f"User group '{group_name}' creation: Content is not TextContent. Content type: {type(first_content)}, Content: {first_content}")
                    return None
            else:
                logger.warning(f"User group '{group_name}' creation: No error reported by tool, but no content returned.")
                return None
        else:  # result.isError is True
            error_message = "Unknown error from tool."
            if result.content and len(result.content) > 0 and isinstance(result.content[0], TextContent):
                error_message = result.content[0].text
            logger.error(f"Tool 'create_user_group_tool' for '{group_name}' reported an error.") # Corrected tool name in log
            logger.error(f"Tool error message: {error_message}")
            logger.error(f"Full error content from tool: {result.content}")
            return None
    except Exception as e: # Catches JSON-RPC errors, network issues, etc.
        logger.error(f"An exception occurred during user group '{group_name}' creation: {e}", exc_info=True)
        return None

async def test_create_user(session: ClientSession, group_id: str | None) -> str | None:
    """Tests creating a user."""
    logger.info("\n--- Testing User Creation ---")
    if not group_id:
        logger.error("User creation skipped: No valid group_id provided.")
        return None

    user_name_prefix = f"test-user-{str(uuid.uuid4()).split('-')[0]}"
    args = None # Initialize args to None
    try:
        args = CreateUserArgs(
            firstName="Test",
            lastName="User",
            username=f"{user_name_prefix}",
            email=f"{user_name_prefix}@example.com",
            groupId=group_id,
            role="MEMBER"
        )
        logger.info(f"Attempting to create user: {args.username} in group {group_id}")
        
        # The create_user tool is defined in user_tools.py and registered with its function name
        result: CallToolResult = await session.call_tool(
            "create_user", 
            {"args": args.model_dump(exclude_none=True)},
        )
        logger.info(f"Raw tool call result from create_user: {result}")

        if not result.isError:
            if result.content and len(result.content) > 0:
                first_content = result.content[0]
                if isinstance(first_content, TextContent):
                    payload_text = first_content.text
                    try:
                        payload_data = json.loads(payload_text)
                        # User creation API returns the full user object, which has an 'id' field.
                        if isinstance(payload_data, dict) and "id" in payload_data:
                            created_id = payload_data["id"]
                            logger.info(f"Successfully created user '{args.username}' with ID: {created_id}")
                            return created_id
                        else:
                            logger.warning(f"User '{args.username}' creation: TextContent received, but 'id' not in parsed JSON or not a dict.")
                            logger.warning(f"Parsed JSON: {payload_data}")
                            return None
                    except json.JSONDecodeError:
                        logger.error(f"User '{args.username}' creation: Failed to parse TextContent as JSON. Content: {payload_text}")
                        return None
                else:
                    logger.warning(f"User '{args.username}' creation: Content is not TextContent. Content type: {type(first_content)}, Content: {first_content}")
                    return None
            else:
                logger.warning(f"User '{args.username}' creation: No error reported by tool, but no content returned.")
                return None
        else:  # result.isError is True
            error_message = "Unknown error from tool."
            if result.content and len(result.content) > 0 and isinstance(result.content[0], TextContent):
                error_message = result.content[0].text
            logger.error(f"Tool 'create_user' for '{args.username}' reported an error.")
            logger.error(f"Tool error message: {error_message}")
            logger.error(f"Full error content from tool: {result.content}")
            return None
    except Exception as e:
        username_for_log = user_name_prefix
        if args and hasattr(args, 'username'): # args is now guaranteed to be defined
            username_for_log = args.username
        logger.error(f"An exception occurred during user '{username_for_log}' creation: {e}", exc_info=True)
        return None

async def main():
    """Main function to run tests."""
    logger.info("Starting MCP client tester for creation tools...")

    # Command to start the MCP server.
    # Using python -m with PYTHONPATH set, and server logs to stdout.
    server_command_parts = ["python", "-m", "connexa_openvpn_mcp_server.server"]
    command_executable = server_command_parts[0]
    command_args = server_command_parts[1:]

    # Determine server CWD and PYTHONPATH base
    # This script is in 'c:/GitRepos/python-sdk/connexa_openvpn_mcp_server/'
    # The project root (python-sdk) is one level up.
    project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    logger.info(f"Calculated project root for CWD and PYTHONPATH: {project_root_dir}")

    # Set environment for the subprocess, ensuring local project path is preferred.
    # Copy current environment and prepend project_root_dir to PYTHONPATH
    current_env = os.environ.copy()
    existing_pythonpath = current_env.get("PYTHONPATH")
    new_pythonpath = project_root_dir
    if existing_pythonpath:
        new_pythonpath = f"{project_root_dir}{os.pathsep}{existing_pythonpath}"
    current_env["PYTHONPATH"] = new_pythonpath
    logger.info(f"Setting PYTHONPATH for server subprocess to: {new_pythonpath}")

    server_params = StdioServerParameters(
        command=command_executable,
        args=command_args,
        cwd=project_root_dir, # Server's working directory is the project root
        env=current_env # Pass modified environment
    )

    async with AsyncExitStack() as stack:
        try:
            logger.info(f"Initializing stdio client for command: {' '.join(server_command_parts)} in CWD: {server_params.cwd}")
            # logger.info(f"Server CWD will be: {server_params.cwd}") # Redundant with above

            stdio_transport = await stack.enter_async_context(
                stdio_client(server_params)
            )
            read_stream, write_stream = stdio_transport
            logger.info("Stdio transport established.")

            session = await stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            logger.info("MCP ClientSession created. Initializing session...")
            await session.initialize()
            logger.info("Session initialized.")

            # Optional: Wait for server to fully initialize tools
            logger.info("Waiting a few seconds for server to be ready...")
            await asyncio.sleep(5)

            fetched_regions_list = []
            try:
                logger.info("Attempting to fetch VPN regions...")
                regions_result_wrapper = await session.read_resource(AnyUrl("mcp://resources/regions")) 
                
                if regions_result_wrapper and regions_result_wrapper.contents:
                    if len(regions_result_wrapper.contents) > 0:
                        first_content_item = regions_result_wrapper.contents[0]
                        if isinstance(first_content_item, TextContent):
                            regions_data_str = first_content_item.text
                            try:
                                parsed_regions_data = json.loads(regions_data_str)
                                if isinstance(parsed_regions_data, list):
                                    fetched_regions_list = parsed_regions_data
                                    logger.info(f"Available VPN regions: {json.dumps(fetched_regions_list, indent=2)}")
                                else:
                                    logger.error(f"Parsed regions data is not a list: {type(parsed_regions_data)}")
                            except json.JSONDecodeError:
                                logger.error(f"Failed to parse regions JSON from text: {regions_data_str}") 
                        else:
                            logger.error(f"Unexpected type for first content item when fetching regions: {type(first_content_item)}")
                    else:
                        logger.error("Fetched VPN regions, but regions_result_wrapper.contents is empty.")
                elif regions_result_wrapper:
                     logger.error(f"Fetched VPN regions, but result has no 'contents' or it's empty. Result: {regions_result_wrapper}")
                else:
                    logger.error("Failed to fetch VPN regions: read_resource returned None.")
            except Exception as e_regions:
                logger.error(f"Error fetching VPN regions: {e_regions}", exc_info=True)

            user_group_id = None
            if fetched_regions_list:
                first_region = fetched_regions_list[0]
                if isinstance(first_region, dict) and "id" in first_region:
                    region_id_to_use = first_region["id"]
                    logger.info(f"Using first fetched region ID for user group creation: {region_id_to_use}")
                    user_group_id = await test_create_user_group(session, region_id_to_use)
                else:
                    logger.error("Could not extract ID from the first fetched region or region is not a dict. Skipping user group creation.")
            else:
                logger.error("No VPN regions fetched or parsed successfully. Cannot proceed with user group creation without a valid region ID.")

            if user_group_id:
                logger.info(f"User Group creation test successful. ID: {user_group_id}")
            else:
                logger.error("User Group creation test failed or ID not retrieved.")

            # Test User creation
            user_id = await test_create_user(session, user_group_id)
            if user_id:
                logger.info(f"User creation test successful. ID: {user_id}")
            else:
                logger.error("User creation test failed or ID not retrieved.")
            
            # Future tests will be added here

        except Exception as e:
            logger.error(f"An error occurred in main: {e}", exc_info=True)
        finally:
            logger.info("Client operations finished. AsyncExitStack will handle cleanup.")

if __name__ == "__main__":
    asyncio.run(main())
