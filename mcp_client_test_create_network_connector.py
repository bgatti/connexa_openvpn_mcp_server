# To run this file correctly from the project root (c:/GitRepos/python-sdk):
# PS C:\GitRepos\python-sdk> uv run python -m connexa_openvpn_mcp_server.mcp_client_test_create_network_connector

import asyncio
import logging
import uuid
import os
import json
from contextlib import AsyncExitStack
from typing import Optional

from mcp import ClientSession, StdioServerParameters
from mcp.types import CallToolResult, TextContent, EmbeddedResource # UriContent removed, EmbeddedResource added
from mcp.client.stdio import stdio_client

# Attempt to import actual CreateNetworkConnectorArgs, fallback to placeholder
try:
    from connexa_openvpn_mcp_server.connexa.connector_tools import CreateNetworkConnectorArgs
except ImportError:
    logging.warning("Actual CreateNetworkConnectorArgs not found or connexa.connector_tools doesn't exist. Using placeholder.")
    from pydantic import BaseModel, Field, ConfigDict

    class CreateNetworkConnectorArgs(BaseModel):  # Placeholder definition
        name: str
        vpn_region_id: str = Field(default="us-default-region", alias="vpnRegionId")
        # This placeholder assumes 'name' and 'vpnRegionId' are key.
        # 'networkId' is intentionally omitted based on the hypothesis that
        # the tool uses an implicitly selected object.
        # If other fields are mandatory for the actual tool, this placeholder will need adjustment.
        model_config = ConfigDict(populate_by_name=True, extra='ignore')


# Imports for creating prerequisite objects (Network, User Group)
from connexa_openvpn_mcp_server.connexa.creation_tools import CreateNetworkArgs, CreateUserGroupArgs

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Expected error identifier for specific failure cases
ERROR_NETWORK_REQUIRED = "ERROR_NETWORK_REQUIRED"

async def test_create_network_connector(session: ClientSession) -> Optional[str]:
    """
    Tests creating a network connector.
    Assumes a relevant object (network or non-network) has been selected via 'select_object' tool,
    and 'create_network_connector_tool' will use this implicitly selected object.
    """
    logger.info("\n--- Testing Network Connector Creation (relies on prior selection) ---")
    connector_name = f"test-conn-{str(uuid.uuid4()).split('-')[0]}"
    try:
        args = CreateNetworkConnectorArgs(
            name=connector_name
            # vpn_region_id will use default from placeholder if not overridden,
            # or actual model's default/requirements.
        )
        logger.info(f"Attempting to create network connector: {args.name} (using implicitly selected object)")

        result: CallToolResult = await session.call_tool(
            "create_network_connector_tool",
            {"args": args.model_dump(by_alias=True, exclude_none=True)}
        )
        logger.info(f"Raw tool call result from create_network_connector_tool: {result}")

        if not result.isError:
            if result.content and len(result.content) > 0:
                first_content = result.content[0]
                if isinstance(first_content, TextContent):
                    payload_text = first_content.text
                    try:
                        payload_data = json.loads(payload_text)
                        # Check for specific error message first, as it might be a valid JSON response
                        if "select or create a network before creating a connector" in payload_text:
                            logger.info(f"Connector creation for '{args.name}' failed as expected with message: {payload_text}")
                            return ERROR_NETWORK_REQUIRED

                        if isinstance(payload_data, dict) and payload_data.get("status") in [200, 201, "ok", "success"]: # Common success indicators
                            created_id = payload_data.get("data", {}).get("id") or payload_data.get("id")
                            if created_id:
                                logger.info(f"Successfully created network connector '{args.name}' with ID: {created_id}")
                                return created_id
                            else:
                                logger.warning(f"Connector '{args.name}' creation: Success status, but 'id' not found. JSON: {payload_data}")
                                return None
                        elif isinstance(payload_data, dict) and payload_data.get("status") == "error":
                             logger.error(f"API returned an error for connector '{args.name}': {payload_data.get('message', 'No message')}")
                             return None
                        else: # Unexpected response
                            logger.error(f"Connector '{args.name}' creation: API did not return clear success/error. Response: {payload_data}")
                            return None
                    except json.JSONDecodeError:
                        # If it's not JSON, but contains the message, it's still the specific error
                        if "select or create a network before creating a connector" in payload_text:
                            logger.info(f"Connector creation for '{args.name}' failed as expected with non-JSON message: {payload_text}")
                            return ERROR_NETWORK_REQUIRED
                        logger.error(f"Connector '{args.name}' creation: Failed to parse TextContent as JSON. Content: {payload_text}")
                        return None
                else: # Not TextContent
                    logger.warning(f"Connector '{args.name}' creation: Content is not TextContent. Type: {type(first_content)}")
                    return None
            else: # No content
                logger.warning(f"Connector '{args.name}' creation: No error reported by tool, but no content returned.")
                return None
        else:  # result.isError is True
            error_message = "Unknown error from tool."
            if result.content and len(result.content) > 0 and isinstance(result.content[0], TextContent):
                error_message = result.content[0].text
            
            if "select or create a network before creating a connector" in error_message:
                logger.info(f"Connector creation for '{args.name}' failed as expected (tool error): {error_message}")
                return ERROR_NETWORK_REQUIRED
            
            logger.error(f"Tool 'create_network_connector_tool' for '{args.name}' reported an error: {error_message}")
            logger.error(f"Full error content from tool: {result.content}")
            return None

    except Exception as e:
        logger.error(f"An exception occurred during network connector '{connector_name}' creation: {e}", exc_info=True)
        return None

