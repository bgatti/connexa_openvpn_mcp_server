import asyncio
import logging
import os
from contextlib import AsyncExitStack

# Correct imports based on the mcp example client
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import AnyUrl # Import AnyUrl

# Configure basic logging for the client
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """
    MCP Client Tester (Refactored to use mcp.ClientSession and stdio_client)
    This script starts an MCP client, connects to the OpenVPN-Connexa-Server
    (by launching it as a subprocess via stdio), calls a tool, and prints the result.
    """
    # Command to start the MCP server.
    server_command_parts = ["uv", "run", "-m", "connexa_openvpn_mcp_server"]
    
    # StdioServerParameters expects the command and args separately.
    # The first part is the command, the rest are args.
    # We need to ensure 'uv' is resolved to its full path if not universally in PATH
    # for subprocesses, but shutil.which within StdioServerParameters usually handles this.
    command_executable = server_command_parts[0]
    command_args = server_command_parts[1:]

    server_params = StdioServerParameters(
        command=command_executable,
        args=command_args,
        # Set working directory if .env file is in a specific place relative to the server's execution
        # cwd="C:/GitRepos/python-sdk" # Example: if .env is in python-sdk root
        # If not set, the server's CWD might be this script's directory or system default.
        # The OpenVPN Connexa server loads .env from its CWD.
        # The original server run from `python-sdk` had CWD `C:\GitRepos\python-sdk`.
        # To ensure .env is found, explicitly set CWD for the server process.
        # Assuming .env is in 'C:/GitRepos/python-sdk' or 'C:/GitRepos/python-sdk/connexa_openvpn_mcp_server'
        # If the .env is in 'C:/GitRepos/python-sdk/connexa_openvpn_mcp_server', then CWD should be that.
        # If the .env is in 'C:/GitRepos/python-sdk', then CWD should be that.
        # The server logs showed it looking for .env in C:\GitRepos\python-sdk
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")) # Sets CWD to python-sdk
    )

    async with AsyncExitStack() as stack:
        try:
            logger.info(f"Initializing stdio client for command: {' '.join(server_command_parts)}")
            
            stdio_transport = await stack.enter_async_context(
                stdio_client(server_params)
            )
            read_stream, write_stream = stdio_transport
            logger.info("Stdio transport established.")

            # The name "OpenVPN-Connexa-Server" is not used by ClientSession directly,
            # but it's good to know what server we expect.
            # The server's actual name is defined in its own server.py (app = FastMCP(name=...))
            # This client connects to one server defined by server_params.
            session = await stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            logger.info("MCP ClientSession created. Initializing session...")
            await session.initialize()
            logger.info("Session initialized.")

            # Wait a bit for the server to fully initialize if needed.
            # The server logs indicate it takes a few seconds for all tools to register.
            logger.info("Waiting for server to be ready...")
            await asyncio.sleep(5) # Adjust if server startup is slow

            logger.info("Attempting to call 'validate_credentials'...")
            tool_result = await session.call_tool("validate_credentials", {})
            
            logger.info("Result from 'validate_credentials':")
            logger.info(tool_result)

            # Demonstrate selecting base objects
            base_objects = ["network", "host", "user_group"]
            for obj_type in base_objects:
                logger.info(f"Attempting to call 'select_object_tool' for object type: {obj_type}")
                select_object_payload = {"object_type": obj_type}
                select_object_result = await session.call_tool("select_object_tool", select_object_payload)
                logger.info(f"Result from 'select_object_tool' for {obj_type}:")
                logger.info(select_object_result)

            # Get current selection resource (after selections)
            logger.info("Attempting to read 'mcp://resources/current_selection' resource...")
            current_selection_resource_pydantic_uri = AnyUrl("mcp://resources/current_selection")
            current_selection_result = await session.read_resource(current_selection_resource_pydantic_uri)
            logger.info(f"Result from reading '{current_selection_resource_pydantic_uri}':")
            logger.info(current_selection_result)

            logger.info("Listing available tools...")
            list_tools_result = await session.list_tools()
            tool_names = [tool.name for tool in list_tools_result.tools]
            logger.info(f"Available tools: {tool_names}")

            logger.info("Listing available resources (including dynamic)...")
            list_resources_result = await session.list_resources()
            resource_names = [resource.name if hasattr(resource, 'name') else resource.uri for resource in list_resources_result.resources]
            logger.info(f"Available resources: {resource_names}")

            # Demonstrate selecting a specific network
            logger.info("Attempting to call 'select_object_tool' for network: test-network-71c7398d")
            select_network_payload = {"object_type": "network", "name_search": "test-network-71c7398d"}
            select_network_result = await session.call_tool("select_object_tool", select_network_payload)
            logger.info("Result from 'select_object_tool' for network test-network-71c7398d:")
            logger.info(select_network_result)

        except Exception as e:
            logger.error(f"An error occurred: {e}", exc_info=True)
        finally:
            logger.info("Client operations finished. AsyncExitStack will handle cleanup.")

if __name__ == "__main__":
    asyncio.run(main())
