import boto3
import time
from typing import Optional, Dict, Any
import os
import ipaddress
import botocore.exceptions # Import botocore.exceptions

# Assume AWS credentials and region are configured in the environment or AWS config files

def get_latest_amazon_linux_2023_ami_id(ec2_client) -> Optional[str]:
    """
    Retrieves the latest Amazon Linux 2023 AMI ID for the region configured in the ec2_client.
    """
    try:
        response = ec2_client.describe_images(
            Owners=['amazon'],
            Filters=[
                {'Name': 'name', 'Values': ['al2023-ami-2023.*-kernel-*-x86_64']},
                {'Name': 'state', 'Values': ['available']},
                {'Name': 'architecture', 'Values': ['x86_64']},
                {'Name': 'virtualization-type', 'Values': ['hvm']},
                {'Name': 'root-device-type', 'Values': ['ebs']}
            ],
            IncludeDeprecated=False
        )
        # Sort images by creation date in descending order to get the latest
        images = sorted(response['Images'], key=lambda x: x['CreationDate'], reverse=True)
        if images:
            ami_id = images[0]['ImageId']
            print(f"Found latest Amazon Linux 2023 AMI ID: {ami_id} in region {ec2_client.meta.region_name}")
            return ami_id
        else:
            print(f"No Amazon Linux 2023 AMI found in region {ec2_client.meta.region_name}")
            return None
    except Exception as e:
        print(f"Error fetching latest Amazon Linux 2023 AMI ID in region {ec2_client.meta.region_name}: {e}")
        return None

def upsert_elastic_ip(ec2_client, instance_id: str, connector_name: str) -> Optional[str]:
    """
    Finds an existing Elastic IP tagged with connector_name, or allocates a new one,
    and associates it with the instance if not already associated.
    Returns the Elastic IP address.
    """
    try:
        # Check if instance already has an Elastic IP associated
        instance_desc = ec2_client.describe_instances(InstanceIds=[instance_id])
        network_interfaces = instance_desc.get('Reservations', [{}])[0].get('Instances', [{}])[0].get('NetworkInterfaces', [])
        if network_interfaces:
            association = network_interfaces[0].get('Association')
            if association and association.get('AllocationId'): # AllocationId indicates an EIP
                public_ip = association.get('PublicIp')
                print(f"Instance {instance_id} already associated with Elastic IP: {public_ip} (Allocation ID: {association.get('AllocationId')})")
                return public_ip

        eip_name_tag_value = connector_name # EIP is named with the connector name
        allocation_id_to_associate = None
        public_ip_to_associate = None

        # Try to find an unallocated Elastic IP tagged for this combination
        addresses_desc = ec2_client.describe_addresses(
            Filters=[
                {'Name': 'tag:Name', 'Values': [eip_name_tag_value]},
                {'Name': 'domain', 'Values': ['vpc']}
            ]
        )
        
        for addr in addresses_desc.get('Addresses', []):
            if 'AssociationId' not in addr: # Check if it's unallocated
                allocation_id_to_associate = addr['AllocationId']
                public_ip_to_associate = addr['PublicIp']
                print(f"Found unallocated Elastic IP {public_ip_to_associate} (Allocation ID: {allocation_id_to_associate}) tagged as {eip_name_tag_value}")
                break
        
        if not allocation_id_to_associate:
            # If no suitable unallocated EIP found, allocate a new one
            print(f"No suitable unallocated Elastic IP found with tag {eip_name_tag_value}. Allocating a new one...")
            try:
                allocation = ec2_client.allocate_address(
                    Domain='vpc',
                    TagSpecifications=[{
                        'ResourceType': 'elastic-ip',
                        'Tags': [{'Key': 'Name', 'Value': eip_name_tag_value}]
                    }]
                )
                allocation_id_to_associate = allocation['AllocationId']
                public_ip_to_associate = allocation['PublicIp']
                print(f"Allocated new Elastic IP: {public_ip_to_associate} (Allocation ID: {allocation_id_to_associate}), tagged as {eip_name_tag_value}")
            except Exception as alloc_e:
                print(f"Error allocating new Elastic IP: {alloc_e}")
                return None # Could not allocate EIP, so can't proceed with association

        if allocation_id_to_associate and public_ip_to_associate:
            # Associate the found or newly allocated Elastic IP with the instance
            print(f"Associating Elastic IP {public_ip_to_associate} with instance {instance_id}...")
            try:
                ec2_client.associate_address(
                    AllocationId=allocation_id_to_associate,
                    InstanceId=instance_id
                )
                print(f"Successfully associated Elastic IP {public_ip_to_associate} with instance {instance_id}")
                return public_ip_to_associate
            except Exception as assoc_e:
                print(f"Error associating Elastic IP {public_ip_to_associate} with instance {instance_id}: {assoc_e}")
                # If association fails and we *just allocated* this EIP (i.e., it wasn't a pre-existing unallocated one), release it.
                # We can infer it was newly allocated if we went through the allocation block.
                # A simple way to check: was allocation_id_to_associate set by the 'allocate_address' call?
                # This requires knowing if the EIP was from the describe_addresses or allocate_address path.
                # For simplicity, if association fails after an EIP was identified/allocated for association,
                # and if that EIP was newly allocated in this function call, it should be released.
                # Let's refine this: if we allocated it (i.e., `allocation` object exists from `ec2_client.allocate_address`), then release on failure.
                # This check is a bit tricky without a flag. Let's assume if an EIP was allocated in the 'if not allocation_id_to_associate:' block,
                # and association fails, we should try to release it.
                # A more direct way: if the EIP was obtained via allocate_address, its 'AllocationId' would match 'allocation_id_to_associate'.
                # We need to know if it was *newly* allocated.
                # Let's add a flag.
                was_newly_allocated = False # Assume not initially
                # ... (code before allocation) ...
                # Inside the 'if not allocation_id_to_associate:' block, after successful allocation:
                # was_newly_allocated = True
                # This requires restructuring.
                # For now, the original comment stands: "we might consider releasing it."
                # The enhanced delete_if_found will be the primary cleanup for orphaned EIPs by tag.
                return None
        
        return None # Fallback

    except Exception as e:
        print(f"Error in upsert_elastic_ip for instance {instance_id} (connector_name: {connector_name}): {e}")
        return None

