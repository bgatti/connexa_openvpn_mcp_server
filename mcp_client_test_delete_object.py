# To run this file correctly from the project root (c:/GitRepos/python-sdk):
# PS C:\GitRepos\python-sdk> uv run python -m connexa_openvpn_mcp_server.mcp_client_test_delete_object

import asyncio
import logging
import uuid
import os
import json
from contextlib import AsyncExitStack
from typing import Optional
from dotenv import load_dotenv

from mcp import ClientSession, StdioServerParameters
from mcp.types import CallToolResult, TextContent, EmbeddedResource
from mcp.client.stdio import stdio_client

# Import necessary argument types for creation tools (no longer needed for this version)
# from connexa_openvpn_mcp_server.connexa.creation_tools import CreateNetworkArgs

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def select_object(session: ClientSession, object_type: str, name_search: Optional[str]) -> bool:
    """
    Selects an object using the select_object_tool.
    Returns True if selection was successful, False otherwise.
    """
    logger.info(f"\n--- Selecting {object_type} '{name_search}' ---")
    try:
        # The select_object_tool handles parent object context internally
        # if the parent is already selected.
        result: CallToolResult = await session.call_tool(
            "select_object_tool",
            {"object_type": object_type, "name_search": name_search}
        )
        logger.info(f"Raw tool call result from select_object_tool: {result}")

        if not result.isError and result.content and isinstance(result.content[0], TextContent):
            try:
                response_data = json.loads(result.content[0].text)
                logger.info(f"Parsed select object response: {json.dumps(response_data, indent=2)}")
                if isinstance(response_data, dict) and response_data.get("status") == "success":
                    logger.info(f"Successfully selected {object_type}: {response_data.get('object_name')} (ID: {response_data.get('object_id')})")
                    return True
                elif isinstance(response_data, dict) and response_data.get("status") in ["error", "not_found"]:
                     logger.error(f"Select object tool reported status '{response_data.get('status')}': {response_data.get('message', 'No message')}.")
                     return False
                else:
                    logger.error(f"Select object tool returned data in an unexpected format: {response_data}")
                    return False
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response from select_object_tool: {result.content[0].text}")
                return False
        elif result.isError:
            error_text = "Unknown tool error"
            if result.content and len(result.content) > 0 and isinstance(result.content[0], TextContent):
                error_text = result.content[0].text
            logger.error(f"Select object tool returned an error: {error_text}.")
            return False
        else:
            logger.warning("Select object tool returned no error and no content.")
            return False
    except Exception as e:
        logger.error(f"An exception occurred during object selection: {e}", exc_info=True)
        return False

async def delete_selected_object_test(session: ClientSession) -> bool:
    """
    Calls the delete_selected_object tool.
    Returns True if deletion was successful, False otherwise.
    """
    logger.info(f"\n--- Deleting Selected Object ---")
    try:
        result: CallToolResult = await session.call_tool(
            "delete_selected_object",
            {} # delete_selected_object takes no arguments
        )
        logger.info(f"Raw tool call result from delete_selected_object: {result}")

        # Check if the result content is a TextContent object containing JSON
        response_data = None
        if result.content and isinstance(result.content[0], TextContent):
            try:
                response_data = json.loads(result.content[0].text)
                logger.info(f"Parsed delete selected object response: {json.dumps(response_data, indent=2)}")
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response from delete_selected_object: {result.content[0].text}")
                # The test should fail if the response is not valid JSON when expected
                return False # Indicate failure to parse JSON

        # Now check the status within the parsed response data
        if isinstance(response_data, dict) and response_data.get("status") == "success":
            logger.info(f"Successfully deleted selected object: {response_data.get('message')}")
            return True
        elif isinstance(response_data, dict) and response_data.get("status") == "error":
             logger.error(f"Delete selected object tool reported status 'error': {response_data.get('message', 'No message')}.")
             # Return False for an explicit error status from the tool
             return False
        elif result.isError:
            # Handle cases where isError is True (less common for tools returning structured output)
            error_text = "Unknown tool error"
            if result.content and len(result.content) > 0 and isinstance(result.content[0], TextContent):
                error_text = result.content[0].text
            logger.error(f"Delete selected object tool returned an MCP error: {error_text}.")
            return False
        else:
            logger.warning("Delete selected object tool returned no error, no content, or unhandled format.")
            # This case might indicate an issue with the tool's return structure
            return False
    except Exception as e:
        logger.error(f"An exception occurred during object deletion: {e}", exc_info=True)
        return False


