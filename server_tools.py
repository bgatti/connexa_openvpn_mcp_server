# aws/server_tools.py
from typing import Any, Dict, List, Tuple, Optional
from connexa.connexa_api import call_api # Updated to use connexa_api module

# Attempt to import from aws_tools.py; these are expected to be implemented there.
# If aws_tools.py is not yet complete, these will act as placeholders.
from aws import aws_tools
upsert_regional_egress = aws_tools.upsert_regional_egress
# Add delete_regional_egress_by_prefix
delete_regional_egress_by_prefix = aws_tools.delete_regional_egress_by_prefix
get_aws_regions = aws_tools.get_aws_regions
validate_aws_credentials = aws_tools.validate_aws_credentials
print("Successfully imported functions from aws.aws_tools.")

def _get_connector_profile_and_id(connector_id: str, ovpn_region_id: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetches the connector's OpenVPN profile content and its resolved ID (GUID).
    It uses the provided connector ID and OpenVPN region ID to fetch the profile via API.
    
    Args:
        connector_id (str): The ID (GUID) of the connector.
        ovpn_region_id (str): The OpenVPN region ID for which the profile should be generated.

    Returns:
        A tuple (profile_content, resolved_connector_id).
        Returns (None, None) if the profile cannot be fetched.
    """
    profile_content: Optional[str] = None
    
    print(f"Attempting to fetch OpenVPN profile for connector ID: {connector_id} for region: {ovpn_region_id} via API.")
    
    try:
        # The API for network connector profile is POST /api/v1/networks/connectors/{id}/profile
        # It requires the regionId as a query parameter.
        api_response_profile = call_api(
            action="post",
            path=f"/api/v1/networks/connectors/{connector_id}/profile?regionId={ovpn_region_id}",
            value={} # Assuming empty payload is sufficient
        )
        
        # Check if the profile call was successful and data is present
        if api_response_profile and isinstance(api_response_profile.get("status"), int) and 200 <= api_response_profile["status"] < 300 and api_response_profile.get("data"):
            profile_content = api_response_profile["data"]
            if isinstance(profile_content, dict): # If API returns JSON instead of raw profile string
                print(f"Warning: API for profile returned JSON, not raw string. Data: {profile_content}")
                profile_content = None # Or try to extract from dict if structure is known
            else:
                print(f"Successfully fetched OpenVPN profile for connector ID {connector_id}.")
        else:
            print(f"Warning: Failed to fetch OpenVPN profile for connector ID {connector_id}. API response: {api_response_profile}")
            profile_content = None
            print(f"Error: Failed to fetch OpenVPN profile for connector ID {connector_id}. API response: {api_response_profile}")
            return None, None # Stop if profile fetch fails
            
    except Exception as e:
        print(f"Error: Exception while trying to fetch profile for connector ID '{connector_id}': {e}.")
        return None, None # Stop if any exception occurs
        
    if not profile_content:
        print(f"Error: Profile content is unexpectedly None for connector ID {connector_id}.")
        return None, None
        
    # The resolved_connector_id for prefixing AWS resources should be derived from the connector ID
    resolved_connector_id_for_prefix = f"connprefix-{connector_id.replace(' ', '_').lower()}"
    
    return profile_content, resolved_connector_id_for_prefix


# --- Resource: Available AWS Server Regions ---
def get_available_aws_regions_resource() -> List[Dict[str, str]]:
    """
    Resource provider for available AWS server regions.
    This function is intended to be called by the MCP server to expose AWS regions.
    It delegates to a function expected to be in `aws_tools.py`.
    """
    if not validate_aws_credentials():
        return [{"id": "error", "name": "AWS credential validation failed."}]
    try:
        # get_aws_regions returns a list of region strings, e.g., ['us-east-1', 'us-west-2']
        # We should fetch opted-in regions for practical use.
        region_codes = get_aws_regions(only_opted_in_regions=True)
        
        # Transform into the list of dicts format expected by some MCP contexts if needed,
        # or adjust MCP server to handle list of strings.
        # For now, transforming to: [{"id": "code", "name": "code (AWS Region)"}]
        # A more sophisticated approach might map codes to friendly names if available.
        formatted_regions = []
        for code in region_codes:
            formatted_regions.append({"id": code, "name": f"{code} (AWS Region)"})
        
        if not formatted_regions and region_codes: # Transformation failed but codes exist
             print(f"Warning: get_aws_regions returned codes, but formatting failed. Codes: {region_codes}")
             return [{"id": "error", "name": "Failed to format AWS regions from codes."}]
        elif not region_codes:
            print("No AWS regions returned by get_aws_regions.")
            return [{"id": "empty", "name": "No AWS regions found."}]
            
        return formatted_regions
    except Exception as e:
        print(f"Error calling get_aws_regions from aws_tools: {str(e)}")
        # Fallback or error representation if the call fails
        return [{"id": "error", "name": f"Failed to fetch/process AWS regions: {str(e)}"}]


# --- Tool: Provision Connector ---
def Provision_Connector_tool(
    connector_id: str, # Changed parameter name and type hint
    aws_region_id: str
) -> Dict[str, Any]:
    """
    Tool to provision an AWS instance to act as a connector, configured with an OpenVPN profile
    derived from the given OpenVPN Connexa connector ID.

    This tool is intended to be exposed by the MCP server.

    Args:
        connector_id (str): The ID (GUID) of the OpenVPN Connexa connector. The profile for this
                            connector will be used to configure the AWS instance.
        aws_region_id (str): The AWS region ID (e.g., "us-east-1") where the EC2 instance
                             should be launched to act as the connector.

    Returns:
        Dict[str, Any]: An object containing:
                        - "details": Information about the created AWS resources (e.g., instance ID, IP).
                        - "notes": Any relevant notes about the operation.
                        - "status": The status of the operation (e.g., "success_aws_provision", "error_profile_generation", "error_aws_launch").
    """
    print(f"Tool: Provision_Connector_tool called with connector_id='{connector_id}', aws_region_id='{aws_region_id}'")

    if not validate_aws_credentials():
        return {
            "details": {},
            "notes": "AWS credential validation failed before attempting provision.",
            "status": "error_aws_credentials"
        }

    # Step 1: Get the OpenVPN profile content and a resolved ID for the OpenVPN Connexa connector.
    # The resolved ID will be used as a prefix for AWS resource naming.
    # Pass the connector_id and a hardcoded ovpn_region_id for profile generation
    profile_content, resolved_connector_id_for_prefix = _get_connector_profile_and_id(connector_id, "us-west-1") # Hardcoded OVPN region for now

    if profile_content:
        profile_length_kb = len(profile_content.encode('utf-8')) / 1024
        print(f"Debug: In server_tools.py, after _get_connector_profile_and_id, profile_content length: {profile_length_kb:.2f} KB, first 20 chars: '{profile_content[:20]}'")
    else:
        print("Debug: In server_tools.py, after _get_connector_profile_and_id, profile_content is None or empty.")
    
    if not profile_content or not resolved_connector_id_for_prefix:
        error_msg = (f"Failed to download/generate OpenVPN profile for connector ID: {connector_id}. "
                       "This could be due to issues resolving the connector or missing parameters "
                       "(like specific OpenVPN User ID or OpenVPN Profile Region ID) required for profile generation. "
                       "Check placeholder logic in _get_connector_profile_and_id.")
        print(error_msg)
        return {
            "details": {},
            "notes": error_msg,
            "status": "error_profile_generation"
        }
    
    print(f"Successfully retrieved/generated OpenVPN profile for connector ID '{connector_id}' and resolved connector ID to '{resolved_connector_id_for_prefix}'.")

    # Step 2: Call the upsert_regional_egress function in aws_tools.py.
    try:
        # Parameters for upsert_regional_egress:
        # prefix (str): resolved_connector_id_for_prefix
        # public (bool): True (as we are setting up an OpenVPN egress point)
        # region_id (Optional[str]): aws_region_id
        # openvpn_profile_content (Optional[str]): profile_content
        
        if profile_content:
            profile_length_kb = len(profile_content.encode('utf-8')) / 1024
            print(f"Debug: In server_tools.py, before calling upsert_regional_egress, profile_content length: {profile_length_kb:.2f} KB, first 20 chars: '{profile_content[:20]}'")
        else:
            print("Debug: In server_tools.py, before calling upsert_regional_egress, profile_content is None or empty.")
        
        print(f"Calling upsert_regional_egress with prefix='{resolved_connector_id_for_prefix}', public=True, region_id='{aws_region_id}', OVPN profile provided.")
        
        egress_result = upsert_regional_egress(
            prefix=resolved_connector_id_for_prefix,
            public=True,
            region_id=aws_region_id,
            openvpn_profile_content=profile_content
        )

        # Check for PROVISIONING_STARTED status first
        if egress_result and egress_result.get("instance_status") == "PROVISIONING_STARTED":
            instance_details = {
                "instance_id": egress_result.get("ovpn_instance_id"),
                "public_ip": None, # IP not yet available
                "vpc_id": egress_result.get("vpc_id"),
                "subnet_id": egress_result.get("ovpn_instance_subnet_id"),
                "security_group_id": egress_result.get("ovpn_instance_security_group_id"),
                "security_group_name": egress_result.get("ovpn_instance_security_group_name"),
                "region": egress_result.get("region"),
                "instance_status": "PROVISIONING_STARTED",
                "raw_egress_details": egress_result
            }
            notes = egress_result.get("notes", ["AWS instance provisioning started."])
            if isinstance(notes, list):
                notes_str = "; ".join(notes)
            else:
                notes_str = str(notes)
            
            return {
                "details": instance_details,
                "notes": notes_str,
                "status": "success_aws_provision_started" # New status
            }
        elif egress_result and egress_result.get("ovpn_instance_id"): # Existing logic for fully provisioned or found instance
            # Successfully created/found an OpenVPN instance
            instance_details = {
                "instance_id": egress_result.get("ovpn_instance_id"),
                "public_ip": egress_result.get("public_ip"),
                "vpc_id": egress_result.get("vpc_id"),
                "subnet_id": egress_result.get("ovpn_instance_subnet_id"),
                "security_group_id": egress_result.get("ovpn_instance_security_group_id"),
                "security_group_name": egress_result.get("ovpn_instance_security_group_name"),
                "region": egress_result.get("region"),
                "raw_egress_details": egress_result # Include all details from aws_tools
            }
            notes = egress_result.get("notes", ["OpenVPN egress operation successful."])
            if isinstance(notes, list):
                notes_str = "; ".join(notes)
            else:
                notes_str = str(notes)

            return {
                "details": instance_details,
                "notes": notes_str,
                "status": "success_aws_provision" # Changed status
            }
        elif egress_result:
            # upsert_regional_egress returned something, but maybe not an OVPN instance or it failed partially
            error_notes = egress_result.get("notes", ["AWS provision operation completed but OpenVPN instance details not found or incomplete."])
            if isinstance(error_notes, list):
                error_notes_str = "; ".join(error_notes)
            else:
                error_notes_str = str(error_notes)
            
            print(f"Warning: upsert_regional_egress completed but OVPN instance details might be missing. Result: {egress_result}")
            return {
                "details": egress_result, # Return all details from aws_tools
                "notes": error_notes_str,
                "status": "warning_aws_provision_incomplete" # Changed status
            }
        else:
            # upsert_regional_egress returned None, indicating a failure
            error_msg = f"Failed to upsert regional egress for connector ID {connector_id} in region {aws_region_id}. upsert_regional_egress returned None."
            print(error_msg)
            return {
                "details": {},
                "notes": error_msg,
                "status": "error_aws_provision_returned_none" # Changed status
            }

    except Exception as e:
        error_msg = f"Exception during AWS instance provision (calling upsert_regional_egress): {str(e)}" # Changed launch to provision
        print(error_msg)
        return {
            "details": {},
            "notes": error_msg,
            "status": "error_aws_provision_exception" # Changed status
        }

# --- Tool: DeProvision Connector ---
def DeProvision_Connector_tool( # Renamed from release_aws_instance_tool
    connector: str,
    aws_region_id: str
) -> Dict[str, Any]:
    """
    Tool to deprovision/delete an AWS instance and related resources associated with a connector prefix.

    Args:
        connector (str): The name or ID of the OpenVPN Connexa connector used to derive the prefix
                         for AWS resources.
        aws_region_id (str): The AWS region ID (e.g., "us-east-1") where the resources exist.

    Returns:
        Dict[str, Any]: An object containing:
                        - "details": Information about the deleted AWS resources.
                        - "notes": Any relevant notes about the operation.
                        - "status": The status of the operation (e.g., "success_aws_deprovision", "error_aws_credentials", "error_aws_deprovision_exception").
    """
    print(f"Tool: DeProvision_Connector_tool called with connector='{connector}', aws_region_id='{aws_region_id}'")

    if not validate_aws_credentials():
        return {
            "details": {},
            "notes": "AWS credential validation failed before attempting deprovision.", # Changed release to deprovision
            "status": "error_aws_credentials"
        }

    # Derive the prefix from the connector name, consistent with how it's created in Provision_Connector_tool
    # via _get_connector_profile_and_id which sets resolved_connector_id = f"connprefix-{connector_identifier.replace(' ', '_').lower()}"
    resolved_prefix = f"connprefix-{connector.replace(' ', '_').lower()}"
    print(f"Derived prefix for deprovisioning: '{resolved_prefix}' from connector '{connector}'.") # Changed deletion to deprovisioning

    try:
        print(f"Calling delete_regional_egress_by_prefix with prefix='{resolved_prefix}', region_id='{aws_region_id}', instance_id=None.")

        deprovision_result = delete_regional_egress_by_prefix( # Changed release_result to deprovision_result
            instance_id=None, # Explicitly pass None for instance_id
            prefix=resolved_prefix,
            region_id=aws_region_id
        )

        if deprovision_result and deprovision_result.get("status") in ["success", "simulated_success"]: # aws_tools might return "success"
            notes = deprovision_result.get("notes", ["AWS resources deprovisioned successfully."]) # Changed released to deprovisioned
            if isinstance(notes, list):
                notes_str = "; ".join(notes)
            else:
                notes_str = str(notes)

            return {
                "details": deprovision_result.get("details", {}),
                "notes": notes_str,
                "status": "success_aws_deprovision" # Changed status
            }
        elif deprovision_result:
            error_notes = deprovision_result.get("notes", ["AWS deprovision operation completed with unexpected status or incomplete results."]) # Changed release to deprovision
            if isinstance(error_notes, list):
                error_notes_str = "; ".join(error_notes)
            else:
                error_notes_str = str(error_notes)

            print(f"Warning: delete_regional_egress_by_prefix completed with status: {deprovision_result.get('status')}. Result: {deprovision_result}")
            return {
                "details": deprovision_result.get("details", {}),
                "notes": error_notes_str,
                "status": f"warning_aws_deprovision_{deprovision_result.get('status', 'unknown')}" # Changed status
            }
        else:
            # delete_regional_egress_by_prefix returned None or an unhandled result
            error_msg = f"Failed to deprovision regional egress for prefix {resolved_prefix} in region {aws_region_id}. delete_regional_egress_by_prefix returned None or invalid." # Changed release to deprovision
            print(error_msg)
            return {
                "details": {},
                "notes": error_msg,
                "status": "error_aws_deprovision_returned_none" # Changed status
            }

    except Exception as e:
        error_msg = f"Exception during AWS instance deprovision (calling delete_regional_egress_by_prefix): {str(e)}" # Changed release to deprovision
        print(error_msg)
        return {
            "details": {},
            "notes": error_msg,
            "status": "error_aws_deprovision_exception" # Changed status
        }

if __name__ == "__main__":
    print("--- Testing aws.server_tools: Provision and DeProvision Connector ---")

    test_connector_name = "dc1d9805-5a4e-4320-b260-423866d17ed5"
    test_aws_region = "us-west-1"

    # --- Test Provision Connector ---
    print(f"\nAttempting to provision AWS instance for connector '{test_connector_name}' in region '{test_aws_region}'.")
    print(f"This involves: 1. Finding connector & getting profile. 2. Provisioning EC2 instance.")

    # Use a hardcoded connector ID for testing since the tool now expects it
    test_connector_id = "4b6852d3-ae4a-4c9b-b6c8-6fac228b832a" # Example ID, replace with a valid one if needed

    provision_result = Provision_Connector_tool(
        connector_id=test_connector_id, # Changed parameter name
        aws_region_id=test_aws_region
    )

    print("\n--- Provision Test Result ---")
    provision_status = provision_result.get("status", "unknown_status")
    provision_notes = provision_result.get("notes", "No notes provided.")
    provision_details = provision_result.get("details", {})

    if provision_status == "success_aws_provision":
        print(f"SUCCESS: AWS instance provisioned successfully for connector ID '{test_connector_id}'.") # Updated message
        print(f"  Status: {provision_status}")
        print(f"  Instance ID: {provision_details.get('instance_id', 'N/A')}")
        print(f"  Public IP: {provision_details.get('public_ip', 'N/A')}")
        print(f"  Notes: {provision_notes}")
    elif provision_status == "error_profile_generation":
        print(f"FAILURE: Could not get/generate OpenVPN profile for connector ID '{test_connector_id}'.") # Updated message
        print(f"  Status: {provision_status}")
        print(f"  Notes: {provision_notes}")
    elif provision_status == "error_aws_credentials":
        print(f"FAILURE: AWS credential validation failed.")
        print(f"  Status: {provision_status}")
        print(f"  Notes: {provision_notes}")
    elif "error_aws_provision" in provision_status or provision_status == "warning_aws_provision_incomplete":
        print(f"FAILURE/WARNING: Problem during AWS instance provision for connector ID '{test_connector_id}'.") # Updated message
        print(f"  Status: {provision_status}")
        print(f"  Notes: {provision_notes}")
        if provision_details:
             print(f"  Details: {provision_details}")
    else:
        print(f"FAILURE: Unknown outcome for AWS instance provision for connector ID '{test_connector_id}'.") # Updated message
        print(f"  Status: {provision_status}")
        print(f"  Notes: {provision_notes}")
        if provision_details:
             print(f"  Details: {provision_details}")

    print(f"\nRaw Provision Result: {provision_result}")

    # --- Test DeProvision Connector (only if provision was successful) ---
    if provision_status == "success_aws_provision":
        print(f"\n--- Test DeProvision Connector ---")
        # The DeProvision tool still takes connector name/ID to derive prefix.
        # Using the original test_connector_name here for consistency with prefix derivation.
        print(f"\nSUCCESS: AWS instance provisioned. Now attempting to deprovision instance for connector '{test_connector_name}' in region '{test_aws_region}'.")
        
        deprovision_result = DeProvision_Connector_tool(
            connector=test_connector_name,
            aws_region_id=test_aws_region
        )
        
        print(f"\n--- DeProvision Test Result ---")
        deprovision_status = deprovision_result.get("status", "unknown_status")
        deprovision_notes = deprovision_result.get("notes", "No notes provided.")
        deprovision_details = deprovision_result.get("details", {})
        
        print(f"DeProvision Result: {deprovision_result}")
        
        if deprovision_status == "success_aws_deprovision":
            print(f"SUCCESS: AWS instance deprovisioned successfully for connector '{test_connector_name}'.")
        else:
            print(f"FAILURE/WARNING: Problem during AWS instance deprovision for connector '{test_connector_name}'.")
        print(f"  Status: {deprovision_status}")
        print(f"  Notes: {deprovision_notes}")
        if deprovision_details:
            print(f"  Details: {deprovision_details}")
    else:
        print(f"\nSKIPPING DEPROVISION TEST: Provision was not successful. Status: {provision_status}")

    print("\n--- Testing Complete ---")
    print("To run this module directly from the project root (connexa_openvpn_mcp_server), use:")
    print("python -m connexa_openvpn_mcp_server.server_tools") # Corrected module path