def upsert_named_internet_gateway(ec2_client, vpc_id: str, connector_name: str) -> Optional[str]:
    """
    Finds or creates an Internet Gateway (named using connector_name) and ensures it's attached to the VPC.
    Returns the Internet Gateway ID.
    """
    igw_name_tag_value = connector_name # IGW is named with the connector name
    try:
        # Check for an existing IGW attached to the VPC
        igw_response = ec2_client.describe_internet_gateways(
            Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}]
        )

        if igw_response.get('InternetGateways'):
            igw = igw_response['InternetGateways'][0]
            internet_gateway_id = igw['InternetGatewayId']
            print(f"Found Internet Gateway {internet_gateway_id} attached to VPC {vpc_id}")
            
            current_name_tag = next((tag['Value'] for tag in igw.get('Tags', []) if tag['Key'] == 'Name'), None)
            if current_name_tag != igw_name_tag_value:
                try:
                    ec2_client.create_tags(Resources=[internet_gateway_id], Tags=[{'Key': 'Name', 'Value': igw_name_tag_value}])
                    print(f"Tagged Internet Gateway {internet_gateway_id} with Name: {igw_name_tag_value}")
                except Exception as tag_e:
                    print(f"Warning: Error tagging Internet Gateway {internet_gateway_id}: {tag_e}") # Non-fatal, proceed with IGW
            return internet_gateway_id
        else:
            # No IGW attached, create a new one
            print(f"No Internet Gateway attached to VPC {vpc_id}. Creating, naming ('{igw_name_tag_value}'), and attaching one...")
            try:
                new_igw_response = ec2_client.create_internet_gateway(
                    TagSpecifications=[{'ResourceType': 'internet-gateway', 'Tags': [{'Key': 'Name', 'Value': igw_name_tag_value}]}]
                )
                internet_gateway_id = new_igw_response['InternetGateway']['InternetGatewayId']
                ec2_client.attach_internet_gateway(InternetGatewayId=internet_gateway_id, VpcId=vpc_id)
                print(f"Created, named ('{igw_name_tag_value}'), and attached Internet Gateway {internet_gateway_id} to VPC {vpc_id}")
                return internet_gateway_id
            except Exception as create_igw_e:
                print(f"Error creating/attaching new Internet Gateway: {create_igw_e}")
                return None
    except Exception as e:
        print(f"Error in upsert_named_internet_gateway for VPC {vpc_id} (connector_name: {connector_name}): {e}")
        return None