async def main():
    # Load environment variables from .env file located in the same directory as this script
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        logger.info(f"Loaded environment variables from {dotenv_path}")
    else:
        logger.warning(f".env file not found at {dotenv_path}. Relying on system environment variables.")

    logger.info("Starting MCP client tester for Delete Object tool...")

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

            # --- Test Delete Connector ---
            logger.info("\n=== Test Delete Connector ===")

            # Hardcoded values for testing the delete tool fix with the original connector
            object_type_to_delete = "connector"
            object_name_to_delete = "test-conn-main-30a31a0f"
            parent_network_name = "test-network-fe5fa038" # Needed for connector selection

            selection_successful = False
            if object_type_to_delete.lower() == "connector":
                if not parent_network_name:
                    logger.error("Parent network name is required for connector deletion.")
                else:
                    # Select the parent network first
                    logger.info(f"Selecting parent network '{parent_network_name}' for connector...")
                    parent_selection_successful = await select_object(session, "network", parent_network_name)

                    if parent_selection_successful:
                        logger.info(f"Parent network '{parent_network_name}' selected. Proceeding to select connector.")
                        # Select the connector within the context of the selected network
                        selection_successful = await select_object(session, object_type_to_delete, object_name_to_delete)
                    else:
                        logger.error(f"Failed to select parent network '{parent_network_name}'. Cannot select connector.")
            else:
                # For other object types, just select the object directly (This block is not used for this test)
                selection_successful = await select_object(session, object_type_to_delete, object_name_to_delete)


            if selection_successful:
                logger.info(f"Object '{object_name_to_delete}' ({object_type_to_delete}) selected successfully. Proceeding to call delete_selected_object.")

                # Call the delete_selected_object tool
                # We expect this call NOT to fail with the specific resource reading error
                # The actual API deletion might fail (e.g., 404 Not Found), but the tool
                # should handle reading the selected object data correctly and report the API result.
                delete_result: CallToolResult = await session.call_tool(
                    "delete_selected_object",
                    {} # delete_selected_object takes no arguments
                )
                logger.info(f"Raw tool call result from delete_selected_object: {delete_result}")

                # Check the status within the tool's response content
                response_data = None
                if delete_result.content and isinstance(delete_result.content[0], TextContent):
                    try:
                        response_data = json.loads(delete_result.content[0].text)
                    except json.JSONDecodeError:
                        logger.error("Test Failed: Failed to parse JSON response from delete_selected_object.")
                        assert False, "Failed to parse JSON response from delete_selected_object."

                # Assert that the tool call did not return the specific resource reading error
                # and that it returned a valid status (success or API error)
                resource_reading_error_message = "Unexpected format for selected object data from resource."
                if isinstance(response_data, dict) and response_data.get("status") == "error" and response_data.get("message") == resource_reading_error_message:
                    logger.error(f"Test Failed: delete_selected_object returned the specific resource reading error.")
                    assert False, f"delete_selected_object returned the specific resource reading error: {resource_reading_error_message}"
                elif isinstance(response_data, dict) and response_data.get("status") in ["success", "error"]:
                     logger.info(f"Test Passed: delete_selected_object reported a valid status ('{response_data.get('status')}'). Message: {response_data.get('message')}")
                     assert True # Explicitly pass the test, as the resource reading part worked and a valid API result was returned
                else:
                    logger.error(f"Test Failed: delete_selected_object returned unexpected data format or no parsable content: {delete_result}")
                    assert False, f"delete_selected_object returned unexpected data format or no parsable content: {delete_result}"

                logger.info(f"Test for deleting connector '{object_name_to_delete}' completed.")

            else:
                logger.error(f"Failed to select object '{object_name_to_delete}' ({object_type_to_delete}) for deletion.")
                assert False, f"Failed to select object '{object_name_to_delete}' ({object_type_to_delete}) for deletion test."


        except Exception as e:
            logger.error(f"An error occurred in main: {e}", exc_info=True)
        finally:
            logger.info("Client operations finished. AsyncExitStack will handle cleanup.")

if __name__ == "__main__":
    asyncio.run(main())
