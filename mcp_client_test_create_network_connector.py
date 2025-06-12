# To run this file correctly from the project root (c:/GitRepos/python-sdk):
# PS C:\GitRepos\python-sdk> uv run python -m connexa_openvpn_mcp_server.mcp_client_test_create_network_connector

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

from connexa_openvpn_mcp_server.connexa.connector_tools import CreateConnectorArgs
from connexa_openvpn_mcp_server.connexa.creation_tools import CreateNetworkArgs
# CURRENT_SELECTED_OBJECT and CreateUserGroupArgs are no longer needed for this simplified test
# from connexa_openvpn_mcp_server.connexa.selected_object import CURRENT_SELECTED_OBJECT
# from connexa_openvpn_mcp_server.connexa.creation_tools import CreateUserGroupArgs


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Expected error identifier for specific failure cases
ERROR_NETWORK_REQUIRED = "ERROR_NETWORK_REQUIRED" # Kept for now, though direct test removed
ERROR_CONNEXA_REGION_NOT_SET = "ERROR_CONNEXA_REGION_NOT_SET"

async def test_create_network_connector(session: ClientSession, actual_network_id: str, connector_name_to_create: str) -> tuple[Optional[str], Optional[str]]:
    """
    Tests creating a network connector.
    Uses the provided actual_network_id.
    Returns a tuple: (connector_id, connector_name)
    """
    logger.info(f"\n--- Testing Network Connector Creation for '{connector_name_to_create}' ---")
    
    try:
        vpn_region_id_from_env = os.environ.get("CONNEXA_REGION")
        if not vpn_region_id_from_env:
            logger.error("CONNEXA_REGION environment variable not set. Cannot determine vpn_region_id for connector creation.")
            return ERROR_CONNEXA_REGION_NOT_SET, None

        args = CreateConnectorArgs(
            name=connector_name_to_create,
            network_id=actual_network_id,
            vpn_region_id=vpn_region_id_from_env,
            description=f"Test connector {connector_name_to_create}"
        )
        logger.info(f"Attempting to create network connector: {args.name} for network_id='{actual_network_id}' and vpn_region_id='{vpn_region_id_from_env}'")

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
                        logger.info(f"Parsed tool response payload: {json.dumps(payload_data, indent=2)}") # Log the parsed payload

                        # Log top-level status and message if present
                        tool_status = payload_data.get("status")
                        tool_message = payload_data.get("message")
                        if tool_status == "warning":
                            logger.warning(f"Tool returned status: {tool_status}, message: {tool_message}")
                        elif tool_status or tool_message:
                            logger.info(f"Tool returned status: {tool_status}, message: {tool_message}")

                        # The actual connector data is expected to be in payload_data["data"]
                        actual_connector_data = payload_data.get("data")

                        created_id = None
                        created_name = None

                        if isinstance(actual_connector_data, dict):
                            created_id = actual_connector_data.get("id")
                            created_name = actual_connector_data.get("name")

                        if created_id and created_name: # Success if id and name are found in the data field
                            logger.info(f"Successfully created network connector '{created_name}' with ID: {created_id} (from data field)")
                            logger.info("Adding 30-second delay to allow provisioning to finish...")
                            await asyncio.sleep(30) # Add delay here

                            return created_id, created_name
                        
                        # If id/name not found in the data field, check for error status in the top-level payload
                        tool_status = payload_data.get("status")
                        tool_message = payload_data.get("message")

                        if tool_status == "error":
                            logger.error(f"Connector '{args.name}' creation failed (Client Check v2): Tool reported an error status. Message: {tool_message}. Full Payload: {payload_data}")
                            return None, args.name # Return name for context, but ID is None
                        elif tool_status == "warning":
                             logger.warning(f"Connector '{args.name}' creation (Client Check v2): Tool reported a warning status. Message: {tool_message}. Full Payload: {payload_data}")
                             # Continue to check for data even with a warning
                             if created_id and created_name:
                                 logger.info(f"Despite warning, found connector ID '{created_id}' and name '{created_name}' in data field.")
                                 return created_id, created_name
                             else:
                                 logger.error(f"Connector '{args.name}' creation (Client Check v2): Tool reported warning, but ID or name not found in data field. Full Payload: {payload_data}")
                                 return None, args.name # Return name for context

                        # If neither ID/name found in data nor top-level error/warning, log unexpected format
                        logger.error(f"Connector '{args.name}' creation (Client Check v2): 'id' or 'name' not found in expected 'data' field or unexpected response format. Response: {payload_data}")
                        return None, args.name # Return name for context

                    except json.JSONDecodeError:
                        logger.error(f"Connector '{args.name}' creation: Failed to parse TextContent as JSON. Content: {payload_text}")
                        return None, None
                else: # Not TextContent
                    logger.warning(f"Connector '{args.name}' creation: Content is not TextContent. Type: {type(first_content)}")
                    return None, None
            else: # result.isError is False, but no content
                logger.warning(f"Connector '{args.name}' creation: Tool call successful but returned no content.")
                return None, None
        else: # result.isError is True
            error_message = "Unknown tool error"
            if result.content and len(result.content) > 0 and isinstance(result.content[0], TextContent):
                error_message = result.content[0].text
            logger.error(f"Tool 'create_network_connector_tool' for '{args.name}' reported an error: {error_message}")
            return None, None
            
    except Exception as e:
        logger.error(f"An exception occurred during network connector '{connector_name_to_create}' creation: {e}", exc_info=True)
        return None, None

