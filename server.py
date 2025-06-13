import sys
import logging
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Unique log message to confirm file version ---
TEMP_SERVER_VERSION_LOG = "SERVER.PY VERSION: 2025-06-07_1530_EXPLICIT_NAMES"

print(f"--- SERVER.PY TOP LEVEL PRINT: Attempting to run {__file__} ---", flush=True)
print(f"--- SERVER.PY SYS.PATH: {sys.path} ---", flush=True)
print(f"--- SERVER.PY CWD: {os.getcwd()} ---", flush=True)
print(f"--- SERVER.PY PYTHONPATH ENV: {os.environ.get('PYTHONPATH')} ---", flush=True)


# MCP Framework Imports
from mcp.server.fastmcp import FastMCP
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.shared._httpx_utils import create_mcp_http_client

# Third-Party Imports
import anyio
import click

# Local Application Imports
# For initializing config, changed to relative and specific imports
from connexa_openvpn_mcp_server.connexa.config_manager import get_api_token as cm_get_api_token, \
                            initialize_config as cm_initialize_config, \
                            BUSINESS_NAME as CM_BUSINESS_NAME, \
                            API_TOKEN as CM_API_TOKEN, \
                            CLIENT_ID as CM_CLIENT_ID
from connexa_openvpn_mcp_server.connexa.config_manager import validate_credentials
from connexa_openvpn_mcp_server.prompts import CONNEXA_API_GUIDELINES


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout # Ensure this is also stdout if it were active
)
logger = logging.getLogger(__name__)

logger.info("Initializing shared configuration...")
try:
    if not cm_initialize_config():
        logger.warning("Failed to initialize shared configuration. API calls may fail.")
except Exception as e:
    logger.critical(f"Critical error during config initialization: {e}", exc_info=True)
    sys.exit(1) # Exit if config is absolutely essential

# Initialize FastMCP app at the module level
app = FastMCP(
    name="OpenVPN-Connexa-Server",
    version="1.0.0",
    instructions="Provides tools for interacting with various OpenVPN Connexa VPN APIs."
)
# app.current_selection = {"type": None, "id": None, "name": None, "data": None}
logger.info(f"FastMCP application '{app.name}' created at module level.")

# Import for dynamic tools and selected object
from connexa_openvpn_mcp_server.connexa.selected_object import CURRENT_SELECTED_OBJECT


# --- Register Prompts using @app.prompt() decorator style ---
logger.info("Registering prompts dynamically...")
loop_count = 0
for guideline_data in CONNEXA_API_GUIDELINES:
    loop_count += 1
    guideline_id = guideline_data['id']
    guideline_text = guideline_data['text']
    logger.info(f"Loop iteration {loop_count}, attempting to register prompt_id: {guideline_id}")

    # Define the actual function that will be decorated
    # Use a default argument to correctly capture the guideline_text for each iteration
    def _create_prompt_func(text_to_return=guideline_text):
        # According to the example, returning a string is sufficient.
        # FastMCP should wrap this in a PromptMessage.
        return text_to_return

    # Set the function's name and docstring, which @app.prompt() might use
    _create_prompt_func.__name__ = guideline_id
    # Create a summary for the docstring if text is too long
    docstring_summary = (guideline_text[:150] + "...") if len(guideline_text) > 150 else guideline_text
    _create_prompt_func.__doc__ = docstring_summary
    
    # Apply the decorator
    # This is equivalent to:
    # @app.prompt()
    # def some_name(): ...
    # So, we call app.prompt() to get the decorator, then call the decorator with the function
    try:
        logger.info(f"Before decorating prompt_id: {guideline_id}")
        decorated_func = app.prompt()(_create_prompt_func)
        logger.info(f"After decorating, successfully registered prompt: {guideline_id}")
    except Exception as e_prompt:
        logger.error(f"Failed to register prompt {guideline_id}: {e_prompt}", exc_info=True)

# --- Import Tool Modules and Register Tools/Resources on the module-level 'app' ---
try:
    logger.info("Importing tool modules...")
    from connexa_openvpn_mcp_server.connexa import connector_tools
    from connexa_openvpn_mcp_server.connexa import mcp_ovpn_res
    from connexa_openvpn_mcp_server.connexa import connexa_api
    from connexa_openvpn_mcp_server.connexa import selected_object
    from connexa_openvpn_mcp_server.connexa.delete_tool import delete_selected_object
    from connexa_openvpn_mcp_server import server_tools # Renamed for clarity, as it now contains more than just AWS related tools
    from connexa_openvpn_mcp_server.connexa  import creation_tools

    logger.info("Tool modules imported (including connexa_api.py, mcp_ovpn_res.py, server_tools.py, creation_tools.py, and delete_tool.py).")

    logger.info("Registering Resources...")
    # Register the new resource. The URI will be derived from the function name
    # or can be specified. Let's use a specific URI.
    # Resource functions are accessed via the imported mcp_ovpn_res module.
    app.resource(uri="mcp://resources/user_groups_summary")(mcp_ovpn_res.get_user_groups_resource)
    

    # Register the API overview resource using the synchronous wrapper
    app.resource(uri="mcp://resources/api_overview")(mcp_ovpn_res.get_api_overview_resource_sync)
    # Register the new api_commands resource using the synchronous wrapper
