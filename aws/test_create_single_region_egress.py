import os
import json
from aws_tools import upsert_regional_egress, refresh_aws_credentials_and_region

DETAILS_FILE = "single_region_egress_details.json"

if __name__ == '__main__':
    print("Starting create_single_region_egress test...")

    refresh_aws_credentials_and_region() 

    default_region_from_env = os.getenv("AWS_DEFAULT_REGION", "us-west-1")
    print(f"Using region: {default_region_from_env} for single region egress creation test.")

    test_prefix_ovpn = "test-sre-create-462e" 
    ovpn_file_name = "featherriverprinter_san_jose_(ca).ovpn"
    ovpn_profile_data = None
    try:
        with open(ovpn_file_name, 'r') as f:
            ovpn_profile_data = f.read()
        print(f"Successfully read OpenVPN profile: {ovpn_file_name}")
    except FileNotFoundError:
        print(f"Error: OpenVPN profile file '{ovpn_file_name}' not found. Make sure it exists in the current directory.")
        exit(1)
    except Exception as e:
        print(f"Error reading OpenVPN profile file '{ovpn_file_name}': {e}")
        exit(1)

    if ovpn_profile_data:
        print(f"\n--- Creating Public Regional Egress with OpenVPN (Region: {default_region_from_env}, Prefix: {test_prefix_ovpn}) ---")
        public_ovpn_egress_info = upsert_regional_egress(
            prefix=test_prefix_ovpn,
            public=True,
            region_id=default_region_from_env,
            openvpn_profile_content=ovpn_profile_data
        )
        if public_ovpn_egress_info and public_ovpn_egress_info.get("ovpn_instance_id"):
            print("\nPublic Egress with OpenVPN Setup Successful:")
            for key, value in public_ovpn_egress_info.items():
                print(f"  {key}: {value}")
            
            # Save details to file for the deletion script
            details_to_save = {
                "instance_id": public_ovpn_egress_info.get("ovpn_instance_id"),
                "prefix": test_prefix_ovpn,
                "region_id": default_region_from_env,
                "sg_group_name": public_ovpn_egress_info.get("ovpn_instance_security_group_name"),
                "vpc_id": public_ovpn_egress_info.get("vpc_id"),
                "instance_base_name": public_ovpn_egress_info.get("instance_base_name"),
                "subnet_id_to_delete": public_ovpn_egress_info.get("ovpn_instance_subnet_id")
            }
            try:
                with open(DETAILS_FILE, 'w') as f:
                    json.dump(details_to_save, f, indent=4)
                print(f"\nSuccessfully saved egress details to {DETAILS_FILE}")
                print("You can now run test_delete_single_region_egress.py to clean up these resources.")
            except IOError as e:
                print(f"Error writing details to {DETAILS_FILE}: {e}")
                print("Please manually note down the details above for cleanup if needed.")

        elif public_ovpn_egress_info:
            print("\nPublic Egress with OpenVPN setup initiated, but ovpn_instance_id was not found. Details:")
            for key, value in public_ovpn_egress_info.items():
                print(f"  {key}: {value}")
            print(f"Details were not saved to {DETAILS_FILE} as instance creation might have failed.")
            print("Review the output. If resources were partially created, manual cleanup might be needed or use delete_regional_egress with known parameters.")
        else:
            print("Public Egress with OpenVPN setup failed completely.")
    else:
        print(f"\n--- Skipping OpenVPN Egress Creation: Profile content from '{ovpn_file_name}' could not be loaded. ---")
    
    print("\ncreate_single_region_egress test finished.")