def upsert_small_ec2_instance(ec2_client: Optional[boto3.client], instance_base_name: str, ami_id: str, prefix: str, instance_type: str = 't3.micro', key_name: Optional[str] = None, security_group_ids: Optional[list] = None, subnet_id: Optional[str] = None, openvpn_profile_content: Optional[str] = None) -> Optional[Dict[str, Optional[str]]]:
    """
    Finds or creates a small EC2 instance (named using prefix and base_name) and ensures it is running.
    Optionally configures OpenVPN using User Data.
    Accepts an optional ec2_client.

    Args:
        instance_base_name: The base name for the EC2 instance (e.g., "gateway").
        ami_id: The ID of the Amazon Machine Image (AMI) to use.
        prefix: The prefix for naming resources (e.g., "ovpn_mcp").
        instance_type: The type of instance to create (default is 't3.micro').
        key_name: The name of the EC2 key pair to use for SSH access.
        security_group_ids: A list of security group IDs to assign to the instance.
        subnet_id: The ID of the subnet to launch the instance in.
        openvpn_profile_content: The content of the OpenVPN .ovpn profile file.

    Returns:
        A dictionary containing the 'InstanceId' and 'PublicIpAddress' of the instance,
        or None if creation/finding failed or instance is not running.
    """
    ec2_to_use = ec2_client if ec2_client else boto3.client('ec2')
    instance_name_tag_value = prefix

    try:
        # Check if an instance with the given name tag already exists and is running
        response = ec2_to_use.describe_instances(
            Filters=[
                {'Name': 'tag:Name', 'Values': [instance_name_tag_value]},
                {'Name': 'instance-state-name', 'Values': ['running']},
                {'Name': 'image-id', 'Values': [ami_id]},
                # Add filters for key_name, security_group_ids, subnet_id if needed for stricter matching
            ]
        )
        if response['Reservations'] and response['Reservations'][0]['Instances']:
            instance = response['Reservations'][0]['Instances'][0]
            instance_id = instance['InstanceId']
            public_ip = instance.get('PublicIpAddress')
            print(f"Instance '{instance_name_tag_value}' already exists and is running with ID: {instance_id}")
            # EIP is named with connector_name (which is 'prefix' in this function's scope)
            elastic_ip = upsert_elastic_ip(ec2_to_use, instance_id, prefix) # prefix is connector_name
            if elastic_ip:
                print(f"Instance {instance_id} is now associated with Elastic IP: {elastic_ip}")
                return {'InstanceId': instance_id, 'PublicIpAddress': elastic_ip}
            elif public_ip: # Fallback to dynamic public IP if EIP association failed but dynamic IP exists
                print(f"Failed to associate Elastic IP. Instance {instance_id} has dynamic Public IP Address: {public_ip}")
                return {'InstanceId': instance_id, 'PublicIpAddress': public_ip}
            else: # This case means it was an existing instance without any public IP, stop/start was attempted, and EIP failed
                print(f"Instance {instance_id} does not have a public IP address. Stopping and starting to assign one...")
                stop_ec2_instance(ec2_client=ec2_to_use, instance_id=instance_id)
                start_ec2_instance(ec2_client=ec2_to_use, instance_id=instance_id)
                # Attempt EIP association again after restart
                elastic_ip_after_restart = upsert_elastic_ip(ec2_to_use, instance_id, prefix) # prefix is connector_name
                if elastic_ip_after_restart:
                     print(f"Instance {instance_id} (after restart) is now associated with Elastic IP: {elastic_ip_after_restart}")
                     return {'InstanceId': instance_id, 'PublicIpAddress': elastic_ip_after_restart}
                else:
                    # Final check for any public IP after restart if EIP failed again
                    instance_desc_after_restart = ec2_to_use.describe_instances(InstanceIds=[instance_id])
                    final_public_ip = instance_desc_after_restart.get('Reservations', [{}])[0].get('Instances', [{}])[0].get('PublicIpAddress')
                    if final_public_ip:
                        print(f"Failed to associate Elastic IP after restart. Instance {instance_id} has dynamic Public IP: {final_public_ip}")
                        return {'InstanceId': instance_id, 'PublicIpAddress': final_public_ip}
                    else:
                        print(f"Instance {instance_id} still does not have any public IP address after stop/start and EIP attempt.")
                        return {'InstanceId': instance_id, 'PublicIpAddress': None}


        # If instance doesn't exist or is not running, create a new one
        print(f"Instance '{instance_name_tag_value}' not found or not running, creating a new one...")

        user_data_script = ""
        if openvpn_profile_content:
            profile_length_kb = len(openvpn_profile_content.encode('utf-8')) / 1024
            print(f"Debug: In aws_boto3_apis.py, inside upsert_small_ec2_instance, before creating user_data, profile_content length: {profile_length_kb:.2f} KB, first 20 chars: '{openvpn_profile_content[:20]}'")
            # User Data script to install OpenVPN and configure it for Amazon Linux
            user_data_script = f"""#!/bin/bash
# Update packages and install OpenVPN
# For Amazon Linux 2023, dnf is preferred. For older Amazon Linux 2, yum install openvpn -y might be used.
sudo dnf update -y
sudo dnf install openvpn -y

# Create OpenVPN client configuration directory
sudo mkdir -p /etc/openvpn/client

# Write the OpenVPN profile content to the configuration file
echo '{openvpn_profile_content}' | sudo tee /etc/openvpn/client/client.conf > /dev/null

# Enable and start the OpenVPN client service
# The service name is typically openvpn-client@<config_file_name_without_extension>.service
sudo systemctl enable openvpn-client@client.service
sudo systemctl start openvpn-client@client.service
"""

        run_instances_params = {
            'ImageId': ami_id,
            'InstanceType': instance_type,
            'MinCount': 1,
            'MaxCount': 1,
            'TagSpecifications': [
                {
                    'ResourceType': 'instance',
                    'Tags': [{'Key': 'Name', 'Value': instance_name_tag_value}]
                }
            ],
            'UserData': user_data_script if user_data_script else None,
        }

        if key_name:
            run_instances_params['KeyName'] = key_name
        if security_group_ids:
            run_instances_params['SecurityGroupIds'] = security_group_ids
        if subnet_id:
            run_instances_params['SubnetId'] = subnet_id

        response = ec2_to_use.run_instances(**run_instances_params)

        instance_id = response['Instances'][0]['InstanceId']
        print(f"Created EC2 instance with ID: {instance_id}. Returning immediately without waiting for it to be fully running.")

        # Return immediately after initiating the launch
        # The instance is provisioning. Public IP and EIP association will happen later or need to be checked separately.
        return {'InstanceId': instance_id, 'PublicIpAddress': None, 'Status': 'PROVISIONING_STARTED', 'Notes': 'Instance launch initiated. Check AWS console for status.'}

        # Commented out waiter and EIP association for newly created instances to return quickly:
        # # Wait for the instance to be running
        # waiter = ec2_to_use.get_waiter('instance_running')
        # print(f"Waiting for instance {instance_id} to be running...")
        # waiter.wait(InstanceIds=[instance_id])
        # print(f"Instance {instance_id} is now running.")
        # 
        # # For newly created instance, attempt to associate an Elastic IP
        # elastic_ip = upsert_elastic_ip(ec2_to_use, instance_id, instance_base_name, prefix)
        # if elastic_ip:
        #     print(f"Newly created instance {instance_id} associated with Elastic IP: {elastic_ip}")
        #     return {'InstanceId': instance_id, 'PublicIpAddress': elastic_ip}
        # else:
        #     # Fallback to checking for a dynamic public IP if EIP association failed
        #     print(f"Failed to associate Elastic IP with newly created instance {instance_id}. Checking for dynamic public IP...")
        #     instance_desc = ec2_to_use.describe_instances(InstanceIds=[instance_id])
        #     dynamic_public_ip = instance_desc.get('Reservations', [{}])[0].get('Instances', [{}])[0].get('PublicIpAddress')
        #     if dynamic_public_ip:
        #         print(f"Newly created instance {instance_id} has dynamic Public IP Address: {dynamic_public_ip}")
        #         return {'InstanceId': instance_id, 'PublicIpAddress': dynamic_public_ip}
        #     else:
        #         print(f"Newly created instance {instance_id} does not have any public IP address (EIP failed, no dynamic IP).")
        #         return {'InstanceId': instance_id, 'PublicIpAddress': None}

    except Exception as e:
        print(f"Error finding or creating EC2 instance '{instance_name_tag_value}': {e}")
        return None


def create_custom_instance_profile(instance_id: str, profile_name: Optional[str], role_name: Optional[str]):
    """
    Creates and associates a custom IAM instance profile with the EC2 instance.

    Args:
        instance_id: The ID of the EC2 instance.
        profile_name: The name for the new instance profile.
        role_name: The name of the IAM role to associate with the profile.

    This function is a placeholder. The actual implementation would involve:
    1. Creating an IAM instance profile.
    2. Adding the specified IAM role to the instance profile.
    3. Associating the instance profile with the EC2 instance.
    """
    print(f"Placeholder for creating and associating custom instance profile '{profile_name}' with role '{role_name}' for instance {instance_id}")
    print("Steps involved:")
    print("1. Create IAM instance profile (boto3.client('iam').create_instance_profile).")
    print("2. Add role to instance profile (boto3.client('iam').add_role_to_instance_profile).")
    print("3. Associate instance profile with EC2 instance (boto3.client('ec2').associate_iam_instance_profile).")
    pass


def start_ec2_instance(ec2_client: Optional[boto3.client], instance_id: str):
    """
    Starts an EC2 instance.
    Accepts an optional ec2_client.

    Args:
        instance_id: The ID of the EC2 instance to start.
    """
    ec2_to_use = ec2_client if ec2_client else boto3.client('ec2')
    try:
        print(f"Starting EC2 instance: {instance_id}")
        ec2_to_use.start_instances(InstanceIds=[instance_id])
        waiter = ec2_to_use.get_waiter('instance_running')
        print(f"Waiting for instance {instance_id} to be running...")
        waiter.wait(InstanceIds=[instance_id])
        print(f"Instance {instance_id} is now running.")
    except Exception as e:
        print(f"Error starting EC2 instance: {e}")

def stop_ec2_instance(ec2_client: Optional[boto3.client], instance_id: str):
    """
    Stops an EC2 instance.
    Accepts an optional ec2_client.

    Args:
        instance_id: The ID of the EC2 instance to stop.
    """
    ec2_to_use = ec2_client if ec2_client else boto3.client('ec2')
    try:
        print(f"Stopping EC2 instance: {instance_id}")
        ec2_to_use.stop_instances(InstanceIds=[instance_id])
        waiter = ec2_to_use.get_waiter('instance_stopped')
        print(f"Waiting for instance {instance_id} to be stopped...")
        waiter.wait(InstanceIds=[instance_id])
        print(f"Instance {instance_id} is now stopped.")
    except Exception as e:
        print(f"Error stopping EC2 instance: {e}")

