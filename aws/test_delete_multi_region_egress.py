import os
import json
from aws_tools import delete_regional_egress, refresh_aws_credentials_and_region

DETAILS_FILE = "multi_region_egress_details.json"

if __name__ == '__main__':
    print("Starting delete_multi_region_egress test...")

    refresh_aws_credentials_and_region() # Ensure AWS environment is set up

    if not os.path.exists(DETAILS_FILE):
        print(f"Error: Details file '{DETAILS_FILE}' not found.")
        print("Please run test_create_multi_region_egress.py first to create resources and generate this file.")
        exit(1)

    all_details_to_delete = None
    try:
        with open(DETAILS_FILE, 'r') as f:
            all_details_to_delete = json.load(f)
        print(f"Successfully read egress details from {DETAILS_FILE}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {DETAILS_FILE}: {e}")
        exit(1)
    except IOError as e:
        print(f"Error reading {DETAILS_FILE}: {e}")
        exit(1)

    if isinstance(all_details_to_delete, list) and all_details_to_delete:
        overall_success = True
        for details in all_details_to_delete:
            instance_id = details.get("instance_id")
            prefix = details.get("prefix")
            region_id = details.get("region_id")
            sg_group_name = details.get("sg_group_name")
            vpc_id = details.get("vpc_id")
            instance_base_name = details.get("instance_base_name")
            subnet_id_to_delete = details.get("subnet_id_to_delete")

            if not prefix or not region_id:
                print(f"Error: Skipping entry due to missing 'prefix' or 'region_id': {details}")
                overall_success = False
                continue
            
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
            else:
                print(f"Deletion/cleanup for prefix {prefix} in region {region_id} failed or encountered issues.")
                overall_success = False
        
        if overall_success:
            print(f"\nAll multi-region deletions processed successfully.")
            # Optionally remove the details file
            # try:
            #     os.remove(DETAILS_FILE)
            #     print(f"Removed details file: {DETAILS_FILE}")
            # except OSError as e:
            #     print(f"Error removing details file {DETAILS_FILE}: {e}")
        else:
            print(f"\nSome multi-region deletions encountered issues. The details file {DETAILS_FILE} has been kept for review.")

    elif not all_details_to_delete: # Empty list
        print(f"No details found in {DETAILS_FILE} to process for deletion.")
    else: # Not a list
        print(f"Error: Expected a list of details in {DETAILS_FILE}, but found {type(all_details_to_delete)}.")

    print("\ndelete_multi_region_egress test finished.")
