import sys
import logging
import os

# Basic logger for __main__ in case server.py's logging isn't set up yet
# when 'app' is imported, or if there's an issue importing 'app'.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s (%(module)s) - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

try:
    # This works when run as `python -m connexa_openvpn_mcp_server`
    from .server import app
    logger.info("Successfully imported 'app' using relative import (.server) in __main__.py.")
except ImportError:
    logger.warning("Relative import '.server' failed. Attempting to adjust sys.path for direct script execution or alternative runners like 'uv run'.")
    # This block is for when __main__.py is run as a script directly
    # (e.g., python connexa_openvpn_mcp_server/__main__.py or potentially uv run)
    # We need to ensure the parent directory of 'connexa_openvpn_mcp_server' is in sys.path
    # so that 'from connexa_openvpn_mcp_server.server import app' can work.

    # Get the directory of the current script (__main__.py)
    current_script_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_script_path) # Directory of __main__.py

    # Get the parent directory (e.g., /path/to/python-sdk, which contains connexa_openvpn_mcp_server package)
    parent_dir = os.path.dirname(current_dir)

    # Add the parent directory to sys.path if it's not already there
    # This allows 'import connexa_openvpn_mcp_server' and its submodules.
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
        logger.info(f"Added '{parent_dir}' to sys.path to enable absolute package imports.")

    try:
        from connexa_openvpn_mcp_server.server import app
        logger.info("Successfully imported 'app' using absolute import (connexa_openvpn_mcp_server.server) after sys.path adjustment.")
    except ImportError as e_abs:
        logger.critical(f"CRITICAL: Failed to import 'app' using absolute import 'connexa_openvpn_mcp_server.server' even after sys.path adjustment: {e_abs}. Ensure connexa_openvpn_mcp_server/server.py exists and is importable.", exc_info=True)
        sys.exit(1)
    except AttributeError as e_attr_abs:
        logger.critical(f"CRITICAL: AttributeError after sys.path adjustment: 'app' not found in 'connexa_openvpn_mcp_server.server' module: {e_attr_abs}. Ensure server.py defines 'app = FastMCP(...)' at the module level.", exc_info=True)
        sys.exit(1)
except AttributeError as e_attr_rel: # Catch AttributeError from the initial relative import attempt
    logger.critical(f"CRITICAL: AttributeError during relative import: 'app' not found in .server module: {e_attr_rel}. Ensure server.py defines 'app = FastMCP(...)' at the module level.", exc_info=True)
    sys.exit(1)

if __name__ == "__main__":
    # This block runs only when the script is executed directly
    # (e.g., python -m connexa_openvpn_mcp_server or python connexa_openvpn_mcp_server/__main__.py)
    # It will NOT run when imported by `mcp dev`.
    logger.info(f"Executing as __main__: Starting '{app.name}' MCP server for stdio transport...")
    try:
        app.run(transport="stdio")
        # If app.run() returns, it means the server has stopped (e.g., stdio streams closed).
        logger.info(f"'{app.name}' MCP server (via __main__.py) app.run() has completed. Server is stopping.")
    except SystemExit as e:
        # Log SystemExit if it's not a clean exit (e.g., sys.exit(0) might be fine)
        if e.code != 0:
            logger.error(f"'{app.name}' MCP server (via __main__.py) exited with SystemExit code {e.code}.", exc_info=True)
        else:
            logger.info(f"'{app.name}' MCP server (via __main__.py) exited cleanly with SystemExit code {e.code}.")
        raise # Re-raise SystemExit to ensure proper exit code propagation
    except KeyboardInterrupt:
        logger.info(f"'{app.name}' MCP server (via __main__.py) received KeyboardInterrupt. Shutting down gracefully.")
    except Exception as e:
        logger.critical(f"CRITICAL: '{app.name}' MCP server (via __main__.py) exited with an unexpected error: {e}", exc_info=True)
    finally:
        logger.info(f"'{app.name}' MCP server (via __main__.py) __main__ execution block is ending.")
