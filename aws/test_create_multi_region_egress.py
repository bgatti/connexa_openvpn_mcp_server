import os
import json
from aws_tools import get_aws_regions, upsert_regional_egress, refresh_aws_credentials_and_region

DETAILS_FILE = "multi_region_egress_details.json"

if __name__ == '__main__':
    print("Starting create_multi_region_egress test...")

    refresh_aws_credentials_and_region()

    print("\n--- Listing Opted-In AWS Regions ---")
    available_regions = get_aws_regions(only_opted_in_regions=True)
    
    if not available_regions:
        print("Could not retrieve opted-in AWS regions. Aborting multi-region egress creation.")
        exit(1)
    print(f"Found {len(available_regions)} opted-in/available regions.")

    test_region_1 = os.getenv("AWS_TEST_REGION_1", "us-west-1")
    test_region_2 = os.getenv("AWS_TEST_REGION_2", "us-east-2")

    if test_region_1 not in available_regions:
        print(f"Warning: Test region 1 '{test_region_1}' not in available regions. Defaulting to 'us-west-1' if available, or first available region.")
        test_region_1 = "us-west-1" if "us-west-1" in available_regions else available_regions[0]
    
    regions_to_create_in = [test_region_1]
    if len(available_regions) > 1:
        if test_region_2 not in available_regions or test_region_2 == test_region_1:
            print(f"Warning: Test region 2 '{test_region_2}' not in available regions or same as region 1. Selecting a different one.")
            if "us-east-2" in available_regions and "us-east-2" != test_region_1:
                test_region_2 = "us-east-2"
            else:
                for region in available_regions:
                    if region != test_region_1:
                        test_region_2 = region
                        break
            if test_region_2 != test_region_1:
                 regions_to_create_in.append(test_region_2)
        elif test_region_2 != test_region_1 : # test_region_2 is valid and different
            regions_to_create_in.append(test_region_2)

    if len(regions_to_create_in) == 1 and test_region_1 != test_region_2 and len(available_regions) > 1:
         print(f"Warning: Could not find two distinct, valid, available regions for testing. Proceeding with: {regions_to_create_in}")
    elif len(regions_to_create_in) < 2 and len(available_regions) > 1:
        print(f"Warning: Only one distinct region selected for multi-region test: {regions_to_create_in}. Ensure AWS_TEST_REGION_1 and AWS_TEST_REGION_2 are set to distinct, available regions if two are desired.")


    print(f"Selected regions for egress creation: {regions_to_create_in}")

    test_prefix_ovpn_base = "mcp-mro-create" 
    ovpn_file_name = "featherriverprinter_san_jose_(ca).ovpn"
    ovpn_profile_data = None
    try:
        with open(ovpn_file_name, 'r') as f:
            ovpn_profile_data = f.read()
        print(f"Successfully read OpenVPN profile: {ovpn_file_name}")
    except FileNotFoundError:
        print(f"Error: OpenVPN profile file '{ovpn_file_name}' not found. Make sure it exists.")
        exit(1)
    except Exception as e:
        print(f"Error reading OpenVPN profile file '{ovpn_file_name}': {e}")
        exit(1)

    all_created_egress_details = []
    if ovpn_profile_data:
        for region_to_test in regions_to_create_in:
            current_test_prefix = f"{test_prefix_ovpn_base}-{region_to_test.replace('-', '')}"
            print(f"\n--- Creating Public Regional Egress with OpenVPN (Region: {region_to_test}, Prefix: {current_test_prefix}) ---")
            
            public_ovpn_egress_info = upsert_regional_egress(
                prefix=current_test_prefix,
                public=True,
                region_id=region_to_test,
                openvpn_profile_content=ovpn_profile_data
            )
            
            if public_ovpn_egress_info and public_ovpn_egress_info.get("ovpn_instance_id"):
                print(f"\nPublic Egress with OpenVPN Setup Successful for Region {region_to_test}:")
                for key, value in public_ovpn_egress_info.items():
                    print(f"  {key}: {value}")
                
                # Store details for this region
                details_for_region = {
                    "instance_id": public_ovpn_egress_info.get("ovpn_instance_id"),
                    "prefix": current_test_prefix,
                    "region_id": region_to_test,
                    "sg_group_name": public_ovpn_egress_info.get("ovpn_instance_security_group_name"),
                    "vpc_id": public_ovpn_egress_info.get("vpc_id"),
                    "instance_base_name": public_ovpn_egress_info.get("instance_base_name"),
                    "subnet_id_to_delete": public_ovpn_egress_info.get("ovpn_instance_subnet_id")
                }
                all_created_egress_details.append(details_for_region)
            elif public_ovpn_egress_info:
                 print(f"\nPublic Egress setup for {region_to_test} initiated, but ovpn_instance_id was not found. Details:")
                 for key, value in public_ovpn_egress_info.items():
                    print(f"  {key}: {value}")
                 print(f"Skipping saving details for {region_to_test} as instance creation might have failed.")
            else:
                print(f"Public Egress with OpenVPN setup failed completely for Region {region_to_test}.")
        
        if all_created_egress_details:
            try:
                with open(DETAILS_FILE, 'w') as f:
                    json.dump(all_created_egress_details, f, indent=4)
                print(f"\nSuccessfully saved all created egress details to {DETAILS_FILE}")
                print("You can now run test_delete_multi_region_egress.py to clean up these resources.")
            except IOError as e:
                print(f"Error writing details to {DETAILS_FILE}: {e}")
                print("Please manually note down the details above for cleanup if needed.")
        else:
            print(f"\nNo egress resources were successfully created with an instance ID. {DETAILS_FILE} not written.")

    else:
        print(f"\n--- Skipping Multi-Region OpenVPN Egress Creation: Profile content from '{ovpn_file_name}' could not be loaded. ---")
    
    print("\ncreate_multi_region_egress test finished.")