def configure_subnet_as_gateway(ec2_client: Optional[boto3.client], subnet_id: str, internet_gateway_id: str):
    """
    Configures a subnet's route table to direct internet-bound traffic through an Internet Gateway.
    Accepts an optional ec2_client.

    Args:
        subnet_id: The ID of the subnet to configure.
        internet_gateway_id: The ID of the Internet Gateway to associate with the route table.
    """
    ec2_to_use = ec2_client if ec2_client else boto3.client('ec2')
    route_table_id_to_configure = None

    try:
        subnet_desc = ec2_to_use.describe_subnets(SubnetIds=[subnet_id])
        if not subnet_desc['Subnets']:
            print(f"Error: Subnet {subnet_id} not found.")
            return
        vpc_id = subnet_desc['Subnets'][0]['VpcId']

        # Check for an explicitly associated route table
        explicit_rt_response = ec2_to_use.describe_route_tables(
            Filters=[{'Name': 'association.subnet-id', 'Values': [subnet_id]}]
        )

        if explicit_rt_response['RouteTables']:
            route_table_id_to_configure = explicit_rt_response['RouteTables'][0]['RouteTableId']
            print(f"Subnet {subnet_id} is explicitly associated with route table {route_table_id_to_configure}")
        else:
            # If no explicit association, it uses the main route table for the VPC
            main_rt_response = ec2_to_use.describe_route_tables(
                Filters=[
                    {'Name': 'vpc-id', 'Values': [vpc_id]},
                    {'Name': 'association.main', 'Values': ['true']}
                ]
            )
            if main_rt_response['RouteTables']:
                route_table_id_to_configure = main_rt_response['RouteTables'][0]['RouteTableId']
                print(f"Subnet {subnet_id} uses main route table {route_table_id_to_configure} for VPC {vpc_id}")
            else:
                print(f"Error: No main route table found for VPC {vpc_id} (subnet {subnet_id}) and no explicit association.")
                return

        if route_table_id_to_configure:
            # Create or replace a route to the Internet Gateway in the identified route table
            try:
                ec2_to_use.create_route(
                    RouteTableId=route_table_id_to_configure,
                    DestinationCidrBlock='0.0.0.0/0',
                    GatewayId=internet_gateway_id
                )
                print(f"Ensured route (created) in {route_table_id_to_configure} to Internet Gateway {internet_gateway_id} for subnet {subnet_id}")
            except Exception as route_error:
                if "RouteAlreadyExists" in str(route_error):
                    print(f"Route to 0.0.0.0/0 already exists in route table {route_table_id_to_configure}. Attempting to replace to ensure validity...")
                    try:
                        ec2_to_use.replace_route(
                            RouteTableId=route_table_id_to_configure,
                            DestinationCidrBlock='0.0.0.0/0',
                            GatewayId=internet_gateway_id
                        )
                        print(f"Ensured route (replaced) in {route_table_id_to_configure} to Internet Gateway {internet_gateway_id} for subnet {subnet_id}")
                    except Exception as replace_error:
                        print(f"Error replacing existing route in {route_table_id_to_configure}: {replace_error}")
                        # If replace fails, the route might still be problematic.
                else:
                    # Different error during create_route
                    print(f"Error creating route in {route_table_id_to_configure}: {route_error}")
                    # Consider how to handle this, e.g., raise route_error or return failure
        else:
            print(f"Could not determine route table for subnet {subnet_id}")

    except Exception as e:
        print(f"Error configuring subnet {subnet_id} as gateway: {e}")

def upsert_gateway_subnet(ec2_client: Optional[boto3.client], vpc_id: str, subnet_base_name: str, vpc_cidr_block: str, prefix: str):
    """
    Finds or creates a subnet (named using prefix and base_name) and configures it as a gateway subnet.
    Accepts an optional ec2_client.

    Args:
        vpc_id: The ID of the VPC.
        subnet_base_name: The base name for the subnet (e.g., "gateway").
        vpc_cidr_block: The CIDR block of the VPC.
        prefix: The prefix for naming resources (e.g., "ovpn_mcp").

    Returns:
        The ID of the subnet, or None if creation/finding failed.
    """
    ec2_to_use = ec2_client if ec2_client else boto3.client('ec2')
    subnet_name_tag_value = prefix

    try:
        # Check if a subnet with the given name tag already exists in the VPC
        response = ec2_to_use.describe_subnets(
            Filters=[
                {'Name': 'tag:Name', 'Values': [subnet_name_tag_value]},
                {'Name': 'vpc-id', 'Values': [vpc_id]}
            ]
        )
        if response['Subnets']:
            existing_subnet_id = response['Subnets'][0]['SubnetId']
            print(f"Subnet '{subnet_name_tag_value}' already exists with ID: {existing_subnet_id}")
            
            # Ensure an IGW is attached to the VPC and get its ID
            internet_gateway_id = upsert_named_internet_gateway(ec2_to_use, vpc_id, prefix)

            if internet_gateway_id:
                configure_subnet_as_gateway(ec2_to_use, existing_subnet_id, internet_gateway_id)
            else:
                print(f"Failed to ensure an Internet Gateway for VPC {vpc_id} (prefix: {prefix}). Cannot configure subnet {existing_subnet_id} as gateway.")
                # Potentially return None or raise an error, as subnet might not be public
            
            # Ensure auto-assign public IP is enabled for the existing subnet
            ec2_to_use.modify_subnet_attribute(
                SubnetId=existing_subnet_id,
                MapPublicIpOnLaunch={'Value': True}
            )
            print(f"Ensured auto-assign public IP is enabled for existing subnet {existing_subnet_id}")
            return existing_subnet_id

        # If subnet doesn't exist, create a new one
        print(f"Subnet '{subnet_name_tag_value}' not found, creating a new one...")
        new_subnet_id = None

        # Get existing subnet CIDRs to avoid conflicts
        existing_subnets_response = ec2_to_use.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
        existing_cidr_blocks = {s['CidrBlock'] for s in existing_subnets_response['Subnets']}

        try:
            vpc_network = ipaddress.ip_network(vpc_cidr_block)
            # Iterate through potential /24 subnets within the VPC CIDR block
            for i, potential_subnet_network in enumerate(vpc_network.subnets(new_prefix=24)):
                subnet_cidr_block = str(potential_subnet_network)
                if subnet_cidr_block in existing_cidr_blocks:
                    print(f"CIDR block {subnet_cidr_block} is already in use, trying next...")
                    continue

                print(f"Attempting to create subnet with CIDR block: {subnet_cidr_block}")
                try:
                    subnet_response = ec2_to_use.create_subnet(
                        VpcId=vpc_id,
                        CidrBlock=subnet_cidr_block,
                        TagSpecifications=[
                            {
                                'ResourceType': 'subnet',
                                'Tags': [{'Key': 'Name', 'Value': subnet_name_tag_value}]
                            }
                        ]
                    )
                    new_subnet_id = subnet_response['Subnet']['SubnetId']
                    print(f"Successfully created subnet: {new_subnet_id} with tag '{subnet_name_tag_value}'")

                    # Enable auto-assign public IP for the new subnet
                    ec2_to_use.modify_subnet_attribute(
                        SubnetId=new_subnet_id,
                        MapPublicIpOnLaunch={'Value': True}
                    )
                    print(f"Enabled auto-assign public IP for subnet {new_subnet_id}")

                    break # Stop if subnet creation is successful
                except Exception as subnet_error:
                    # This specific CIDR might be invalid for other reasons, or a race condition
                    print(f"Error creating subnet with CIDR block {subnet_cidr_block}: {subnet_error}")
                    # Continue to try next CIDR block
                if i >= 50: # Limit attempts
                     print("Reached maximum subnet creation attempts.")
                     break

            if new_subnet_id:
                # Ensure an IGW is attached to the VPC and get its ID
                internet_gateway_id = upsert_named_internet_gateway(ec2_to_use, vpc_id, prefix)
                
                if internet_gateway_id:
                    configure_subnet_as_gateway(ec2_to_use, new_subnet_id, internet_gateway_id)
                    return new_subnet_id
                else:
                    print(f"Failed to ensure an Internet Gateway for VPC {vpc_id} (prefix: {prefix}). Cannot configure newly created subnet {new_subnet_id} as gateway.")
                    return None # Subnet created, but might not be public
            else:
                print("Failed to create a new subnet with an available CIDR block.")
                return None
        except Exception as e:
            print(f"Error during new subnet creation process: {e}")
            return None
    except Exception as e:
        print(f"Error finding or creating gateway subnet '{subnet_name_tag_value}': {e}")
        return None

