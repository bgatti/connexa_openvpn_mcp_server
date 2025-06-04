import os
import boto3
import botocore.exceptions # Added for specific exception handling
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List # Import List
import random # Added for random CIDR generation
import threading # Added for background EIP association

# Import functions from aws_boto3_apis.py
# Assuming aws_boto3_apis.py is in the same directory
if __name__ == "__main__" or __package__ is None or __package__ == '':
    # When running aws_tools.py directly for testing
    import aws_boto3_apis as aws_ops
else:
    # When aws_tools.py is imported as part of the 'aws' package
    from . import aws_boto3_apis as aws_ops

# Helper functions for subnet creation with random CIDR strategy
# START OF NEW HELPER FUNCTIONS

def _find_existing_subnet_by_name(ec2_client, vpc_id: str, subnet_name: str) -> Optional[str]:
    """Checks if a subnet with the given Name tag already exists in the VPC."""
    try:
        response = ec2_client.describe_subnets(
            Filters=[
                {'Name': 'vpc-id', 'Values': [vpc_id]},
                {'Name': 'tag:Name', 'Values': [subnet_name]}
            ]
        )
        if response['Subnets']:
            # Assuming the name tag is unique enough for this purpose within the VPC
            return response['Subnets'][0]['SubnetId']
    except botocore.exceptions.ClientError as e:
        print(f"Error describing subnets to find existing '{subnet_name}': {e}")
    return None

def _ensure_route_to_igw(ec2_client, vpc_id: str, subnet_id: str, igw_id: str) -> bool:
    """Ensures a route to the specified Internet Gateway exists in the subnet's route table."""
    try:
        # Determine the route table for the subnet
        rt_response = ec2_client.describe_route_tables(
            Filters=[{'Name': 'association.subnet-id', 'Values': [subnet_id]}]
        )
        route_table_id = None
        if rt_response.get('RouteTables'):
            route_table_id = rt_response['RouteTables'][0]['RouteTableId']
        else:
            # If no explicit association, it uses the main route table for the VPC
            main_rt_response = ec2_client.describe_route_tables(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}, {'Name': 'association.main', 'Values': ['true']}]
            )
            if main_rt_response.get('RouteTables'):
                route_table_id = main_rt_response['RouteTables'][0]['RouteTableId']
        
        if not route_table_id:
            print(f"Error: Could not determine route table for subnet {subnet_id} in VPC {vpc_id}.")
            return False

        # Create the default route to the Internet Gateway
        ec2_client.create_route(
            RouteTableId=route_table_id,
            DestinationCidrBlock='0.0.0.0/0',
            GatewayId=igw_id
        )
        print(f"Ensured route 0.0.0.0/0 -> {igw_id} in route table {route_table_id} for subnet {subnet_id} (created).")
        return True
    except botocore.exceptions.ClientError as e:
        # Check if route_table_id was bound before trying to use it in error messages
        rt_id_for_log = locals().get('route_table_id', 'unknown (error before assignment)') # For logging if general error

        if e.response.get('Error', {}).get('Code') == 'RouteAlreadyExists':
            # This error code implies that the 'create_route' call was attempted,
            # which means 'route_table_id' must have been non-None when 'create_route' was called.
            # So, 'route_table_id' as captured by locals() or directly should be valid here.
            # To satisfy Pylance, we ensure it's explicitly checked before use in this specific block.
            
            current_route_table_id = locals().get('route_table_id') # Get the value as it was in the try block
            if current_route_table_id is None:
                # This case should be logically impossible if RouteAlreadyExists was raised by create_route,
                # as create_route would have failed earlier if route_table_id was None.
                print(f"Critical Error: 'RouteAlreadyExists' received, but route_table_id was not determined (is None) for subnet {subnet_id}. Error: {e}")
                return False

            # Now current_route_table_id is confirmed not None.
            print(f"A route for 0.0.0.0/0 already exists in route table {current_route_table_id}. Verifying and updating if necessary...")
            try:
                # Describe the existing route to check its target and state
                rt_details = ec2_client.describe_route_tables(RouteTableIds=[current_route_table_id])
                existing_route = None
                for route in rt_details.get('RouteTables', [{}])[0].get('Routes', []):
                    if route.get('DestinationCidrBlock') == '0.0.0.0/0':
                        existing_route = route
                        break
                
                if existing_route:
                    current_gateway_id = existing_route.get('GatewayId')
                    current_state = existing_route.get('State') # 'active' or 'blackhole'
                    
                    if current_gateway_id == igw_id and current_state == 'active':
                        print(f"Existing route 0.0.0.0/0 -> {current_gateway_id} in route table {current_route_table_id} is active and correct. No change needed.")
                        return True
                    else:
                        print(f"Existing route 0.0.0.0/0 in {current_route_table_id} points to {current_gateway_id} (state: {current_state}). Expected IGW: {igw_id}. Replacing route...")
                        ec2_client.replace_route(
                            RouteTableId=current_route_table_id,
                            DestinationCidrBlock='0.0.0.0/0',
                            GatewayId=igw_id
                        )
                        print(f"Successfully replaced route in {current_route_table_id} to point 0.0.0.0/0 -> {igw_id}.")
                        return True
                else:
                    # This case should be rare if RouteAlreadyExists was thrown
                    print(f"Error: RouteAlreadyExists was reported for {current_route_table_id}, but could not find the 0.0.0.0/0 route to verify. Attempting to create again.")
                    ec2_client.create_route(
                        RouteTableId=current_route_table_id,
                        DestinationCidrBlock='0.0.0.0/0',
                        GatewayId=igw_id
                    )
                    print(f"Re-attempted and created route 0.0.0.0/0 -> {igw_id} in {current_route_table_id} after failing to verify existing.")
                    return True

            except Exception as verify_e:
                print(f"Error verifying/replacing existing route in {current_route_table_id} for IGW {igw_id}: {verify_e}")
                return False
        else:
            # Original error was not RouteAlreadyExists
            # rt_id_for_log (which is locals().get('route_table_id', ...)) is appropriate here
            print(f"Error ensuring route to IGW for subnet {subnet_id} (route table ID used in failed create_route: {rt_id_for_log}): {e}")
            return False

