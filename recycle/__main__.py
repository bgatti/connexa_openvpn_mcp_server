import sys
import logging

# Basic logger for __main__ in case server.py's logging isn't set up yet
# when 'app' is imported, or if there's an issue importing 'app'.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s (%(module)s) - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

try:
    # Use relative import to get 'app' from server.py within the same package
    # server.py should define 'app = FastMCP(...)' at the module level.
    from server import app
    logger.info("Successfully imported 'app' from .server in __main__.py.")
except ImportError as e:
    logger.critical(f"CRITICAL: Error importing 'app' from .server in __main__.py: {e}. Ensure server.py exists and is importable, and that 'mcp-server-demo' is run as a module (e.g., python -m mcp-server-demo).", exc_info=True)
    sys.exit(1)
except AttributeError as e:
    logger.critical(f"CRITICAL: AttributeError: 'app' not found in .server module: {e}. Ensure server.py defines 'app = FastMCP(...)' at the module level.", exc_info=True)
    sys.exit(1)

# The main execution block is implicitly __name__ == "__main__" when run via python -m
logger.info(f"Starting '{app.name}' MCP server via __main__.py for stdio transport...")
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