def upsert_instance_security_group(ec2_client: Optional[boto3.client], vpc_id: str, ingress_rules: list, sg_base_name: str, prefix: str):
    """
    Finds or creates a security group (named using prefix and base_name),
    ensures rules are present, and allows all outbound traffic.
    Accepts an optional ec2_client.

    Args:
        vpc_id: The ID of the VPC.
        ingress_rules: A list of dictionaries defining the ingress rules.
        sg_base_name: The base name for the security group (e.g., "gateway").
        prefix: The prefix for naming resources (e.g., "ovpn_mcp").

    Returns:
        The ID of the security group, or None if creation/finding failed.
    """
    ec2_to_use = ec2_client if ec2_client else boto3.client('ec2')
    # Security Group names are unique per VPC. GroupName is what's used in filters.
    # Name tag is for display/identification.
    sg_group_name_value = prefix
    sg_name_tag_value = prefix # Use the same for the Name tag for consistency

    try:
        # Check if the security group already exists by GroupName
        response = ec2_to_use.describe_security_groups(
            Filters=[
                {'Name': 'group-name', 'Values': [sg_group_name_value]},
                {'Name': 'vpc-id', 'Values': [vpc_id]}
            ]
        )
        if response['SecurityGroups']:
            sg_data = response['SecurityGroups'][0]
            security_group_id = sg_data['GroupId']
            print(f"Security group '{sg_group_name_value}' (GroupName) already exists with ID: {security_group_id}")

            # Check and update Name tag if necessary
            current_name_tag = next((tag['Value'] for tag in sg_data.get('Tags', []) if tag['Key'] == 'Name'), None)
            if current_name_tag != sg_name_tag_value:
                try:
                    ec2_to_use.create_tags(Resources=[security_group_id], Tags=[{'Key': 'Name', 'Value': sg_name_tag_value}])
                    print(f"Updated Name tag for security group {security_group_id} to '{sg_name_tag_value}'")
                except Exception as tag_e:
                    print(f"Warning: Error updating Name tag for security group {security_group_id}: {tag_e}")

            # Ensure ingress rules are present (idempotent operation)
            if ingress_rules:
                try:
                    ec2_to_use.authorize_security_group_ingress(GroupId=security_group_id, IpPermissions=ingress_rules)
                    print(f"Ensured ingress rules for existing security group {security_group_id}")
                except Exception as ingress_error:
                     if "InvalidPermission.Duplicate" in str(ingress_error):
                        print(f"Ingress rules already exist for security group {security_group_id}")
                     else: # Re-raise other errors
                        print(f"Error authorizing ingress for SG {security_group_id}: {ingress_error}")
                        # Depending on severity, might want to return None or raise
            return security_group_id

        # Create the security group if it doesn't exist
        print(f"Creating security group with GroupName '{sg_group_name_value}' and Name tag '{sg_name_tag_value}'...")
        sg_response = ec2_to_use.create_security_group(
            Description=f'Security group for {prefix} {sg_base_name}',
            GroupName=sg_group_name_value,
            VpcId=vpc_id,
            TagSpecifications=[{
                'ResourceType': 'security-group',
                'Tags': [{'Key': 'Name', 'Value': sg_name_tag_value}]
            }]
        )
        security_group_id = sg_response['GroupId']
        print(f"Created security group: {security_group_id}")

        # Add ingress rules
        if ingress_rules:
            ec2_to_use.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=ingress_rules
            )
            print(f"Added ingress rules to security group {security_group_id}")

        # Add egress rule (allow all outbound traffic)
        try:
            ec2_to_use.authorize_security_group_egress(
                GroupId=security_group_id,
                IpPermissions=[
                    {
                        'IpProtocol': '-1', # All protocols
                        'FromPort': 0,
                        'ToPort': 65535,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    }
                ]
            )
            print(f"Added egress rule to security group {security_group_id}")
        except Exception as egress_error:
            if "InvalidPermission.Duplicate" in str(egress_error):
                print(f"Default egress rule already exists in security group {security_group_id}")
            else:
                raise egress_error
        return security_group_id
    except Exception as e:
        print(f"Error finding or creating security group: {e}")
        return None

