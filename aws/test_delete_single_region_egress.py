import os
import json
from aws_tools import delete_regional_egress, refresh_aws_credentials_and_region

DETAILS_FILE = "single_region_egress_details.json"

if __name__ == '__main__':
    print("Starting delete_single_region_egress test...")

    refresh_aws_credentials_and_region() # Ensure AWS environment is set up

    if not os.path.exists(DETAILS_FILE):
        print(f"Error: Details file '{DETAILS_FILE}' not found.")
        print("Please run test_create_single_region_egress.py first to create resources and generate this file.")
        exit(1)

    details_to_delete = None
    try:
        with open(DETAILS_FILE, 'r') as f:
            details_to_delete = json.load(f)
        print(f"Successfully read egress details from {DETAILS_FILE}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {DETAILS_FILE}: {e}")
        exit(1)
    except IOError as e:
        print(f"Error reading {DETAILS_FILE}: {e}")
        exit(1)

    if details_to_delete:
        instance_id = details_to_delete.get("instance_id")
        prefix = details_to_delete.get("prefix")
        region_id = details_to_delete.get("region_id")
        sg_group_name = details_to_delete.get("sg_group_name")
        vpc_id = details_to_delete.get("vpc_id")
        instance_base_name = details_to_delete.get("instance_base_name")
        subnet_id_to_delete = details_to_delete.get("subnet_id_to_delete")

        # Basic validation
        if not prefix or not region_id:
            print("Error: 'prefix' and 'region_id' are required in the details file for deletion.")
            exit(1)
        
        # instance_id can be None if creation failed but other resources (like SG, subnet) might exist.
        # delete_regional_egress is designed to handle None instance_id for cleanup.

        print(f"\n--- Deleting/Cleaning Regional Egress (Instance ID: {instance_id or 'N/A'}, Prefix: {prefix}, Region: {region_id}) ---")
        
        delete_success = delete_regional_egress(
            instance_id=instance_id,
            prefix=prefix,
            region_id=region_id,
            sg_group_name=sg_group_name,
            vpc_id=vpc_id,
            instance_base_name=instance_base_name,
            subnet_id_to_delete=subnet_id_to_delete
        )
        
        if delete_success:
            print(f"Successfully processed deletion/cleanup for prefix {prefix} in region {region_id}.")
            # Optionally, remove the details file after successful deletion
            # try:
            #     os.remove(DETAILS_FILE)
            #     print(f"Removed details file: {DETAILS_FILE}")
            # except OSError as e:
            #     print(f"Error removing details file {DETAILS_FILE}: {e}")
        else:
            print(f"Deletion/cleanup for prefix {prefix} in region {region_id} failed or encountered issues.")
            print(f"The details file {DETAILS_FILE} has been kept for review.")
    else:
        print(f"No details found in {DETAILS_FILE} to process for deletion.")
    
    print("\ndelete_single_region_egress test finished.")
