import os
import sys

# Add the parent directory to the sys.path to be able to import connexa and aws
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))) # Current dir for aws
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # Parent for connexa

from server_tools import Provision_Connector_tool
from connexa.config_manager import initialize_config

# Initialize the config manager (needed for API calls within provisioning)
initialize_config()

# Parameters for provisioning the connector
connector_id = "26669cdd-d3c9-4370-8dc6-4758e339f3dd" # ID provided by user for testing
aws_region = "us-west-1"

print(f"Attempting to provision connector instance for connector ID: {connector_id} in AWS region: {aws_region}")

# Call the Provision_Connector_tool function
result = Provision_Connector_tool(
    connector=connector_id,
    aws_region_id=aws_region
)

print("\nResult of Provision_Connector_tool:")
print(result)

# Check the status of the result
status = result.get("status", "unknown_status")
notes = result.get("notes", "No notes provided.")
details = result.get("details", {})

if status == "success_aws_provision":
    print("\nConnector instance provisioned successfully.")
    print(f"  Instance ID: {details.get('instance_id', 'N/A')}")
    print(f"  Public IP: {details.get('public_ip', 'N/A')}")
    print(f"  Notes: {notes}")
elif "error" in status:
    print("\nError during connector instance provisioning.")
    print(f"  Status: {status}")
    print(f"  Notes: {notes}")
    if details:
        print(f"  Details: {details}")
else:
    print("\nUnexpected result status from Provision_Connector_tool.")
    print(f"  Status: {status}")
    print(f"  Notes: {notes}")
    if details:
        print(f"  Details: {details}")
