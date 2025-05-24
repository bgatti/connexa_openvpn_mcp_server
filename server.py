import sys
import logging
import os # Added for os.environ
from mcp.server.fastmcp import FastMCP
from . import config_manager # For initializing config, changed to relative
from . import prompts as guideline_prompt_provider # Import the prompts module


import anyio
import click
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.shared._httpx_utils import create_mcp_http_client



# Configure basic logging (similar to double_factorial_mcp_server)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Log environment details early
logger.info(f"Python version: {sys.version}")
logger.info(f"Python executable: {sys.executable}")
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"sys.path: {sys.path}")
# Optionally log specific environment variables if relevant, e.g., PYTHONPATH
# logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH')}")


# This 'app' variable will be defined inside if __name__ == "__main__"
# For Uvicorn (via main.py) to work, it needs 'app' at the module level.
# We will define it here, but the main execution logic will be in the main block.

# --- API Configuration Access Functions ---
# These functions provide a clear interface for other modules (like api.py)
# to get necessary API details, managed by this server module.

def get_connexa_base_url() -> str:
    """
    Returns the base URL for the OpenVPN Connexa API.
    The BUSINESS_NAME is sourced from config_manager.
    """
    # Ensure config_manager is initialized if it hasn't been (though it's done globally below)
    if not config_manager.API_TOKEN and not config_manager.CLIENT_ID: # Heuristic to check if init ran
        logger.warning("config_manager might not be initialized when calling get_connexa_base_url early.")
        # Attempting to initialize here might be too late or cause issues if called during import.
        # Relying on the global initialization below.
    
    # Construct base URL using BUSINESS_NAME from config_manager
    # This makes it clear that BUSINESS_NAME is part of the API configuration.
    if not config_manager.BUSINESS_NAME:
        logger.error("OVPN_BUSINESS_NAME is not configured in config_manager. Cannot determine base URL.")
        # Fallback or raise error, for now, returning a placeholder or empty string
        return "https://your_business_name_here.api.openvpn.com" # Placeholder
    return f"https://{config_manager.BUSINESS_NAME}.api.openvpn.com"

def get_connexa_auth_token() -> str | None:
    """
    Retrieves the current API authentication token.
    This token is managed (fetched and refreshed) by config_manager.
    It's made obvious here that an API key/secret (managed by config_manager)
    is used to generate this token.
    """
    token = config_manager.get_api_token()
    if not token:
        logger.error("Failed to retrieve Connexa auth token via config_manager.")
    return token

# Initialize shared configuration and token (once for all tools)
# This should be done before FastMCP instantiation if it affects server setup,
# or before tool registration if tools rely on it at import/decoration time.
# For now, let's assume it's okay here.
logger.info("Initializing shared configuration...")
try:
    if not config_manager.initialize_config():
        logger.warning("Failed to initialize shared configuration. API calls may fail.")
except Exception as e:
    logger.critical(f"Critical error during config initialization: {e}", exc_info=True)
    sys.exit(1) # Exit if config is absolutely essential

app = FastMCP(
    name="OpenVPN-Connexa-Server", # Using a more typical MCP name
    version="1.0.0",
    instructions="Provides tools for interacting with various OpenVPN Connexa VPN APIs.", # 'description' is 'instructions' in FastMCP
    prompt_provider=guideline_prompt_provider.list_guideline_prompts,
    get_prompt_provider=guideline_prompt_provider.get_guideline_prompt
)
# app.current_selection = {"type": None, "id": None, "name": None, "data": None} # Temporarily commented out
logger.info(f"FastMCP application '{app.name}' created.")
logger.info(f"Prompt providers (list_guideline_prompts, get_guideline_prompt) passed to FastMCP for '{app.name}'.") # Adjusted log message

# --- Import and Register Tools ---
# It's generally cleaner to group imports and then registrations.