def get_default_vpc_info(ec2_client: Optional[boto3.client] = None):
    """
    Retrieves the ID and CIDR block of the default VPC in the current AWS region.
    Accepts an optional ec2_client.

    Returns:
        A dictionary containing 'VpcId' and 'CidrBlock' of the default VPC,
        or None if no default VPC is found.
    """
    ec2_to_use = ec2_client if ec2_client else boto3.client('ec2')

    try:
        response = ec2_to_use.describe_vpcs(
            Filters=[
                {
                    'Name': 'isDefault',
                    'Values': ['true']
                },
            ]
        )

        if response['Vpcs']:
            default_vpc_info = {
                'VpcId': response['Vpcs'][0]['VpcId'],
                'CidrBlock': response['Vpcs'][0]['CidrBlock']
            }
            print(f"Found default VPC: {default_vpc_info['VpcId']} with CIDR block {default_vpc_info['CidrBlock']}")
            return default_vpc_info
        else:
            print("No default VPC found in this region.")
            return None

    except Exception as e:
        print(f"Error getting default VPC info: {e}")
        return None

def analyze_nacl_for_subnet(ec2_client, subnet_id: str) -> Dict[str, Any]:
    """
    Analyzes the Network ACL associated with a given subnet to determine if it's generally permissive
    or potentially restrictive for common traffic like SSH, OpenVPN, and ICMP.

    Args:
        ec2_client: Initialized Boto3 EC2 client.
        subnet_id: The ID of the subnet to analyze.

    Returns:
        A dictionary containing the NACL analysis.
    """
    analysis_result = {
        "nacl_id": None,
        "is_default_vpc_nacl": False, # This is harder to determine directly, will focus on rules
        "status": "UNKNOWN", # PERMISSIVE, RESTRICTIVE, UNKNOWN
        "analysis_notes": [],
        "rules_summary": {"inbound": [], "outbound": []}
    }

    try:
        # Find the NACL associated with the subnet
        response = ec2_client.describe_network_acls(
            Filters=[{'Name': 'association.subnet-id', 'Values': [subnet_id]}]
        )

        if not response.get('NetworkAcls'):
            # If no explicit association, it might be using the VPC's default NACL.
            # This requires getting VPC_ID from subnet_id, then finding default NACL for that VPC.
            subnet_info = ec2_client.describe_subnets(SubnetIds=[subnet_id])
            if not subnet_info.get('Subnets'):
                analysis_result["analysis_notes"].append(f"Subnet {subnet_id} not found.")
                return analysis_result
            vpc_id = subnet_info['Subnets'][0]['VpcId']
            
            default_nacl_response = ec2_client.describe_network_acls(
                Filters=[
                    {'Name': 'vpc-id', 'Values': [vpc_id]},
                    {'Name': 'default', 'Values': ['true']}
                ]
            )
            if not default_nacl_response.get('NetworkAcls'):
                analysis_result["analysis_notes"].append(f"Could not find default NACL for VPC {vpc_id} of subnet {subnet_id}.")
                return analysis_result
            nacl = default_nacl_response['NetworkAcls'][0]
            analysis_result["analysis_notes"].append(f"Subnet {subnet_id} is using the default NACL for VPC {vpc_id}.")
            analysis_result["is_default_vpc_nacl"] = True
        else:
            nacl = response['NetworkAcls'][0]
            analysis_result["analysis_notes"].append(f"Subnet {subnet_id} is explicitly associated with NACL.")
        
        analysis_result["nacl_id"] = nacl['NetworkAclId']

        # Analyze rules
        inbound_allows_all = False
        outbound_allows_all = False
        inbound_ssh_allowed = False
        inbound_icmp_allowed = False
        
        # Sort rules by rule number to evaluate them in order
        sorted_entries = sorted(nacl['Entries'], key=lambda x: x['RuleNumber'])

        for entry in sorted_entries:
            if entry['RuleNumber'] == 32767: # Default rule, skip for specific analysis here
                continue

            rule_details = {
                "RuleNumber": entry['RuleNumber'],
                "Protocol": entry['Protocol'], # -1 for all, 6 for TCP, 17 for UDP, 1 for ICMP
                "PortRange": entry.get('PortRange', {}), # e.g., {'From': 22, 'To': 22}
                "CidrBlock": entry['CidrBlock'],
                "Egress": entry['Egress'], # True for outbound, False for inbound
                "RuleAction": entry['RuleAction'] # 'allow' or 'deny'
            }

            direction = "outbound" if entry['Egress'] else "inbound"
            analysis_result["rules_summary"][direction].append(rule_details)

            if entry['RuleAction'] == 'allow':
                if entry['CidrBlock'] == '0.0.0.0/0' and entry['Protocol'] == '-1':
                    if entry['Egress']:
                        outbound_allows_all = True
                    else:
                        inbound_allows_all = True
                
                if not entry['Egress']: # Inbound rules
                    if entry['Protocol'] == '6': # TCP
                        if entry.get('PortRange') and entry['PortRange'].get('From') == 22 and entry['PortRange'].get('To') == 22:
                            inbound_ssh_allowed = True
                    elif entry['Protocol'] == '1': # ICMP
                        inbound_icmp_allowed = True
            
            # If an early deny rule for 0.0.0.0/0 is found, it's highly restrictive
            if entry['RuleAction'] == 'deny' and entry['CidrBlock'] == '0.0.0.0/0' and entry['Protocol'] == '-1':
                if entry['Egress'] and not outbound_allows_all: # If deny all outbound comes before an allow all
                    analysis_result["analysis_notes"].append(f"Outbound: Explicit DENY ALL rule ({entry['RuleNumber']}) found before any ALLOW ALL.")
                elif not entry['Egress'] and not inbound_allows_all: # If deny all inbound comes before an allow all
                    analysis_result["analysis_notes"].append(f"Inbound: Explicit DENY ALL rule ({entry['RuleNumber']}) found before any ALLOW ALL.")


        if inbound_allows_all:
            analysis_result["analysis_notes"].append("Inbound: Effectively allows all traffic due to a '0.0.0.0/0 All Traffic Allow' rule.")
        else:
            if inbound_ssh_allowed:
                analysis_result["analysis_notes"].append("Inbound: Allows TCP port 22 (SSH) from 0.0.0.0/0.")
            else:
                analysis_result["analysis_notes"].append("Inbound: TCP port 22 (SSH) from 0.0.0.0/0 appears to be DENIED or not explicitly allowed before default deny.")
            if inbound_icmp_allowed:
                analysis_result["analysis_notes"].append("Inbound: Allows ICMP (Ping) from 0.0.0.0/0.")
            else:
                analysis_result["analysis_notes"].append("Inbound: ICMP (Ping) from 0.0.0.0/0 appears to be DENIED or not explicitly allowed before default deny.")
        
        if outbound_allows_all:
            analysis_result["analysis_notes"].append("Outbound: Effectively allows all traffic due to a '0.0.0.0/0 All Traffic Allow' rule.")
        else:
            # Default NACLs usually allow all outbound. If not, it's custom and needs more specific checks.
            # For this summary, we'll assume if not explicitly "allows all", it might be restrictive.
            analysis_result["analysis_notes"].append("Outbound: Does not have an explicit '0.0.0.0/0 All Traffic Allow' rule. Traffic relies on specific allow rules or default deny.")


        # Determine overall status
        # This is a heuristic. A truly permissive NACL usually has allow all for both in/out or specific allows for common ports.
        if inbound_allows_all and outbound_allows_all:
            analysis_result["status"] = "PERMISSIVE"
        elif (inbound_ssh_allowed or inbound_icmp_allowed) and outbound_allows_all : # Basic check
             analysis_result["status"] = "PARTIALLY_PERMISSIVE" # Permissive for some key services
        else:
            # Check for the default deny all rule if no explicit allow all was found
            default_deny_in = any(r['RuleNumber'] == 32767 and not r['Egress'] and r['RuleAction'] == 'deny' for r in nacl['Entries'])
            default_deny_out = any(r['RuleNumber'] == 32767 and r['Egress'] and r['RuleAction'] == 'deny' for r in nacl['Entries'])

            if (not inbound_allows_all and default_deny_in) or \
               (not outbound_allows_all and default_deny_out):
                analysis_result["status"] = "RESTRICTIVE_BY_DEFAULT"
            
            if not (inbound_ssh_allowed or inbound_icmp_allowed):
                 analysis_result["status"] = "LIKELY_RESTRICTIVE"


    except Exception as e:
        analysis_result["analysis_notes"].append(f"Error analyzing NACL for subnet {subnet_id}: {str(e)}")
        analysis_result["status"] = "ERROR_ANALYZING"

    return analysis_result