def _upsert_public_subnet_with_random_cidrs(ec2_client, vpc_id: str, vpc_main_cidr: str, subnet_base_name: str, prefix: str) -> Optional[str]:
    """
    Upserts a public subnet. Finds an existing one by name tag or creates a new one
    using a random third octet strategy for a /24 CIDR. Ensures it's public via IGW.
    """
    subnet_name_tag = f"{prefix}_{subnet_base_name}_subnet"

    existing_subnet_id = _find_existing_subnet_by_name(ec2_client, vpc_id, subnet_name_tag)
    if existing_subnet_id:
        print(f"Found existing public subnet '{subnet_name_tag}' with ID: {existing_subnet_id}. Verifying IGW route.")
        igw_id = aws_ops.upsert_named_internet_gateway(ec2_client, vpc_id, prefix)
        if not igw_id:
            print(f"Error: Failed to upsert Internet Gateway for VPC {vpc_id} when verifying existing subnet {existing_subnet_id}.")
            return None
        if not _ensure_route_to_igw(ec2_client, vpc_id, existing_subnet_id, igw_id):
            print(f"Error: Failed to ensure IGW route for existing subnet {existing_subnet_id}.")
            return None
        return existing_subnet_id

    print(f"Public subnet '{subnet_name_tag}' not found, attempting to create a new one...")
    
    if '/' not in vpc_main_cidr:
        print(f"Invalid VPC CIDR format: {vpc_main_cidr}. Expected format like '172.31.0.0/16'.")
        return None
    base_ip_part = vpc_main_cidr.split('/')[0]
    octets = base_ip_part.split('.')
    if len(octets) != 4:
        print(f"Invalid base IP format in VPC CIDR: {base_ip_part}")
        return None
    first_two_octets = f"{octets[0]}.{octets[1]}"

    possible_third_octets = list(range(256))
    random.shuffle(possible_third_octets)
    third_octets_to_try = possible_third_octets[:50] # Try up to 50 unique random octets

    created_subnet_id = None
    for third_octet in third_octets_to_try:
        subnet_cidr_block = f"{first_two_octets}.{third_octet}.0/24"
        print(f"Attempting to create subnet '{subnet_name_tag}' with CIDR block: {subnet_cidr_block}")
        try:
            subnet_response = ec2_client.create_subnet(
                VpcId=vpc_id,
                CidrBlock=subnet_cidr_block,
                TagSpecifications=[{'ResourceType': 'subnet', 'Tags': [{'Key': 'Name', 'Value': subnet_name_tag}]}]
            )
            created_subnet_id = subnet_response['Subnet']['SubnetId']
            print(f"Successfully created subnet '{subnet_name_tag}' with ID {created_subnet_id} and CIDR {subnet_cidr_block}")
            
            waiter = ec2_client.get_waiter('subnet_available')
            waiter.wait(SubnetIds=[created_subnet_id])
            print(f"Subnet {created_subnet_id} is available.")
            break 
        except botocore.exceptions.ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == 'InvalidSubnet.Conflict':
                print(f"CIDR block {subnet_cidr_block} conflicts. Trying next random CIDR.")
            elif error_code == 'InvalidSubnet': # Broader InvalidSubnet error
                print(f"InvalidSubnet error for CIDR {subnet_cidr_block}: {e}. Trying next random CIDR.")
            else:
                print(f"Unexpected error creating subnet with CIDR {subnet_cidr_block}: {e}")
                return None 
    
    if not created_subnet_id:
        print(f"Failed to create subnet '{subnet_name_tag}' after trying {len(third_octets_to_try)} random CIDRs.")
        return None

    igw_id = aws_ops.upsert_named_internet_gateway(ec2_client, vpc_id, prefix)
    if not igw_id:
        print(f"Error: Failed to upsert Internet Gateway for VPC {vpc_id} after creating subnet {created_subnet_id}.")
        # Consider deleting the created_subnet_id here for cleanup
        return None
    
    if not _ensure_route_to_igw(ec2_client, vpc_id, created_subnet_id, igw_id):
        print(f"Error: Failed to ensure IGW route for newly created subnet {created_subnet_id}.")
        # Consider deleting the created_subnet_id here for cleanup
        return None
        
    return created_subnet_id