async def main():
    # Load environment variables from .env file located in the same directory as this script
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        logger.info(f"Loaded environment variables from {dotenv_path}")
    else:
        logger.warning(f".env file not found at {dotenv_path}. Relying on system environment variables.")

    logger.info("Starting MCP client tester for Network and Connector creation & provisioning...")

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

            # === Validate Credentials ===
            logger.info("\n--- Validating Credentials ---")
            validate_result: CallToolResult = await session.call_tool(
                "validate_credentials",
                {} # No arguments required for validate_credentials
            )
            logger.info(f"Credential validation result: {validate_result}")

            if validate_result.isError:
                error_message = "Unknown validation error"
                if validate_result.content and len(validate_result.content) > 0 and isinstance(validate_result.content[0], TextContent):
                    error_message = validate_result.content[0].text
                logger.error(f"Credential validation failed: {error_message}. Cannot proceed.")
                return # Stop execution if validation fails
            else:
                logger.info("Credential validation successful.")

            logger.info("Waiting a few seconds for server to be ready...")
            await asyncio.sleep(5)

            # === Part 0: Create (Upsert) a Network ===
            logger.info("\n--- Part 0: Creating/Upserting a Network ---")
            network_name = f"test-network-{str(uuid.uuid4()).split('-')[0]}"
            create_network_args = CreateNetworkArgs(
                name=network_name, 
                internetAccess="SPLIT_TUNNEL_ON",
                description=None,
                egress=None,
                routes=None,
                connectors=None,
                tunnelingProtocol=None,
                gatewaysIds=None
            )
            logger.info(f"Attempting to create network: {network_name}")

            create_network_result: CallToolResult = await session.call_tool(
                "create_network_tool",
                {"args": create_network_args.model_dump(by_alias=True, exclude_none=True)}
            )

            created_network_id: Optional[str] = None
            created_network_name: Optional[str] = None

            if not create_network_result.isError and create_network_result.content and isinstance(create_network_result.content[0], TextContent):
                try:
                    network_data = json.loads(create_network_result.content[0].text)
                    logger.info(f"Create network tool returned data: {json.dumps(network_data, indent=2)}")
                    if isinstance(network_data, dict) and network_data.get("id") and network_data.get("name"):
                         created_network_id = network_data.get("id")
                         created_network_name = network_data.get("name")
                         logger.info(f"Successfully created/retrieved network '{created_network_name}' with ID: {created_network_id}")
                    elif isinstance(network_data, dict) and network_data.get("status") in ["error", "warning"]:
                         logger.error(f"Create network tool reported status '{network_data.get('status')}': {network_data.get('message', 'No message')}.")
                    else:
                         logger.error(f"Create network tool returned data in an unexpected format: {network_data}")
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON response from create_network_tool: {create_network_result.content[0].text}")
            elif create_network_result.isError:
                error_text = "Unknown tool error"
                if create_network_result.content and len(create_network_result.content) > 0 and isinstance(create_network_result.content[0], TextContent):
                    error_text = create_network_result.content[0].text
                logger.error(f"Create network tool returned an error: {error_text}.")
            else:
                 logger.warning("Create network tool returned no error and no content.")

            if not created_network_id or not created_network_name:
                logger.error("Part 0 FAILED: Network creation/retrieval failed. Cannot proceed.")
                return

            logger.info(f"Part 0 SUCCESS: Network '{created_network_name}' (ID: {created_network_id}) is ready.")

            # === Part 1: Select the Network (implicitly done by creation tool if it sets selected_object) ===
            # For robustness, explicitly select if `create_network_tool` doesn't guarantee selection.
            # Assuming `create_network_tool` now handles selection or we rely on explicit network_id for connector.
            # The `select_object_tool` call for network is removed as `create_network_connector` takes explicit `network_id`.
            logger.info(f"\n--- Part 1: Network '{created_network_name}' (ID: {created_network_id}) is available for connector creation ---")


            # === Part 2: Testing connector creation using the Network ID from Part 0 ===
            logger.info(f"\n--- Part 2: Creating Network Connector in Network '{created_network_name}' (ID: {created_network_id}) ---")
            
            connector_name_part2 = f"test-conn-main-{str(uuid.uuid4()).split('-')[0]}"
            created_connector_id, created_connector_name = await test_create_network_connector(session, created_network_id, connector_name_part2)

            if created_connector_id and created_connector_id != ERROR_NETWORK_REQUIRED and created_connector_id != ERROR_CONNEXA_REGION_NOT_SET:
                logger.info(f"Part 2 SUCCESS: Network Connector '{created_connector_name}' created with ID: {created_connector_id} for network '{created_network_name}'.")
                
                aws_region_to_use = os.environ.get("AWS_REGION")
                if not aws_region_to_use:
                    aws_region_to_use = os.environ.get("AWS_DEFAULT_REGION")
                
                if not aws_region_to_use:
                    logger.warning("Neither AWS_REGION nor AWS_DEFAULT_REGION environment variable found. Skipping provisioning step for the connector.")
            elif created_connector_id == ERROR_NETWORK_REQUIRED: # Should not happen if network_id is always passed
                logger.error(f"Part 2 FAILED: Connector creation failed with '{ERROR_NETWORK_REQUIRED}'. This is unexpected as network_id was provided.")
            elif created_connector_id == ERROR_CONNEXA_REGION_NOT_SET:
                logger.error(f"Part 2 FAILED: Connector creation failed because CONNEXA_REGION environment variable was not set.")
            else:
                logger.error(f"Part 2 FAILED: Network Connector creation failed for network '{created_network_name}'. Connector ID: '{created_connector_id}', Name: '{created_connector_name}'")

        except Exception as e:
            logger.error(f"An error occurred in main: {e}", exc_info=True)
        finally:
            logger.info("Client operations finished. AsyncExitStack will handle cleanup.")

if __name__ == "__main__":
    asyncio.run(main())
