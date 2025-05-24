import sys
import os
import requests

# --- Configuration Variables ---
# These are hard-coded for now, but ideally loaded from environment or a secure store.
BUSINESS_NAME = "mcptest"
CLIENT_ID = "UMQdi1gZ7SdArMH9PC8c8ltqWkYapWCo.mcptest"
CLIENT_SECRET = "wllXiCBfcO1fKDDYRhIWABp5TbCrEFO4Ux0sJcgGZxlPk591XSJ6YtZqq3BVnbmw"
API_TOKEN = None # Will be fetched dynamically

# --- Helper Functions ---

def refresh_api_token():
    """
    Fetches a new API token from the OpenVPN OAuth endpoint.
    Updates the global API_TOKEN variable.
    Returns True if successful, False otherwise.
    """
    global API_TOKEN # Allow modification of the global variable

    token_url = f"https://{BUSINESS_NAME}.api.openvpn.com/api/v1/oauth/token"
    params = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    headers = {
        "accept": "*/*"
    }
    
    print(f"Attempting to refresh API token from {token_url}", file=sys.stderr)
    try:
        response = requests.post(token_url, params=params, headers=headers, data='')
        response.raise_for_status()
        token_data = response.json()
        new_token = token_data.get("access_token")
        if new_token:
            API_TOKEN = new_token # Update the global API_TOKEN
            print(f"Successfully refreshed API token. New token: {API_TOKEN[:10]}...", file=sys.stderr)
            # Optionally, you could store and log expires_in here
            # print(f"Token expires in: {token_data.get('expires_in')} seconds", file=sys.stderr)
            return True
        else:
            print("ERROR: 'access_token' not found in token response.", file=sys.stderr)
            print(f"Token response data: {token_data}", file=sys.stderr)
            return False
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to refresh API token: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}", file=sys.stderr)
            print(f"Response text: {e.response.text}", file=sys.stderr)
        return False

def get_api_token():
    """
    Returns the current API token.
    If the token is not set, it attempts to refresh it.
    """
    if API_TOKEN is None:
        print("API_TOKEN is None, attempting to refresh...", file=sys.stderr)
        if not refresh_api_token():
            print("Failed to refresh token in get_api_token.", file=sys.stderr)
            return None # Or raise an exception
    return API_TOKEN

def initialize_config():
    """
    Initializes the configuration, including fetching the API token.
    This should be called once at the start of any server using this config.
    Returns True if successful, False otherwise.
    """
    print("Initializing configuration...", file=sys.stderr)
    # Debug information about Python environment
    print(f"Python version: {sys.version}", file=sys.stderr)
    print(f"Python executable: {sys.executable}", file=sys.stderr)
    
    # Debug information about current directory
    current_dir = os.getcwd()
    print(f"ConfigManager - Current working directory: {current_dir}", file=sys.stderr)
        
    print(f"BUSINESS_NAME: {BUSINESS_NAME}", file=sys.stderr)
    print(f"CLIENT_ID: {CLIENT_ID}", file=sys.stderr)
    # Do not print CLIENT_SECRET in logs for security reasons.
    
    if not refresh_api_token():
        print("ERROR: Failed to obtain API token during configuration initialization.", file=sys.stderr)
        return False
    
    print("Configuration initialized successfully.", file=sys.stderr)
    return True

if __name__ == "__main__":
    # Example of how to initialize and use the config
    if initialize_config():
        token = get_api_token()
        if token:
            print(f"Successfully obtained token: {token[:20]}...")
        else:
            print("Failed to obtain token after initialization.")
    else:
        print("Failed to initialize configuration.")