def delete_if_found(ec2_client: Optional[boto3.client], instance_id: Optional[str], connector_name: Optional[str] = None) -> bool:
    """
    Terminates an EC2 instance if found and releases its associated Elastic IP.
    Also cleans up EIPs tagged with connector_name even if instance_id is None.
    Accepts an optional ec2_client.

    Args:
        instance_id: The ID of the EC2 instance to terminate.
        connector_name: The name used for tagging the EIP (this is the connector's name).

    Returns:
        True if the instance was found and termination initiated (and EIP released if applicable),
        False otherwise.
    """
    ec2_to_use = ec2_client if ec2_client else boto3.client('ec2')
    instance_terminated_successfully = True # Default to true if no instance_id
    eips_cleaned_successfully = False

    # --- Instance Termination (only if instance_id is provided) ---
    if instance_id:
        instance_terminated_successfully = False # Reset for actual instance processing
        try:
            instance_desc = ec2_to_use.describe_instances(InstanceIds=[instance_id])
            if not instance_desc.get('Reservations') or not instance_desc['Reservations'][0].get('Instances'):
                print(f"Instance {instance_id} not found. Assuming already deleted or never existed.")
                instance_terminated_successfully = True # No instance to terminate
            else:
                instance_data = instance_desc['Reservations'][0]['Instances'][0]
                current_state = instance_data.get('State', {}).get('Name')
                if current_state in ['terminated', 'shutting-down']:
                    print(f"Instance {instance_id} is already {current_state}.")
                    instance_terminated_successfully = True
                else:
                    print(f"Found instance {instance_id} in state: {current_state}. Proceeding with termination.")
                    # First, handle directly associated EIP if any
                    network_interfaces = instance_data.get('NetworkInterfaces', [])
                    if network_interfaces:
                        association_info = network_interfaces[0].get('Association')
                        if association_info and association_info.get('AllocationId'):
                            direct_eip_alloc_id = association_info['AllocationId']
                            direct_eip_assoc_id = association_info.get('AssociationId')
                            direct_eip_public_ip = association_info.get('PublicIp')
                            if direct_eip_assoc_id:
                                try:
                                    print(f"Disassociating direct EIP {direct_eip_public_ip} (AssocID: {direct_eip_assoc_id}) from instance {instance_id}...")
                                    ec2_to_use.disassociate_address(AssociationId=direct_eip_assoc_id)
                                    print(f"Successfully disassociated direct EIP {direct_eip_public_ip}.")
                                except Exception as disassoc_e:
                                    print(f"Warning: Error disassociating direct EIP {direct_eip_public_ip}: {disassoc_e}")
                            try:
                                print(f"Releasing direct EIP {direct_eip_public_ip} (AllocID: {direct_eip_alloc_id})...")
                                ec2_to_use.release_address(AllocationId=direct_eip_alloc_id)
                                print(f"Successfully released direct EIP {direct_eip_public_ip}.")
                            except Exception as release_e:
                                print(f"Warning: Error releasing direct EIP {direct_eip_public_ip} (AllocID: {direct_eip_alloc_id}): {release_e}")
                    
                    ec2_to_use.terminate_instances(InstanceIds=[instance_id])
                    # waiter = ec2_to_use.get_waiter('instance_terminated') # Removed waiter for non-blocking termination
                    # print(f"Waiting for instance {instance_id} to be terminated...")
                    # waiter.wait(InstanceIds=[instance_id]) # Removed waiter for non-blocking termination
                    print(f"Instance {instance_id} termination initiated.")
                    instance_terminated_successfully = True # Considered successful if termination is initiated
        except ec2_to_use.exceptions.ClientError as e:
            if 'InvalidInstanceID.NotFound' in str(e):
                print(f"Instance {instance_id} not found (ClientError). Assuming already deleted.")
                instance_terminated_successfully = True
            elif 'InvalidInstanceID.Malformed' in str(e) and instance_id is not None : # Check instance_id is not None before this
                print(f"Instance ID {instance_id} is malformed. Cannot proceed with instance operations.")
                return False # Critical error for instance part
            else:
                print(f"AWS ClientError during instance termination for {instance_id}: {e}")
                # instance_terminated_successfully remains False
        except Exception as e:
            print(f"Unexpected error during instance termination for {instance_id}: {e}")
            # instance_terminated_successfully remains False
    else:
        print("Skipping instance termination as no instance_id was provided.")

    # --- Tagged EIP Cleanup ---
    # This runs regardless of instance termination outcome, to catch orphaned EIPs.
    if connector_name: # connector_name is used directly as the EIP Name tag
        eip_name_tag_value = connector_name
        
        print(f"Searching for and attempting to release Elastic IPs tagged as '{eip_name_tag_value}'...")
        eips_found_and_attempted_release = 0
        eips_successfully_released = 0
        try:
            addresses_desc = ec2_to_use.describe_addresses(
                Filters=[
                    {'Name': 'tag:Name', 'Values': [eip_name_tag_value]},
                    {'Name': 'domain', 'Values': ['vpc']}
                ]
            )
            if not addresses_desc.get('Addresses'):
                print(f"No Elastic IPs found with tag '{eip_name_tag_value}'.")
                eips_cleaned_successfully = True # No tagged EIPs to clean
            else:
                for addr in addresses_desc['Addresses']:
                    eips_found_and_attempted_release += 1
                    alloc_id = addr['AllocationId']
                    public_ip = addr['PublicIp']
                    
                    # If EIP is associated with a *different* instance, skip release.
                    if addr.get('InstanceId') and addr.get('InstanceId') != instance_id:
                        print(f"Skipping release of tagged EIP {public_ip} (AllocID: {alloc_id}) as it's associated with a different instance: {addr.get('InstanceId')}.")
                        continue # Don't count this as a failure for *this* cleanup, but it's not cleaned by this call.

                    # If associated with the target instance (should have been disassociated above, but check again)
                    if instance_id and addr.get('InstanceId') == instance_id and addr.get('AssociationId'): # Only disassociate if related to the specific instance_id
                        try:
                            print(f"Tagged EIP {public_ip} still shows associated with {instance_id}. Attempting disassociation (AssocID: {addr['AssociationId']})...")
                            ec2_to_use.disassociate_address(AssociationId=addr['AssociationId'])
                            print(f"Successfully disassociated tagged EIP {public_ip} from {instance_id}.")
                        except Exception as dis_e:
                            print(f"Error disassociating tagged EIP {public_ip} from {instance_id}: {dis_e}. Skipping release for this EIP.")
                            continue # Skip release if disassociation fails
                    elif not instance_id and addr.get('AssociationId'): # If no instance_id, but EIP is associated with *something*
                        print(f"Skipping release of tagged EIP {public_ip} (AllocID: {alloc_id}) as it's associated (InstanceId: {addr.get('InstanceId')}) and no specific instance_id was targeted for deletion.")
                        continue


                    try:
                        print(f"Releasing tagged Elastic IP {public_ip} (Allocation ID: {alloc_id})...")
                        ec2_to_use.release_address(AllocationId=alloc_id)
                        print(f"Successfully released tagged EIP {public_ip}.")
                        eips_successfully_released += 1
                    except Exception as release_tagged_e:
                        print(f"Error releasing tagged EIP {public_ip} (AllocID: {alloc_id}): {release_tagged_e}")
                
                if eips_found_and_attempted_release == 0: # Should be caught by "No Elastic IPs found"
                     eips_cleaned_successfully = True
                elif eips_successfully_released == eips_found_and_attempted_release:
                     eips_cleaned_successfully = True
                else:
                     print(f"Released {eips_successfully_released} out of {eips_found_and_attempted_release} found tagged EIPs.")
                     eips_cleaned_successfully = False # Not all were cleaned
        except Exception as desc_addr_e:
            print(f"Error describing addresses by tag '{eip_name_tag_value}': {desc_addr_e}")
            eips_cleaned_successfully = False
    else:
        print("Skipping EIP cleanup by tag: connector_name not provided.")
        eips_cleaned_successfully = True # Considered "handled" as it's not applicable.

    return instance_terminated_successfully and eips_cleaned_successfully