# END OF NEW HELPER FUNCTIONS

def refresh_aws_credentials_and_region(region_id: Optional[str] = None) -> Dict[str, Optional[str]]:
    """
    Loads AWS credentials and region from .env file and sets them as environment variables.
    Updates os.environ so boto3 can pick them up.
    A specific region_id can override the one in .env or serve as default.
    Returns a dictionary with the loaded/prioritized credentials and region.
    """
    # Load environment variables from .env files, prioritizing the one in the current directory (aws/)
    # and then the one in the parent directory (connexa_openvpn_mcp_server/).
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'), override=False) # Don't override if already set by the aws/.env

    creds = {
        "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "aws_default_region": os.getenv("AWS_DEFAULT_REGION")
    }

    if region_id:
        creds["aws_default_region"] = region_id
    
    # Ensure these are set in the environment for boto3 to use if not already configured elsewhere
    if creds["aws_access_key_id"]:
        os.environ['AWS_ACCESS_KEY_ID'] = creds["aws_access_key_id"]
    if creds["aws_secret_access_key"]:
        os.environ['AWS_SECRET_ACCESS_KEY'] = creds["aws_secret_access_key"]
    if creds["aws_default_region"]:
        os.environ['AWS_DEFAULT_REGION'] = creds["aws_default_region"]
        
    print(f"Using AWS Region: {creds['aws_default_region']}")
    if not creds["aws_access_key_id"] or not creds["aws_secret_access_key"]:
        print("Warning: AWS Access Key ID or Secret Access Key is not set in .env or environment.")
    
    return creds

def validate_aws_credentials() -> bool:
    """
    Loads AWS credentials using refresh_aws_credentials_and_region and validates them
    by making a simple API call (get_caller_identity).
    Returns:
        True if credentials are loaded and validated successfully, False otherwise.
    """
    print("Validating AWS credentials...")
    loaded_creds = refresh_aws_credentials_and_region() # Load from .env using default behavior

    if not loaded_creds.get("aws_access_key_id") or \
       not loaded_creds.get("aws_secret_access_key") or \
       not loaded_creds.get("aws_default_region"):
        print("Credential validation failed: AWS access key, secret key, or default region not found after loading .env.")
        return False

    try:
        # Use the loaded default region for the STS client, or a common one like 'us-east-1' if needed
        # The region for STS get_caller_identity is generally not critical as it's a global service.
        sts_region = loaded_creds.get("aws_default_region", "us-east-1")
        sts_client = boto3.client('sts', region_name=sts_region)
        identity = sts_client.get_caller_identity()
        print(f"AWS credential validation successful. Account: {identity.get('Account')}, UserID: {identity.get('UserId')}, ARN: {identity.get('Arn')}")
        return True
    except Exception as e:
        print(f"AWS credential validation failed: Error calling get_caller_identity - {str(e)}")
        return False