async def main():
    logger.info("Starting MCP client tester for dependent object (Network Connector) creation...")

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
            await asyncio.sleep(5) # Allow server to initialize tools

            # === Part 1: Testing connector creation with a selected Network named 'test-network-71c7398d' ===
            logger.info("\n--- Part 1: Testing connector creation with a selected Network named 'test-network-71c7398d' ---")
            network_to_select_name = "test-network-71c7398d"  # As per user request
            selected_network_uri_for_log = "N/A" # For logging in success/failure messages

            # Attempt to select the network "test-network-71c7398d"
            logger.info(f"Attempting to select network: {network_to_select_name}")
            select_nw_result: CallToolResult = await session.call_tool(
                "select_object_tool", {"object_type": "network", "name_search": network_to_select_name}
            )

            nw_selected_successfully = False
            if not select_nw_result.isError and select_nw_result.content and isinstance(select_nw_result.content[0], EmbeddedResource):
                selected_resource_content = select_nw_result.content[0].resource
                if hasattr(selected_resource_content, 'uri'):
                    uri_str = str(selected_resource_content.uri)
                    # Since we don't create the network here, we can't check its ID against the URI.
                    # We assume if an EmbeddedResource is returned for "test", it's a successful selection.
                    logger.info(f"Successfully selected network '{network_to_select_name}' (URI: {uri_str}).")
                    selected_network_uri_for_log = uri_str
                    nw_selected_successfully = True
                else:
                    logger.warning(f"Selected object for network '{network_to_select_name}' is EmbeddedResource but missing 'uri' in its 'resource' attribute of the EmbeddedResource.")
            elif not select_nw_result.isError and select_nw_result.content and isinstance(select_nw_result.content[0], TextContent):
                # This case handles scenarios where the tool might return a text message for "not found" or other non-error statuses.
                logger.warning(f"Network selection for '{network_to_select_name}' returned TextContent instead of EmbeddedResource. Content: {select_nw_result.content[0].text}. Assuming selection failed.")
            elif not select_nw_result.isError and select_nw_result.content:
                 # Log if it's not an EmbeddedResource or TextContent
                logger.warning(f"Network selection for '{network_to_select_name}' did not return EmbeddedResource or TextContent. Got type: {type(select_nw_result.content[0])}, Content: {select_nw_result.content[0]}. Assuming selection failed.")
            # No specific handling for `select_nw_result.isError` here, as it's caught by `not nw_selected_successfully` combined with logging below

            if not nw_selected_successfully:
                # Consolidate error logging for selection failure
                failure_reason = "did not succeed (e.g., not found, unexpected response, or tool error)."
                if select_nw_result.isError:
                    error_text = "Unknown tool error"
                    if select_nw_result.content and len(select_nw_result.content) > 0 and isinstance(select_nw_result.content[0], TextContent):
                        error_text = select_nw_result.content[0].text
                    failure_reason = f"failed due to tool error: '{error_text}'."
                
                logger.error(f"Part 1 FAILED: Network selection for '{network_to_select_name}' {failure_reason} Full result: {select_nw_result}")
                return # Exit main if selection fails, maintaining original script's behavior on Part 1 failure.

            # If selection was successful, proceed to create connector
            logger.info(f"Network '{network_to_select_name}' selected (URI: {selected_network_uri_for_log}). Proceeding to test connector creation.")
            connector_id = await test_create_network_connector(session)

            if connector_id and connector_id != ERROR_NETWORK_REQUIRED:
                logger.info(f"Part 1 SUCCESS: Network Connector created with ID: {connector_id} using selected network '{network_to_select_name}' (Selected URI: {selected_network_uri_for_log}).")
            elif connector_id == ERROR_NETWORK_REQUIRED:
                logger.error(f"Part 1 FAILED: Connector creation failed with '{ERROR_NETWORK_REQUIRED}', but network '{network_to_select_name}' was selected (Selected URI: {selected_network_uri_for_log}). This may indicate an issue with the selection state or the connector tool's ability to use it.")
            else:
                logger.error(f"Part 1 FAILED: Network Connector creation failed after selecting network '{network_to_select_name}' (Selected URI: {selected_network_uri_for_log}). Connector creation returned: {connector_id}")

            # === Part 2: Test with a non-Network object selected (User Group) ===
            logger.info("\n--- Part 2: Testing connector creation with a selected non-Network object (User Group) ---")
            ug_name = f"conn-test-ug-{str(uuid.uuid4()).split('-')[0]}"
            # Ensure vpnRegionIds is provided as a list of strings
            create_ug_payload = CreateUserGroupArgs(name=ug_name, vpnRegionIds=["us-west-1"]) # Example region # type: ignore
            ug_creation_call: CallToolResult = await session.call_tool(
                "create_user_group_tool",
                {"args": create_ug_payload.model_dump(by_alias=True, exclude_none=True)}
            )

            ug_id: Optional[str] = None
            if not ug_creation_call.isError and ug_creation_call.content and isinstance(ug_creation_call.content[0], TextContent):
                ug_payload_data = json.loads(ug_creation_call.content[0].text)
                if ug_payload_data.get("data", {}).get("id"): # Assuming structure {data: {id: ...}}
                    ug_id = ug_payload_data["data"]["id"]
                    logger.info(f"Successfully created user group '{ug_name}' with ID: {ug_id}")

            if not ug_id:
                logger.error(f"Part 2 FAILED: Prerequisite user group creation for '{ug_name}' failed. Response: {ug_creation_call}")
                return

            logger.info(f"Attempting to select user group: {ug_name} (ID: {ug_id})")
            select_ug_result: CallToolResult = await session.call_tool(
                "select_object_tool", {"object_type": "user_group", "search_term": ug_name}
            )
            
            ug_selected_successfully = False
            if not select_ug_result.isError and select_ug_result.content and isinstance(select_ug_result.content[0], EmbeddedResource):
                selected_resource_content_ug = select_ug_result.content[0].resource
                if hasattr(selected_resource_content_ug, 'uri'):
                    uri_str = str(selected_resource_content_ug.uri)
                    if ug_id in uri_str:
                        logger.info(f"Successfully selected user group '{ug_name}' (URI: {uri_str}).")
                        ug_selected_successfully = True
                else:
                    logger.warning(f"Selected object for user group '{ug_name}' is EmbeddedResource but missing 'uri' in its 'resource' attribute.")
            elif not select_ug_result.isError and select_ug_result.content:
                logger.warning(f"User group selection for '{ug_name}' did not return EmbeddedResource. Got type: {type(select_ug_result.content[0])}, Content: {select_ug_result.content[0]}")

            if not ug_selected_successfully:
                logger.error(f"Part 2 FAILED: User group selection for '{ug_name}' failed. Result: {select_ug_result}")
                return
            
            connector_res_non_nw = await test_create_network_connector(session)
            if connector_res_non_nw == ERROR_NETWORK_REQUIRED:
                logger.info("Part 2 SUCCESS: Connector creation correctly failed with 'network required' error when a user group was selected.")
            else:
                logger.error(f"Part 2 FAILED: Expected '{ERROR_NETWORK_REQUIRED}', got: {connector_res_non_nw}")

            # === Part 3: Test with no object selected (or selection cleared/invalidated) ===
            logger.info("\n--- Part 3: Testing connector creation with no object effectively selected ---")
            logger.info("Attempting to select a non-existent object to clear/invalidate selection.")
            select_non_existent_call: CallToolResult = await session.call_tool(
                "select_object_tool", {"object_type": "network", "search_term": f"nonexistent-{uuid.uuid4()}"}
            )
            
            # Check if selection failed as expected (e.g., "No object found")
            cleared_selection = False
            if not select_non_existent_call.isError and \
               select_non_existent_call.content and \
               isinstance(select_non_existent_call.content[0], TextContent) and \
               ("No object found" in select_non_existent_call.content[0].text or \
                "Could not find" in select_non_existent_call.content[0].text or \
                "does not exist" in select_non_existent_call.content[0].text.lower()): # More general check
                logger.info("Selection effectively cleared/invalidated by searching for a non-existent object.")
                cleared_selection = True
            elif select_non_existent_call.isError: # Also counts as invalid selection for next step
                 logger.info("Selection failed due to tool error, effectively invalidating selection.")
                 cleared_selection = True
            else:
                logger.warning(f"Could not definitively clear selection, select_object returned: {select_non_existent_call}")
                # Proceeding anyway, as the selection might be invalid for the connector tool

            if cleared_selection:
                connector_res_no_sel = await test_create_network_connector(session)
                if connector_res_no_sel == ERROR_NETWORK_REQUIRED:
                    logger.info("Part 3 SUCCESS: Connector creation correctly failed with 'network required' error when no valid object was selected.")
                else:
                    logger.error(f"Part 3 FAILED: Expected '{ERROR_NETWORK_REQUIRED}', got: {connector_res_no_sel} (no selection).")
            else:
                logger.warning("Part 3 SKIPPED: Could not confirm selection was cleared/invalidated.")


        except Exception as e:
            logger.error(f"An error occurred in main: {e}", exc_info=True)
        finally:
            logger.info("Client operations finished. AsyncExitStack will handle cleanup.")

if __name__ == "__main__":
    asyncio.run(main())