#    app.resource(uri="mcp://resources/api_commands")(mcp_ovpn_res.get_api_commands_resource_sync)
    # Register the new schema resource (pointing to schema.json content) using the synchronous wrapper
    app.resource(uri="mcp://resources/schema")(mcp_ovpn_res.get_schema_json_resource_sync)
    # Register the current_selection resource (already synchronous)
    app.resource(uri="mcp://resources/current_selection")(mcp_ovpn_res.get_current_selection_data)
    # Register the new creation_schema resources using the synchronous wrappers
    # Route for specific object_type
    app.resource(uri="mcp://resources/creation_schema/{object_type}")(mcp_ovpn_res.get_creation_schema_resource_sync)
    # Route for base URI (no object_type)
    app.resource(uri="mcp://resources/creation_schema")(mcp_ovpn_res.get_creation_schema_resource_base_sync) # Uses the new wrapper
    # Register the new selected_object_schema resource
    app.resource(uri="mcp://resources/selected_object_schema")(server_tools.get_selected_object_schema_resource)
    logger.info("Resources registered (including api_commands, schema, current_selection, creation_schema, and selected_object_schema) using synchronous wrappers.")

    logger.info("Registering Custom API tools (from connexa_api.py)...")
#    app.tool()(connexa_api.call_api)


    logger.info("Registering Connector tools...")
    logger.info("Connector tools registered.")

    logger.info("Registering Selection and Update tools...")
    app.tool()(selected_object.select_object_tool)
    app.tool()(delete_selected_object)
    app.tool(name="complete_update_selected")(selected_object.complete_update_selected) # Register the new update tool
    logger.info("Selection and Update tools registered.")

    logger.info("Registering Creation tools (from creation_tools.py)...")
    app.tool(name="create_network_tool")(creation_tools.create_network_tool)
    app.tool(name="create_network_connector_tool")(creation_tools.create_network_connector_tool)
    app.tool(name="create_user_group_tool")(creation_tools.create_user_group_tool)
    app.tool(name="create_host_tool")(creation_tools.create_host_tool)
    app.tool(name="create_host_connector_tool")(creation_tools.create_host_connector_tool)
    app.tool(name="create_device_tool")(creation_tools.create_device_tool)
    app.tool(name="create_dns_record_tool")(creation_tools.create_dns_record_tool)
    app.tool(name="create_access_group_tool")(creation_tools.create_access_group_tool)
    app.tool(name="create_location_context_tool")(creation_tools.create_location_context_tool)
    app.tool(name="create_device_posture_tool")(creation_tools.create_device_posture_tool)
    app.tool(name="create_user_tool")(creation_tools.create_user_tool)
    logger.info(f"Creation tools registration attempted. TEMP_SERVER_VERSION_LOG: {TEMP_SERVER_VERSION_LOG}")

    logger.info("Registering AWS Resources...")
    app.resource(uri="mcp://resources/aws_regions")(server_tools.get_available_aws_regions_resource) # Use the renamed import
    logger.info("AWS Resources registered.")

    logger.info("All tool and resource registrations attempted.")

except ImportError as e:
    logger.critical(f"Failed to import prerequisite modules or tool modules: {e}. Server cannot be fully configured.", exc_info=True)
    # If 'app' was not initialized (e.g. prompt module import failed), server cannot run.
    # We might need to sys.exit(1) here or ensure 'app' is checked before use in __main__
    # For now, this error means 'app' might not be defined or fully functional.
    # Re-raising to make it fatal or exiting.
    # sys.exit(f"Critical import error: {e}") # Original handling if app was in try block
    # Now, if tool import fails, app is still defined. Server might be partially functional.
    logger.error(f"Could not import one or more tool modules: {e}. Some tools may not be available.", exc_info=True)
except Exception as e: # Catch other exceptions during tool/resource registration
    logger.error(f"Error during tool/resource registration: {e}", exc_info=True)
    # App is defined, but registrations may have failed.

# 'app' is now guaranteed to be defined at module level.
logger.info("All attempted tool and resource registrations complete. FastMCP 'app' is configured.")
logger.info("This server can be run via 'uv run connexa_openvpn_mcp_server' for HTTP or 'python -m connexa_openvpn_mcp_server.server' for stdio.")


if __name__ == "__main__":
    # 'app' is a module-level variable, so it's defined.
    logger.info(f"Starting {app.name} MCP server for stdio...")
    try:
        # The 'app' instance should be defined if we reached here.
        app.run(transport="stdio")
        logger.info(f"{app.name} MCP server mcp_server.run() has returned. Server stopping.")
    except SystemExit as e:
        logger.error(f"{app.name} MCP server exited with SystemExit: {e}", exc_info=True)
        raise
    except KeyboardInterrupt:
        logger.info(f"{app.name} MCP server received KeyboardInterrupt. Shutting down.")
    except Exception as e:
        logger.error(f"{app.name} MCP server exited with an unexpected error: {e}", exc_info=True)
    finally:
        logger.info(f"{app.name} MCP server script's __main__ block is ending.")