def upsert_regional_egress(prefix: str, public: bool, region_id: Optional[str] = None, openvpn_profile_content: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Creates or updates regional egress resources.
    If public is True:
        - If openvpn_profile_content is provided, sets up an EC2 instance with OpenVPN for egress.
        - Otherwise, sets up a NAT Gateway for egress.
    If public is False, it might set up resources for private egress or controlled internet access.

    Args:
        prefix: A prefix string for naming AWS resources.
        public: Boolean indicating if public internet egress is required.
        region_id: Optional AWS region ID. If None, uses AWS_DEFAULT_REGION from .env or environment.
        openvpn_profile_content: Optional. If provided and public is True, an EC2 instance will be configured for OpenVPN egress.

    Returns:
        A dictionary containing details of the created/updated resources, including a public IP if applicable.
        Example: {'vpc_id': 'vpc-xxxx', 'subnet_id': 'subnet-xxxx', 'public_ip': 'x.x.x.x', ...}
                 Returns None on failure.
    """
    print(f"Initiating upsert_regional_egress for prefix '{prefix}', public: {public}, region: {region_id or 'default'}, OVPN profile provided: {bool(openvpn_profile_content)}")

    # Load/refresh credentials and set region
    loaded_creds = refresh_aws_credentials_and_region(region_id)
    current_region = loaded_creds.get("aws_default_region")

    if not current_region:
        print("Error: AWS region is not configured. Cannot proceed.")
        return None

    # Initialize EC2 client for the specified or default region
    # Boto3 will use credentials from os.environ if set, or from other configured sources.
    try:
        ec2_client = boto3.client('ec2', region_name=current_region)
    except Exception as e:
        print(f"Error creating EC2 client for region {current_region}: {e}")
        return None

    # Get the latest Amazon Linux 2023 AMI ID for the current region
    ami_id = aws_ops.get_latest_amazon_linux_2023_ami_id(ec2_client) # Pass client
    if not ami_id:
        print(f"Error: Could not retrieve latest Amazon Linux 2023 AMI ID in region {current_region}.")
        return None
    print(f"Using AMI ID: {ami_id} for region {current_region}")

    # Get default VPC information for the current region
    # Pass the ec2_client to get_default_vpc_info for consistency
    vpc_info = aws_ops.get_default_vpc_info(ec2_client=ec2_client) 

    if not vpc_info or not vpc_info.get('VpcId'):
        print(f"Error: Could not retrieve default VPC information in region {current_region}.")
        return None
    
    vpc_id = vpc_info['VpcId']
    vpc_cidr_block = vpc_info['CidrBlock']
    
    egress_details = {
        "vpc_id": vpc_id,
        "region": current_region,
        "prefix": prefix,
        "public_egress_requested": public,
        "openvpn_profile_provided": bool(openvpn_profile_content),
        "public_ip": None,
        "notes": []
    }

    if public:
        if openvpn_profile_content:
            # Scenario 1A: Public Egress via OpenVPN EC2 Instance
            egress_details["egress_type"] = "OpenVPN_EC2_Instance"
            print(f"Setting up Public Egress via OpenVPN EC2 Instance for prefix '{prefix}'")

            # Instance parameters
            key_name = "mcp_openvpn" # Ensure this key pair exists in the region
            instance_base_name = "ovpn_egress" # Base name for the instance and related resources
            egress_details["instance_base_name"] = instance_base_name # Store for deletion context

            # 1. Upsert public subnet for the OVPN instance
            # Using new local upsert function with random CIDR strategy
            ovpn_public_subnet_id = _upsert_public_subnet_with_random_cidrs(
                ec2_client=ec2_client,
                vpc_id=vpc_id,
                vpc_main_cidr=vpc_cidr_block, # Renamed for clarity in the helper
                subnet_base_name=f"{instance_base_name}_public",
                prefix=prefix
            )
            if not ovpn_public_subnet_id:
                msg = f"Failed to upsert public subnet for OpenVPN instance in {current_region}."
                print(f"Error: {msg}")
                egress_details["notes"].append(msg)
                return egress_details
            egress_details["ovpn_instance_subnet_id"] = ovpn_public_subnet_id
            
            # Analyze NACL for the created/found subnet
            if ovpn_public_subnet_id:
                nacl_analysis = aws_ops.analyze_nacl_for_subnet(ec2_client, ovpn_public_subnet_id)
                egress_details["nacl_analysis_for_ovpn_subnet"] = nacl_analysis
            else:
                egress_details["nacl_analysis_for_ovpn_subnet"] = {"status": "SKIPPED", "analysis_notes": ["Subnet ID not available for NACL analysis."]}


            # 2. Upsert security group for the OVPN instance
            # The sg_base_name passed to aws_ops.upsert_instance_security_group is just instance_base_name.
            # aws_ops.upsert_instance_security_group is assumed to construct the full name as prefix_sgbasename_sg.
            constructed_sg_name = f"{prefix}_{instance_base_name}_sg"
            egress_details["ovpn_instance_security_group_name"] = constructed_sg_name # Store the full name

            ingress_rules = [
                {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}, # SSH
                {'IpProtocol': 'udp', 'FromPort': 1194, 'ToPort': 1194, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},# OpenVPN UDP
                {'IpProtocol': 'tcp', 'FromPort': 443, 'ToPort': 443, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},  # OpenVPN TCP (optional)
                {'IpProtocol': 'icmp', 'FromPort': -1, 'ToPort': -1, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]} # ICMP for Ping (All ICMP types)
            ]
            ovpn_sg_id = aws_ops.upsert_instance_security_group(
                ec2_client=ec2_client, # Pass client
                vpc_id=vpc_id,
                ingress_rules=ingress_rules,
                sg_base_name=instance_base_name, 
                prefix=prefix
            )
            if not ovpn_sg_id:
                msg = f"Failed to upsert security group for OpenVPN instance in {current_region}."
                print(f"Error: {msg}")
                egress_details["notes"].append(msg)
                return egress_details
            egress_details["ovpn_instance_security_group_id"] = ovpn_sg_id

            # 3. Upsert the EC2 instance
            # Pass ec2_client to aws_ops.upsert_small_ec2_instance
            instance_info = aws_ops.upsert_small_ec2_instance(
                ec2_client=ec2_client, # Pass client
                instance_base_name=instance_base_name, 
                ami_id=ami_id, # This is now the dynamically fetched AMI ID
                prefix=prefix,
                key_name=key_name,
                security_group_ids=[ovpn_sg_id],
                subnet_id=ovpn_public_subnet_id,
                openvpn_profile_content=openvpn_profile_content,
                instance_type='t3.small' # As per original task context
            )

            if instance_info and instance_info.get('InstanceId') and instance_info.get('Status') == 'PROVISIONING_STARTED':
                instance_id_for_bg = instance_info['InstanceId']
                egress_details["ovpn_instance_id"] = instance_id_for_bg
                egress_details["public_ip"] = None # IP not available yet, will be set by background task
                egress_details["instance_status"] = "PROVISIONING_STARTED"
                
                # Spawn background thread for waiting and EIP association
                # Ensure instance_base_name and prefix are correctly passed for EIP tagging
                print(f"Spawning background thread for post-launch operations on instance {instance_id_for_bg}.")
                bg_thread = threading.Thread(
                    target=_background_post_launch_tasks,
                    args=(
                        current_region, # Pass region_name, thread will create its own client
                        instance_id_for_bg,
                        instance_base_name, # This is the base_name for EIP tagging
                        prefix # This is the prefix for EIP tagging
                    )
                )
                bg_thread.start()
                egress_details["notes"].append(f"OpenVPN egress instance {instance_id_for_bg} provisioning started. EIP association and final checks will occur in background.")

            elif instance_info and instance_info.get('InstanceId') and instance_info.get('PublicIpAddress'): # Existing running instance or one that got IP quickly
                egress_details["public_ip"] = instance_info['PublicIpAddress']
                egress_details["ovpn_instance_id"] = instance_info['InstanceId']
                egress_details["instance_status"] = "RUNNING_WITH_IP" # Or similar status
                egress_details["notes"].append(f"OpenVPN egress instance {instance_info['InstanceId']} created/found with IP {instance_info['PublicIpAddress']}.")
            else: # Covers failure or unexpected return from upsert_small_ec2_instance
                msg = f"Failed to create/find OpenVPN egress EC2 instance or instance_info was unexpected: {instance_info}"
                print(f"Error: {msg}")
                egress_details["notes"].append(msg)
                egress_details["instance_status"] = "FAILED_OR_UNKNOWN"
                # public_ip remains None
        
        else:
            # Scenario 1B: Public Egress via NAT Gateway
            egress_details["egress_type"] = "NAT_Gateway"
            print(f"Setting up Public Egress via NAT Gateway for prefix '{prefix}'")

            public_subnet_base_name = "nat_egress_public" # Subnet for the NAT GW itself
            # Using new local upsert function with random CIDR strategy
            public_subnet_id = _upsert_public_subnet_with_random_cidrs(
                ec2_client=ec2_client,
                vpc_id=vpc_id,
                vpc_main_cidr=vpc_cidr_block, # Renamed for clarity in the helper
                subnet_base_name=public_subnet_base_name,
                prefix=prefix
            )
            if not public_subnet_id:
                msg = f"Failed to upsert public subnet for NAT Gateway in {current_region}."
                print(f"Error: {msg}")
                egress_details["notes"].append(msg)
                return egress_details
            egress_details["nat_gateway_public_subnet_id"] = public_subnet_id

            # Analyze NACL for the NAT gateway's public subnet
            if public_subnet_id:
                nacl_analysis_nat = aws_ops.analyze_nacl_for_subnet(ec2_client, public_subnet_id)
                egress_details["nacl_analysis_for_nat_subnet"] = nacl_analysis_nat
            else:
                egress_details["nacl_analysis_for_nat_subnet"] = {"status": "SKIPPED", "analysis_notes": ["NAT Subnet ID not available for NACL analysis."]}
            
            nat_eip_base_name = "nat_gateway"
            nat_eip_allocation_id = None
            nat_public_ip = None
            try:
                eip_tag_name = f"{prefix}_{nat_eip_base_name}_eip"
                allocation = ec2_client.allocate_address(Domain='vpc') # No tags at allocation for NAT EIP
                nat_eip_allocation_id = allocation['AllocationId']
                nat_public_ip = allocation['PublicIp']
                # Tag the EIP separately
                ec2_client.create_tags(Resources=[nat_eip_allocation_id], Tags=[{'Key': 'Name', 'Value': eip_tag_name}])
                
                egress_details["public_ip"] = nat_public_ip
                egress_details["nat_gateway_eip_allocation_id"] = nat_eip_allocation_id
                print(f"Allocated and tagged Elastic IP {nat_public_ip} (ID: {nat_eip_allocation_id}) for NAT Gateway.")
            except Exception as e:
                print(f"Error allocating or tagging Elastic IP for NAT Gateway: {e}")
                egress_details["notes"].append(f"Failed to allocate/tag EIP for NAT GW: {str(e)}")

            if nat_eip_allocation_id and public_subnet_id:
                nat_gateway_id = None
                try:
                    # Check if a NAT gateway already exists for this EIP or in this subnet to avoid duplication
                    # This logic can be complex; for now, we attempt creation.
                    # A more robust solution would describe NAT gateways and match.
                    
                    response = ec2_client.create_nat_gateway(
                        SubnetId=public_subnet_id,
                        AllocationId=nat_eip_allocation_id
                        # No TagSpecifications here
                    )
                    nat_gateway_id = response['NatGateway']['NatGatewayId']
                    egress_details["nat_gateway_id"] = nat_gateway_id
                    print(f"Creating NAT Gateway {nat_gateway_id} in subnet {public_subnet_id}...")

                    waiter = ec2_client.get_waiter('nat_gateway_available')
                    waiter.wait(NatGatewayIds=[nat_gateway_id])
                    print(f"NAT Gateway {nat_gateway_id} is available.")
                    
                    # Tag the NAT Gateway after creation
                    nat_gw_name_tag = f"{prefix}_nat_gateway"
                    ec2_client.create_tags(Resources=[nat_gateway_id], Tags=[{'Key': 'Name', 'Value': nat_gw_name_tag}])
                    egress_details["notes"].append(f"NAT Gateway {nat_gateway_id} (tagged: {nat_gw_name_tag}) created and available.")

                except Exception as e:
                    print(f"Error creating NAT Gateway: {e}")
                    egress_details["notes"].append(f"Failed to create NAT GW: {str(e)}")
                    if nat_eip_allocation_id and "already has a NAT gateway" not in str(e).lower() and "already exists" not in str(e).lower() :
                        try:
                            print(f"Releasing EIP {nat_eip_allocation_id} due to NAT Gateway creation failure.")
                            ec2_client.release_address(AllocationId=nat_eip_allocation_id)
                        except Exception as rel_e:
                            print(f"Error releasing EIP {nat_eip_allocation_id}: {rel_e}")
            else:
                message = "Cannot create NAT Gateway: Missing Elastic IP allocation or public subnet."
                print(message)
                egress_details["notes"].append(message)
    else:
        # Scenario 2: Non-public or controlled egress
        egress_details["egress_type"] = "IGW_Only_Or_Private"
        print(f"Setting up Non-Public/Controlled Egress for prefix '{prefix}'")
        igw_id = aws_ops.upsert_named_internet_gateway(ec2_client, vpc_id, prefix)
        if igw_id:
            egress_details["internet_gateway_id"] = igw_id
            egress_details["notes"].append(f"Ensured Internet Gateway {igw_id} is present for VPC {vpc_id}.")
        else:
            egress_details["notes"].append(f"Failed to ensure Internet Gateway for VPC {vpc_id}.")
        egress_details["public_ip"] = "N/A (IGW for VPC ensured, no dedicated public egress IP setup)"

    return egress_details


def _background_post_launch_tasks(region_name: str, instance_id: str, instance_base_name_for_eip: str, prefix_for_eip: str):
    """
    Background task to wait for an instance to be running and then associate an Elastic IP.
    This function is intended to be run in a separate thread.
    """
    try:
        print(f"[Thread-{threading.get_ident()}] Background task started for instance {instance_id} in region {region_name}.")
        # Create a new Boto3 EC2 client for this thread
        thread_ec2_client = boto3.client('ec2', region_name=region_name)

        # Wait for the instance to be running
        waiter = thread_ec2_client.get_waiter('instance_running')
        print(f"[Thread-{threading.get_ident()}] Waiting for instance {instance_id} to be running...")
        waiter.wait(InstanceIds=[instance_id])
        print(f"[Thread-{threading.get_ident()}] Instance {instance_id} is now running.")

        # Associate the Elastic IP
        # Note: aws_ops is imported at the top of aws_tools.py
        elastic_ip = aws_ops.upsert_elastic_ip(
            ec2_client=thread_ec2_client,
            instance_id=instance_id,
            base_name_for_eip_tag=instance_base_name_for_eip,
            prefix=prefix_for_eip
        )

        if elastic_ip:
            print(f"[Thread-{threading.get_ident()}] Successfully associated Elastic IP {elastic_ip} with instance {instance_id}.")
            # Here you could potentially update a status in a database or send a notification
        else:
            print(f"[Thread-{threading.get_ident()}] Failed to associate Elastic IP with instance {instance_id}.")

    except Exception as e:
        print(f"[Thread-{threading.get_ident()}] Error in background task for instance {instance_id}: {e}")


def delete_regional_egress_by_prefix(
    instance_id: Optional[str], # Made instance_id optional
    prefix: Optional[str] = None,
    region_id: Optional[str] = None,
    sg_group_name: Optional[str] = None,
    vpc_id: Optional[str] = None,
    instance_base_name: Optional[str] = None,
    subnet_id_to_delete: Optional[str] = None # ID of the subnet to delete
) -> Dict[str, Any]: # Changed return type hint to Dict[str, Any]
    """
    Deletes regional egress resources by prefix: EC2 instance, EIP, Security Group, and associated Subnet.

    Args:
        instance_id: The ID of the EC2 instance to delete.
        prefix: The prefix used for tagging resources.
        region_id: Optional AWS region ID.
        sg_group_name: The GroupName of the security group to delete.
        vpc_id: The VPC ID where the security group resides.
        instance_base_name: The base name used for EIP tagging (e.g., "ovpn_egress").
        subnet_id_to_delete: Optional ID of the subnet to delete.

    Returns:
        A dictionary containing:
        - "status": "success" or "failure"
        - "notes": A list of notes about the deletion process.
        - "details": A dictionary with details of deleted resources (if available).
    """
    print(f"Initiating delete_regional_egress for instance ID '{instance_id}', prefix: {prefix}, region: {region_id or 'default'}, subnet: {subnet_id_to_delete}")

    loaded_creds = refresh_aws_credentials_and_region(region_id)
    current_region = loaded_creds.get("aws_default_region")

    result: Dict[str, Any] = {
        "status": "failure",
        "notes": [],
        "details": {}
    }

    if not current_region:
        msg = "Error: AWS region is not configured. Cannot proceed with deletion."
        print(msg)
        result["notes"].append(msg)
        return result
    
    ec2_client = boto3.client('ec2', region_name=current_region)

    # 1. Delete EC2 instance and its associated/tagged EIP
    # The instance_base_name is crucial for finding the EIP by tag.
    instance_and_eip_deleted = True # Default to True if no instance_id is provided
    instance_deletion_notes: List[str] = []
    eip_deletion_notes: List[str] = []

    if instance_id:
        print(f"Step 1: Deleting instance {instance_id} and its EIPs (using base_name: {instance_base_name})...")
        # Pass ec2_client to aws_ops.delete_if_found
        instance_and_eip_deleted = aws_ops.delete_if_found(
            ec2_client=ec2_client, # Pass client
            instance_id=instance_id,
            prefix=prefix,
            base_name_for_eip_tag=instance_base_name
        )
        # Assuming aws_ops.delete_if_found returns a boolean
        if instance_and_eip_deleted:
             instance_deletion_notes.append(f"Instance {instance_id} and associated EIP processed for deletion.")
        else:
             instance_deletion_notes.append(f"Failed to delete instance {instance_id} and/or associated EIP.")


    else:
        print("Step 1: Skipping instance and EIP deletion as no instance_id was provided.")
        # If instance_id is None, we still might need to clean up tagged EIPs.
        if prefix and instance_base_name: # instance_base_name is used as base_name_for_eip_tag
            print(f"Attempting to clean up tagged EIPs for prefix {prefix}, base_name {instance_base_name} even without instance ID.")
            eip_cleanup_success = aws_ops.delete_if_found( # Assuming delete_if_found can handle instance_id=None
                ec2_client=ec2_client,
                instance_id=None, # Explicitly pass None
                prefix=prefix,
                base_name_for_eip_tag=instance_base_name
            )
            instance_and_eip_deleted = eip_cleanup_success # Overall success depends on EIP cleanup if no instance
            # Assuming aws_ops.delete_if_found returns a boolean
            if eip_cleanup_success:
                 eip_deletion_notes.append(f"Tagged EIP cleanup for prefix {prefix}, base_name {instance_base_name} processed.")
            else:
                 eip_deletion_notes.append(f"Tagged EIP cleanup for prefix {prefix}, base_name {instance_base_name} encountered issues.")

        else:
            print("Skipping EIP cleanup by tag as prefix or instance_base_name is missing.")
            instance_and_eip_deleted = True # Nothing to delete, so considered successful in this context.


    # 2. Delete Security Group
    sg_deleted = False
    sg_deletion_notes: List[str] = []
    derived_sg_name = None

    if not sg_group_name and prefix and instance_base_name:
        derived_sg_name = f"{prefix}_{instance_base_name}_sg"
        print(f"Derived security group name for deletion: {derived_sg_name}")
    
    actual_sg_name_to_delete = sg_group_name or derived_sg_name

    if actual_sg_name_to_delete and vpc_id:
        print(f"Step 2: Deleting security group '{actual_sg_name_to_delete}' in VPC '{vpc_id}'...")
        sg_deleted = aws_ops.delete_security_group_by_name(
            ec2_client=ec2_client,
            vpc_id=vpc_id,
            sg_group_name=actual_sg_name_to_delete
        )
        # Assuming aws_ops.delete_security_group_by_name returns a boolean
        if sg_deleted:
            sg_deletion_notes.append(f"Security group '{actual_sg_name_to_delete}' processed for deletion.")
        else:
            sg_deletion_notes.append(f"Failed to delete security group '{actual_sg_name_to_delete}' or it was not found/already deleted.")

    elif actual_sg_name_to_delete or vpc_id: # Only one of (name or vpc_id) is available and the other is missing
        msg = f"Warning: Skipping security group deletion. Both security group name ('{actual_sg_name_to_delete}') and vpc_id ('{vpc_id}') must be provided."
        print(msg)
        sg_deletion_notes.append(msg)
        sg_deleted = False # Cannot attempt deletion
    else: # Neither sg_group_name (explicit or derived) nor vpc_id is available
        print("Skipping security group deletion: Security group name (or elements to derive it) and/or vpc_id not provided.")
        sg_deleted = True # Nothing to delete, so considered successful in this context.

    # 3. Delete Subnet
    subnet_deleted = False
    subnet_deletion_notes: List[str] = []
    if subnet_id_to_delete:
        print(f"Step 3: Deleting subnet '{subnet_id_to_delete}'...")
        try:
            ec2_client.delete_subnet(SubnetId=subnet_id_to_delete)
            subnet_deleted = True
            subnet_deletion_notes.append(f"Subnet '{subnet_id_to_delete}' deleted successfully.")
            print(f"Subnet '{subnet_id_to_delete}' deleted successfully.")
        except Exception as e:
            # Check if the error is because the subnet is already gone
            if "does not exist" in str(e).lower() or "notfound" in str(e).lower():
                msg = f"Subnet '{subnet_id_to_delete}' not found, likely already deleted."
                print(msg)
                subnet_deletion_notes.append(msg)
                subnet_deleted = True # Considered success if it's already gone
            else:
                msg = f"Error deleting subnet '{subnet_id_to_delete}': {e}"
                print(msg)
                subnet_deletion_notes.append(msg)
                subnet_deleted = False
    else:
        print("Skipping subnet deletion: subnet_id_to_delete not provided.")
        subnet_deleted = True # Nothing to delete, so considered successful.

    # Consolidate results
    all_successful = instance_and_eip_deleted and sg_deleted and subnet_deleted
    result["status"] = "success" if all_successful else "failure"
    result["notes"].extend(instance_deletion_notes)
    result["notes"].extend(eip_deletion_notes)
    result["notes"].extend(sg_deletion_notes)
    result["notes"].extend(subnet_deletion_notes)

    # Add details of what was attempted/deleted
    result["details"]["instance_id_attempted"] = instance_id
    result["details"]["prefix_attempted"] = prefix
    result["details"]["region_id_attempted"] = current_region
    result["details"]["sg_name_attempted"] = actual_sg_name_to_delete
    result["details"]["vpc_id_attempted"] = vpc_id
    result["details"]["subnet_id_attempted"] = subnet_id_to_delete
    result["details"]["instance_and_eip_deleted"] = instance_and_eip_deleted
    result["details"]["sg_deleted"] = sg_deleted
    result["details"]["subnet_deleted"] = subnet_deleted


    if result["status"] == "success":
        print(f"delete_regional_egress for instance {instance_id} completed successfully.")
    else:
        print(f"delete_regional_egress for instance {instance_id} completed with issues.")
        
    return result


def get_aws_regions(only_opted_in_regions: bool = False) -> list:
    """
    Retrieves a list of AWS regions.
    Args:
        only_opted_in_regions: If True, returns only regions that are opted-in or opt-in-not-required.
                               Otherwise, returns all regions.
    """
    # Ensure credentials and region are loaded before making AWS calls
    # Use a common region like 'us-east-1' for describe_regions, or the configured default.
    # The region for describe_regions itself is not super critical as it lists all regions.
    # However, credentials must be valid.
    loaded_creds = refresh_aws_credentials_and_region(region_id='us-east-1') # Ensure .env is loaded, default to us-east-1 for this call
    
    if not loaded_creds.get("aws_access_key_id") or not loaded_creds.get("aws_secret_access_key"):
        print("Error: Cannot get AWS regions because AWS credentials (access key or secret key) are missing.")
        return [] # Return empty list indicating failure to get regions due to creds

    try:
        # Use the region that refresh_aws_credentials_and_region decided on (e.g. from .env or 'us-east-1')
        # for the client that will make the describe_regions call.
        client_region = loaded_creds.get("aws_default_region", "us-east-1")
        ec2_client = boto3.client('ec2', region_name=client_region)
        filters = []
        if only_opted_in_regions:
            filters.append({'Name': 'opt-in-status', 'Values': ['opted-in', 'opt-in-not-required']})
            print("Fetching only opted-in (or not-required-to-opt-in) AWS Regions...")
        else:
            print("Fetching all AWS Regions...")
            
        response = ec2_client.describe_regions(Filters=filters)
        regions = [region['RegionName'] for region in response['Regions']]
        
        if only_opted_in_regions:
            print(f"Opted-in AWS Regions: {regions}")
        else:
            print(f"All AWS Regions: {regions}")
        return regions
    except Exception as e:
        print(f"Error retrieving AWS regions: {e}")
        return []
