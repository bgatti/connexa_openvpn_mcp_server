import json
import os
from typing import Optional, Dict, Any, List

import requests # Ensure requests is imported
from .server import get_connexa_base_url, get_connexa_auth_token

# api.json is now expected to be in the same directory as this file (api_tools.py)
# within the connexa_openvpn_mcp_server package.
API_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api.json')

def schema(api_group: str) -> List[Dict[str, Any]]:
    """
    Retrieves the API entries for a given API group from api.json.

    Args:
        api_group (str): The name of the API group (e.g., "User", "Network").

    Returns:
        List[Dict[str, Any]]: A list of API entries for the specified group, or an empty list if not found.
    """
    if not os.path.exists(API_JSON_PATH):
        print(f"Error: {API_JSON_PATH} not found.")
        return []
    
    try:
        with open(API_JSON_PATH, 'r') as f:
            all_apis: Dict[str, List[Dict[str, Any]]] = json.load(f)
        
        return all_apis.get(api_group, [])
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {API_JSON_PATH}.")
        return []
    except Exception as e:
        print(f"An unexpected error occurred while reading {API_JSON_PATH}: {e}")
        return []

def call_api(action: str, path: str, id: Optional[str] = None, value: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Calls an API endpoint.

    Args:
        action (str): The HTTP action (e.g., "get", "post", "put", "delete").
        path (str): The API path, potentially with an {id} placeholder.
        id (Optional[str]): The ID to substitute into the path if present. Defaults to None.
        value (Optional[Dict[str, Any]]): The JSON payload for "post" or "put" requests. Defaults to None.

    Returns:
        Dict[str, Any]: A dictionary containing the API response status and data, or an error message.
    """
    processed_path = path

    if "{id}" in path:
        if id:
            processed_path = path.replace("{id}", id)
        else:
            error_message = "Error: Path expects an {id} but no id was provided."
            print(error_message, flush=True)
            return {"status": "error", "message": error_message}

    action = action.lower()
    if action in ["post", "put"]:
        if value is None:
            error_message = f"Error: Action '{action}' requires a value/payload, but none was provided."
            print(error_message, flush=True)
            return {"status": "error", "message": error_message}
    
    base_url = get_connexa_base_url()
    auth_token = get_connexa_auth_token()

    if not base_url or base_url == "https://your_business_name_here.api.openvpn.com": # Check for placeholder
        error_message = "Error: API base URL is not configured."
        print(error_message, flush=True)
        return {"status": "error", "message": error_message}
    
    if not auth_token:
        error_message = "Error: API authentication token is not available."
        print(error_message, flush=True)
        return {"status": "error", "message": error_message}

    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Accept": "application/json", 
    }
    if action in ["post", "put"]:
        headers["Content-Type"] = "application/json"

    full_url = f"{base_url}{processed_path}"
    response_data: Optional[Any] = None
    
    print(f"Attempting API call (from api_tools.py):", flush=True)
    print(f"  Action: {action.upper()}", flush=True)
    print(f"  URL: {full_url}", flush=True)
    if value:
        print(f"  Payload: {json.dumps(value)}", flush=True)

    try:
        http_response: Optional[requests.Response] = None
        if action == "get":
            http_response = requests.get(full_url, headers=headers)
        elif action == "post":
            http_response = requests.post(full_url, json=value, headers=headers)
        elif action == "put":
            http_response = requests.put(full_url, json=value, headers=headers)
        elif action == "delete":
            http_response = requests.delete(full_url, headers=headers)
        else:
            error_message = f"Error: Unsupported action '{action}'."
            print(error_message, flush=True)
            return {"status": "error", "message": error_message}

        http_response.raise_for_status()
        
        if http_response.content:
            try:
                response_data = http_response.json()
            except json.JSONDecodeError:
                response_data = http_response.text 
        else:
            response_data = None

        return {"status": http_response.status_code, "data": response_data}

    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP error occurred: {e} - {e.response.status_code} - {e.response.text}"
        print(error_message, flush=True)
        return {"status": "error", "http_status_code": e.response.status_code, "message": error_message, "details": e.response.text}
    except requests.exceptions.RequestException as e:
        error_message = f"Request failed: {e}"
        print(error_message, flush=True)
        return {"status": "error", "message": error_message}
    except Exception as e: 
        error_message = f"An unexpected error occurred during API call: {e}"
        print(error_message, flush=True)
        return {"status": "error", "message": error_message}

if __name__ == '__main__':
    # This __main__ block is for testing api_tools.py directly.
    # It needs to ensure that the config_manager (via server.py's helpers) is initialized.
    print("--- Testing connexa_openvpn_mcp_server/api_tools.py ---", flush=True)
    
    # To make this runnable standalone, we need to ensure the project root is in sys.path
    # so that 'from .server import ...' can resolve '.server' correctly relative to this package.
    # This usually happens if you run 'python -m connexa_openvpn_mcp_server.api_tools'
    # from the project root directory.
    
    # For direct execution 'python connexa_openvpn_mcp_server/api_tools.py',
    # sys.path might need adjustment or rely on PYTHONPATH.
    # The import 'from .server ...' implies this file is part of a package.

    # The following initialization simulation is tricky because of relative imports.
    # It's best to test this module by running the main server.py or through MCP calls.
    # However, for a quick check:
    print("Note: Standalone test of api_tools.py relies on server.py for config.", flush=True)
    print("Ensure server.py can initialize config_manager correctly.", flush=True)

    print("\n--- Testing schema tool (from api_tools.py) ---", flush=True)
    user_api_info = schema("User")
    if user_api_info:
        print("User APIs:", flush=True)
        for api_entry in user_api_info:
            print(f"  Path: {api_entry['api']}, Actions: {api_entry['actions']}, Hint: {api_entry.get('hint', 'N/A')}", flush=True)
    else:
        print("User group not found or api.json is missing/invalid.", flush=True)

    print("\n--- Testing call_api tool (from api_tools.py, will attempt live calls) ---", flush=True)
    # Test GET for users (expected to be empty if no users)
    # print("Test GET /api/v1/users:", flush=True)
    # print(json.dumps(call_api(action="get", path="/api/v1/users"), indent=2), flush=True)
    
    # Test GET for a specific user (will likely fail with 404 if ID is bogus and no users)
    # print("\nTest GET /api/v1/users/{id} (expect 404 or error if ID invalid):", flush=True)
    # print(json.dumps(call_api(action="get", path="/api/v1/users/{id}", id="nonexistent-id"), indent=2), flush=True)

    print("\nTest call_api with path expecting {id} but no id provided (error case):", flush=True)
    print(json.dumps(call_api(action="get", path="/api/v1/users/{id}"), indent=2), flush=True)

    print("\nTest call_api with POST action without value (error case):", flush=True)
    print(json.dumps(call_api(action="post", path="/api/v1/users"), indent=2), flush=True)
    
    print("\n--- End of api_tools.py tests ---", flush=True)