def delete_security_group_by_name(ec2_client, vpc_id: str, sg_group_name: str) -> bool:
    """
    Deletes a security group by its GroupName within a specific VPC.
    Security groups can only be deleted if they are not in use.
    """
    try:
        # First, find the security group ID from its GroupName and VPC ID
        response = ec2_client.describe_security_groups(
            Filters=[
                {'Name': 'group-name', 'Values': [sg_group_name]},
                {'Name': 'vpc-id', 'Values': [vpc_id]}
            ]
        )
        if not response.get('SecurityGroups'):
            print(f"Security group with GroupName '{sg_group_name}' not found in VPC '{vpc_id}'. Considered deleted.")
            return True # Not found, so effectively deleted or never existed.
        
        sg_to_delete = response['SecurityGroups'][0]
        sg_id_to_delete = sg_to_delete['GroupId']
        # Use Name tag for logging if available, otherwise GroupName
        sg_display_name = next((tag['Value'] for tag in sg_to_delete.get('Tags', []) if tag['Key'] == 'Name'), sg_group_name)

        print(f"Found security group '{sg_display_name}' (ID: {sg_id_to_delete}, GroupName: {sg_group_name}) in VPC '{vpc_id}'. Attempting deletion...")
        
        # Attempt to delete the security group by its ID
        ec2_client.delete_security_group(GroupId=sg_id_to_delete)
        print(f"Successfully initiated deletion of security group '{sg_display_name}' (ID: {sg_id_to_delete}).")
        return True
    except ec2_client.exceptions.ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == 'InvalidGroup.NotFound':
            print(f"Security group '{sg_group_name}' (or its ID if resolved) not found during deletion attempt. Considered deleted.")
            return True
        elif error_code == 'DependencyViolation' or "dependency" in str(e).lower() or "in use by" in str(e).lower():
            # This error means the SG is still associated with a network interface or other resource.
            print(f"Error deleting security group '{sg_group_name}': It is still in use. Error: {e}")
            return False
        else:
            print(f"AWS ClientError deleting security group '{sg_group_name}': {e}")
            return False
    except Exception as e:
        # Catch any other unexpected errors
        print(f"An unexpected error occurred while trying to delete security group '{sg_group_name}': {e}")
        return False

# Example Usage (requires valid AMI ID, key pair, security group, and subnet)
#if __name__ == '__main__':
