import json
from mcp.server.fastmcp.server import Tool, Context
from mcp.types import TextContent
from connexa_openvpn_mcp_server.connexa.selected_object import SelectedObject, CURRENT_SELECTED_OBJECT
from typing import Dict, Any, Optional, Sequence, Union
from connexa_openvpn_mcp_server.aws.aws_tools import initiate_delete_regional_egress_resources, refresh_aws_credentials_and_region
import boto3
from connexa_openvpn_mcp_server.connexa.connexa_api import call_api

async def delete_selected_object(ctx: Context) -> Dict[str, Any]:
    """
    Deletes the currently selected object.
    If the selected object is a connector, it will first deprovision the associated AWS instance.
    """
    log_messages = [] # Initialize log messages list
    try:
        # Access the currently selected object details from the global CURRENT_SELECTED_OBJECT instance
        selected_object_details = CURRENT_SELECTED_OBJECT.get_selected_object_info()

        # Add logging to inspect the retrieved details
        log_messages.append(f"Debug: In delete_selected_object, retrieved selected_object_details: {selected_object_details}")
        await ctx.info(log_messages[-1]) # Also send to ctx.info for immediate visibility

        # Check if an object is actually selected (i.e., if it has an ID)
        if not selected_object_details.get("id"): # If 'id' is None or empty, nothing is selected
            log_messages.append("No object is currently selected (based on CURRENT_SELECTED_OBJECT.get_selected_object_info()).")
            await ctx.info(log_messages[-1])
            return {"status": "error", "message": "No object currently selected.", "log": log_messages}

        # Add logging after the initial check
        log_messages.append("Debug: Initial selected object check passed. Proceeding with deletion logic.")
        await ctx.info(log_messages[-1])

        log_messages.append(f"Successfully retrieved selected object details from CURRENT_SELECTED_OBJECT: {selected_object_details}")
        await ctx.info(log_messages[-1])

        # Directly access attributes from the global CURRENT_SELECTED_OBJECT instance
        object_type = CURRENT_SELECTED_OBJECT.object_type
        object_id = CURRENT_SELECTED_OBJECT.object_id
        object_name = CURRENT_SELECTED_OBJECT.object_name
        # Access region ID, checking for both 'aws_region_id' and 'vpnRegionId' from the global instance's details
        aws_region_id = CURRENT_SELECTED_OBJECT.details.get("aws_region_id") or CURRENT_SELECTED_OBJECT.details.get("vpnRegionId")
        # Attempt to get instance_id and instance_base_name from details if available
        instance_id = CURRENT_SELECTED_OBJECT.details.get("instance_id")
        instance_base_name = CURRENT_SELECTED_OBJECT.details.get("instance_base_name")


        if not object_id:
            # If object_id is None after calling select, it means the resource data was missing the 'id'
            log_messages.append(f"Selected object data from resource is missing 'id': {selected_object_details}")
            await ctx.error(log_messages[-1])
            return {"status": "error", "message": f"Selected object data from resource is missing ID.", "log": log_messages}

        delete_status = {"status": "success", "message": f"Successfully deleted {object_type} '{object_name}' (ID: {object_id})."}

        if object_type == "connector":
            # Fallback logic to find instance_id if not in details
            if not instance_id and object_name and aws_region_id:
                log_messages.append(f"Instance ID not found in details for connector '{object_name}'. Attempting to find by Name tag '{object_name}' in region '{aws_region_id}'.")
                await ctx.info(log_messages[-1])
                try:
                    refresh_aws_credentials_and_region(aws_region_id) # Sets environment variables for boto3
                    ec2_search_client = boto3.client('ec2', region_name=aws_region_id)

                    instance_name_tag_to_search = object_name # Instance Name tag is the connector name

                    search_response = ec2_search_client.describe_instances(
                        Filters=[
                            {'Name': 'tag:Name', 'Values': [instance_name_tag_to_search]},
                            {'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped']}
                        ]
                    )

                    found_instances = []
                    for reservation in search_response.get('Reservations', []):
                        for inst in reservation.get('Instances', []):
                            found_instances.append(inst)

                    if len(found_instances) == 1:
                        instance_id = found_instances[0]['InstanceId']
                        log_messages.append(f"Found matching instance by Name tag '{instance_name_tag_to_search}': {instance_id}")
                        await ctx.info(log_messages[-1])
                        # Optionally update selected_object.details if needed elsewhere, for now, local instance_id is enough.
                        # selected_object.details["instance_id"] = instance_id
                    elif len(found_instances) > 1:
                        ids_found = [i['InstanceId'] for i in found_instances]
                        log_messages.append(f"Found multiple ({len(found_instances)}) instances with Name tag '{instance_name_tag_to_search}' in region '{aws_region_id}'. Cannot determine correct instance. IDs: {ids_found}")
                        await ctx.warning(log_messages[-1])
                    else:
                        log_messages.append(f"No instances found with Name tag '{instance_name_tag_to_search}' in region '{aws_region_id}'.")
                        await ctx.info(log_messages[-1])

                except Exception as find_ex:
                    log_messages.append(f"Error occurred while trying to find instance by Name tag '{object_name}' in region '{aws_region_id}': {find_ex}")
                    await ctx.error(log_messages[-1])

            # Attempt AWS deprovisioning if instance_id is available.
            # If instance_id is not found, we will proceed to delete the connector from Connexa.
            deprovision_status = "skipped" # Default status if no instance_id
            deprovision_message = "AWS deprovisioning skipped: No AWS instance ID recorded or found."
            deprovision_notes = ["No AWS instance ID recorded or found."]

            if instance_id:
                if not aws_region_id:
                     log_messages.append(f"Selected connector '{object_name}' has no associated AWS region ID (checked for 'aws_region_id' and 'vpnRegionId') for deprovisioning. Details: {CURRENT_SELECTED_OBJECT.details}")
                     await ctx.error(log_messages[-1])
                     return {"status": "error", "message": f"Selected connector '{object_name}' has no associated AWS region ID for deprovisioning.", "log": log_messages}

                log_messages.append(f"Deprovisioning AWS instance '{instance_id}' for connector '{object_name}' in region '{aws_region_id}'...")
                await ctx.info(log_messages[-1])
                # Call the internal AWS deprovisioning function directly
                deprovision_result = initiate_delete_regional_egress_resources(
                    instance_id=instance_id, # Pass instance_id if available
                    aws_object_name=object_name, # Use connector name as aws_object_name
                    region_id=aws_region_id, # Pass the retrieved region ID
                    vpc_id=CURRENT_SELECTED_OBJECT.details.get("vpc_id"), # Pass the VPC ID from selected object details
                    instance_base_name=instance_base_name # Pass instance_base_name if available
                    # subnet_id_to_delete and other args might be needed depending on how resources were tagged/created
                    # For now, rely on instance_id, aws_object_name, region_id, and vpc_id
                )

                deprovision_status = deprovision_result.get("status", "unknown")
                deprovision_notes = deprovision_result.get("notes", ["No details provided"])
                # Original deprovision_message for internal logic
                original_deprovision_message_for_check = f"AWS deprovisioning status: {deprovision_status}. Notes: {', '.join(deprovision_notes)}"
                
                # User-facing deprovision_message, to be updated based on status
                deprovision_message = original_deprovision_message_for_check 
                log_messages.append(f"AWS deprovisioning result: {deprovision_result}")
                await ctx.info(log_messages[-1])

                is_instance_not_found_error = "instanceid" in original_deprovision_message_for_check.lower() and \
                                              ("not found" in original_deprovision_message_for_check.lower() or \
                                               "does not exist" in original_deprovision_message_for_check.lower())

                proceed_with_connexa_delete = False
                if deprovision_status == "deletion_initiated":
                    log_messages.append(f"AWS deprovisioning initiated for connector '{object_name}'. Proceeding with Connexa deletion.")
                    await ctx.info(log_messages[-1])
                    deprovision_message = f"AWS deprovisioning initiated. Notes: {', '.join(deprovision_notes)}" # Update user-facing message
                    proceed_with_connexa_delete = True
                elif deprovision_status == "success": # Handles cases where deprovisioning might complete quickly or was skipped appropriately
                    log_messages.append(f"AWS deprovisioning reported as successful for connector '{object_name}'. Proceeding with Connexa deletion.")
                    await ctx.info(log_messages[-1])
                    # deprovision_message already reflects success
                    proceed_with_connexa_delete = True
                elif is_instance_not_found_error:
                    log_messages.append(f"AWS instance deprovisioning skipped because instance was not found. Proceeding to delete connector from Connexa. Details: {original_deprovision_message_for_check}")
                    await ctx.warning(log_messages[-1])
                    deprovision_status = "instance_not_found" # Keep this specific status for clarity
                    deprovision_message = f"AWS deprovisioning skipped (instance not found). Original message: {original_deprovision_message_for_check}"
                    proceed_with_connexa_delete = True
                
                if not proceed_with_connexa_delete:
                    # This means deprovision_status was an actual error (e.g., "failure", "unknown")
                    log_messages.append(f"Failed to deprovision AWS instance for connector '{object_name}': {original_deprovision_message_for_check}")
                    await ctx.error(log_messages[-1])
                    return {"status": "error", "message": f"Failed to deprovision AWS instance for connector '{object_name}': {original_deprovision_message_for_check}", "log": log_messages}

            # Proceed with deleting the connector from Connexa using call_api directly
            log_messages.append(f"Proceeding to delete connector '{object_name}' (ID: {object_id}) from Connexa...")
            await ctx.info(log_messages[-1])

            # Construct the API path using the connector ID.
            # Based on user feedback and swagger, the path /api/v1/networks/connectors/{id} is used.
            connexa_api_path = f"/api/v1/networks/connectors/{object_id}"

            log_messages.append(f"Calling call_api directly with action 'delete' and path: {connexa_api_path}") # Added logging
            await ctx.info(log_messages[-1])
            delete_result = await call_api(
                action="delete",
                path=connexa_api_path,
                id=None # ID is already in the path
            )

            delete_api_status = delete_result.get("status")
            delete_api_message = delete_result.get("message", delete_result.get("notes", "No details provided"))
            log_messages.append(f"call_api deletion result: {delete_result}")
            await ctx.info(log_messages[-1])


            connexa_delete_successful = False
            connexa_final_message = delete_api_message

            if delete_api_status == 204: # 204 No Content is the expected success status for DELETE
                connexa_delete_successful = True
                log_messages.append(f"Connector '{object_name}' (ID: {object_id}) successfully deleted via call_api. Status: {delete_api_status}, Message: {delete_api_message}")
                await ctx.info(log_messages[-1])
                connexa_final_message = f"Deletion successful (Status 204)."
            else:
                # call_api did not return 204. Report the failure.
                log_messages.append(f"Failed to delete connector '{object_name}' (ID: {object_id}) using call_api. Status: {delete_api_status}, Message: {delete_api_message}")
                await ctx.error(log_messages[-1])
                connexa_final_message = f"Deletion failed (Status {delete_api_status}): {delete_api_message}"
                # connexa_delete_successful remains False

            if not connexa_delete_successful:
                 # If Connexa deletion was not successful, return an error.
                 # Include AWS deprovisioning status in the error message for context.
                return {"status": "error", "message": f"Failed to delete connector '{object_name}' (ID: {object_id}) from Connexa. AWS deprovisioning status: {deprovision_message}. Connexa deletion details: {connexa_final_message}", "log": log_messages}

            # If we reach here, AWS deprovisioning was attempted (or skipped) and Connexa deletion was successful.
            delete_status["message"] = f"Successfully deleted connector '{object_name}' (ID: {object_id}) from Connexa. AWS deprovisioning details: {deprovision_message}. Connexa deletion details: {connexa_final_message}"

        else:
            log_messages.append(f"Deleting {object_type} '{object_name}' (ID: {object_id}) using call_api...")
            await ctx.info(log_messages[-1])
            # Generic delete logic for other object types using call_api
            # This assumes a consistent API path structure like /api/v1/{object_type}s/{id}
            # and that the call_api tool can handle the DELETE action.
            # Need to confirm actual API paths and tool capabilities for other types.
            if not object_type:
                log_messages.append("object_type is None, cannot determine API path.")
                await ctx.error(log_messages[-1])
                return {"status": "error", "message": "Cannot delete object: object type is missing.", "log": log_messages}

            # Determine API path based on normalized object type
            normalized_object_type = object_type.lower().replace("-", "") # Assuming normalize_object_type exists or using simple lower+replace
            api_path = None

            if normalized_object_type == "network":
                api_path = f"/api/v1/networks/{{id}}"
            elif normalized_object_type == "user":
                api_path = f"/api/v1/users/{{id}}"
            elif normalized_object_type == "usergroup":
                api_path = f"/api/v1/user-groups/{{id}}"
            elif normalized_object_type == "host":
                api_path = f"/api/v1/hosts/{{id}}"
            elif normalized_object_type == "dnsrecord":
                api_path = f"/api/v1/dns-records/{{id}}"
            elif normalized_object_type == "accessgroup":
                api_path = f"/api/v1/access-groups/{{id}}"
            elif normalized_object_type == "locationcontext":
                api_path = f"/api/v1/location-contexts/{{id}}"
            elif normalized_object_type == "deviceposture":
                api_path = f"/api/v1/device-postures/{{id}}"
            elif normalized_object_type == "device":
                 # Handle device deletion requiring userId in path
                 user_id = CURRENT_SELECTED_OBJECT.details.get("userId")
                 if not user_id:
                     log_messages.append(f"Cannot delete device '{object_name}': userId is missing from selected object details.")
                     await ctx.error(log_messages[-1])
                     return {"status": "error", "message": f"Cannot delete device '{object_name}': userId is missing.", "log": log_messages}
                 api_path = f"/api/v1/devices/{{id}}?userId={user_id}" # Include userId in path
            elif normalized_object_type == "networkapplication":
                 network_id = CURRENT_SELECTED_OBJECT.details.get("networkId") or CURRENT_SELECTED_OBJECT.details.get("network_id")
                 # The API path for deleting a network application is /api/v1/networks/applications/{id}
                 api_path = f"/api/v1/networks/applications/{{id}}"
                 # No need to check for networkId here as it's not in the delete path
            elif normalized_object_type == "hostapplication":
                 # The API path for deleting a host application is /api/v1/hosts/applications/{id}
                 api_path = f"/api/v1/hosts/applications/{{id}}"
                 # No need to check for hostId here as it's not in the delete path
            # Note: Connector deletion is handled in the 'if object_type == "connector":' block above.

            if not api_path:
                 log_messages.append(f"Unsupported object type for deletion: {object_type}.")
                 await ctx.error(log_messages[-1])
                 return {"status": "error", "message": f"Unsupported object type for deletion: {object_type}.", "log": log_messages}

            # Format the API path with the object ID
            formatted_api_path = api_path.format(id=object_id)

            call_api_args = {
                "action": "delete",
                "path": formatted_api_path,
                "id": None # ID is already in the path
            }


            # Add logging before call_api
            log_messages.append(f"Debug: Calling call_api for deletion with args: {call_api_args}")
            await ctx.info(log_messages[-1])

            delete_result = await call_api(**call_api_args)

            # Add logging after call_api
            log_messages.append(f"Debug: call_api deletion result: {delete_result}")
            await ctx.info(log_messages[-1])

            delete_tool_status = delete_result.get("status")
            delete_tool_message = delete_result.get("message", delete_result.get("notes", "No details provided"))

            if not (isinstance(delete_tool_status, int) and 200 <= delete_tool_status < 300): # Modified success check
                 log_messages.append(f"Failed to delete {object_type} '{object_name}' (ID: {object_id}): API returned status {delete_tool_status}. Message: {delete_tool_message}")
                 await ctx.error(log_messages[-1])
                 return {"status": "error", "message": f"Failed to delete {object_type} '{object_name}' (ID: {object_id}): API returned status {delete_tool_status}. Message: {delete_tool_message}", "log": log_messages}

            # If we reach here, the API call was successful (status 2xx)
            delete_status["message"] = f"Successfully deleted {object_type} '{object_name}' (ID: {object_id}) via API. Status: {delete_tool_status}. Details: {delete_tool_message}"


        return delete_status

    except Exception as e:
        log_messages.append(f"An unexpected error occurred in delete_selected_object: {e}")
        await ctx.error(log_messages[-1])
        return {"status": "error", "message": f"An unexpected error occurred: {e}", "log": log_messages}
