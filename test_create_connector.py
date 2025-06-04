import requests
import os
import sys

# Add the parent directory to the sys.path to be able to import connexa
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from connexa.connexa_api import call_api
from connexa.config_manager import initialize_config # Import initialize_config

# Initialize the config manager (needed for call_api to get credentials)
# Assuming config is in .env in the parent directory
initialize_config()

# Parameters for getting a list of networks
print("Attempting to get a list of networks")

# Call the call_api function to get networks
result = call_api(
    action="get",
    path="/api/v1/networks"
)

print("\nResult of call_api (get networks):")
print(result)

# Check the status of the result
if result.get("status") == 200:
    print("\nSuccessfully retrieved list of networks via call_api.")
    # You can access the list of networks from result.get("data")
    # print(f"Networks: {result.get('data')}")
elif result.get("status") == "error":
    print("\nError retrieving list of networks via call_api.")
    print(f"Error message: {result.get('message')}")
    if result.get("http_status_code"):
        print(f"HTTP Status Code: {result.get('http_status_code')}")
    if result.get("details"):
        print(f"Details: {result.get('details')}")
else:
    print("\nUnexpected result status from call_api (get networks).")
    print(f"Result: {result}")