try:
    logger.info("Importing tool modules...")
    from . import user_tools # Changed to relative
    from . import device_tools # Changed to relative
    from . import dns_log_tools # Changed to relative
    from . import device_posture_tools # Changed to relative
    from . import group_tools # Changed to relative
    from . import mcp_ovpn_res
    from . import api_tools # Import the new api_tools module
    logger.info("Tool modules imported (including api_tools.py).")

    logger.info("Registering User tools...")
    app.tool()(user_tools.get_users)
    app.tool()(user_tools.get_user)
    app.tool()(user_tools.create_user)
    app.tool()(user_tools.update_user)
    app.tool()(user_tools.delete_user)
    logger.info("User tools registered.")

    logger.info("Registering Device tools...")
    app.tool()(device_tools.get_devices)
    app.tool()(device_tools.create_device)
    app.tool()(device_tools.get_device_details)
    app.tool()(device_tools.update_device_details)
    app.tool()(device_tools.delete_device_record)
    app.tool()(device_tools.generate_device_profile)
    app.tool()(device_tools.revoke_device_profile)
    logger.info("Device tools registered.")

    logger.info("Registering DNS Log tools...")
    app.tool()(dns_log_tools.enable_dns_log)
    app.tool()(dns_log_tools.disable_dns_log)
    app.tool()(dns_log_tools.get_user_dns_resolutions)
    logger.info("DNS Log tools registered.")

    logger.info("Registering Device Posture tools...")
    app.tool()(device_posture_tools.get_device_posture_policies)
    app.tool()(device_posture_tools.create_device_posture_policy)
    app.tool()(device_posture_tools.get_device_posture_policy_details)
    app.tool()(device_posture_tools.update_device_posture_policy_details)
    app.tool()(device_posture_tools.delete_device_posture_policy_record)
    logger.info("Device Posture tools registered.")

    logger.info("Registering Group tools...")
    app.tool()(group_tools.get_user_groups)
    app.tool()(group_tools.get_user_group)
    app.tool()(group_tools.create_user_group)
    app.tool()(group_tools.update_user_group_name)
    app.tool()(group_tools.update_user_group_internet_access)
    app.tool()(group_tools.update_user_group_max_device)
    app.tool()(group_tools.update_user_group_connect_auth)
    app.tool()(group_tools.update_user_group_all_regions_included)
    app.tool()(group_tools.delete_user_group)
    logger.info("Group tools registered.")

    logger.info("Registering Resources...")
    # Register the new resource. The URI will be derived from the function name
    # or can be specified. Let's use a specific URI.
    # Resource functions are accessed via the imported mcp_ovpn_res module.
    app.resource(uri="mcp://resources/user_groups_summary")(mcp_ovpn_res.get_user_groups_resource)
    app.resource(uri="mcp://resources/users_with_group_info")(mcp_ovpn_res.get_users_with_group_info_resource)
    app.resource(uri="mcp://resources/current_selection")(mcp_ovpn_res.get_current_selection_resource)
    # Register the new region resource
    app.resource(uri="mcp://resources/regions")(mcp_ovpn_res.get_regions_resource) # Ensure this is correctly registered
    logger.info("Resources registered.")

    logger.info("Registering Custom API tools (from api_tools.py)...")
    app.tool()(api_tools.call_api)
    app.tool()(api_tools.schema)
    logger.info("Custom API tools (call_api, schema) registered.")

    # logger.info("Registering Region tools...") # Section removed
    # app.tool()(region_tools.get_vpn_regions) # Line removed
    # logger.info("Region tools registered.") # Line removed

except ImportError as e:
    logger.error(f"Could not import one or more tool modules: {e}. Some tools may not be available.", exc_info=True)
except Exception as e:
    logger.error(f"Error during tool registration: {e}", exc_info=True)


logger.info("All attempted tool registrations complete. FastMCP 'app' is configured.")
logger.info("This server can be run via 'python -m mcp-server-demo.server' for stdio "
            "or via Uvicorn using 'mcp-server-demo.main:app' for HTTP.")


if __name__ == "__main__":
    logger.info(f"Starting {app.name} MCP server for stdio...")
    try:
        # The 'app' instance is already defined at the module level.
        # We just call its run() method here for stdio execution.
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
