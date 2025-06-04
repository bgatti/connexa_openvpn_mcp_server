# AWS Tools Library

This library provides a set of Python functions for managing AWS resources, particularly focused on creating and deleting regional egress points (either via OpenVPN EC2 instances or NAT Gateways) and managing AWS credentials.

This library is intended to be used as a sub-module within a larger project.

## Prerequisites

1.  **AWS Credentials**: Ensure your AWS credentials (Access Key ID and Secret Access Key) and default region are configured. This library primarily expects these to be available in a `.env` file in the root of the project using this library.
    Example `.env` file:
    ```
    AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY_ID"
    AWS_SECRET_ACCESS_KEY="YOUR_SECRET_ACCESS_KEY"
    AWS_DEFAULT_REGION="us-west-1"
    # Optional: For multi-region testing, you can specify preferred test regions
    # AWS_TEST_REGION_1="us-west-1"
    # AWS_TEST_REGION_2="us-east-2"
    ```
    The `refresh_aws_credentials_and_region` function will load these.

2.  **OpenVPN Profile (Optional)**: If using the `upsert_regional_egress` function to create an OpenVPN-based egress, you will need an `.ovpn` profile file. The test scripts (`test_single_region_egress.py` and `test_multi_region_operations.py`) look for a file named `featherriverprinter_san_jose_(ca).ovpn` in the same directory as the test scripts.

3.  **EC2 Key Pair**: For creating EC2 instances (e.g., for OpenVPN egress), ensure an EC2 Key Pair named `mcp_openvpn` exists in the AWS regions where you intend to deploy resources.

## Dependencies

This library relies on the following Python packages. You can install them using `uv` or `pip`:

```bash
uv pip install boto3 python-dotenv
```
or
```bash
pip install boto3 python-dotenv
```

## Local Dependencies

This library (`aws_tools.py`) depends on a local helper module:

*   `aws_boto3_apis.py`: This file contains lower-level Boto3 API interaction functions and **must be present in the same directory as `aws_tools.py`** for the imports to work correctly.

## Testing the Library

The library includes test scripts that can be run to verify its functionality. These tests will create and delete real AWS resources, so be mindful of potential costs and ensure your AWS credentials have the necessary permissions.

**Test Files:**

*   `test_single_region_egress.py`: Tests the creation and deletion of egress resources (OpenVPN EC2 instance) in a single AWS region.
*   `test_multi_region_operations.py`: Tests listing AWS regions and then creating/deleting egress resources in two different AWS regions.

**Running the Tests:**

1.  **Navigate to the Directory**: Open your terminal and navigate to the directory containing `aws_tools.py`, `aws_boto3_apis.py`, and the test files (e.g., `your_project_root/aws/`).
2.  **Ensure Prerequisites**:
    *   Make sure your `.env` file is set up correctly in the project root (one level above the `aws` directory if `aws` is a subdirectory, or in the same directory if running tests directly from where `.env` would be expected by `load_dotenv()`). The test scripts call `refresh_aws_credentials_and_region` which uses `load_dotenv()`.
    *   Place the `featherriverprinter_san_jose_(ca).ovpn` file (or your test `.ovpn` file, renaming it or updating the test script) in the same directory as the test scripts.
    *   Ensure the `mcp_openvpn` EC2 key pair exists in the regions you'll be testing against (e.g., `us-west-1`, `us-east-2`, or your `AWS_DEFAULT_REGION`).
3.  **Execute the Test Scripts**:
    ```bash
    python test_single_region_egress.py
    ```
    ```bash
    python test_multi_region_operations.py
    ```
    Observe the output in your terminal. The scripts will print information about the resources being created and deleted.

## Available Functions

The following functions are available for import from `aws_tools.py`:

### 1. `refresh_aws_credentials_and_region`

*   **Signature**: `refresh_aws_credentials_and_region(region_id: Optional[str] = None) -> Dict[str, Optional[str]]`
*   **Description**: Loads AWS credentials (access key, secret key) and the default region from a `.env` file located in the project's root directory. It sets these as environment variables, making them accessible to `boto3`. An optional `region_id` parameter can be provided to override the region specified in the `.env` file or to set it if not present.
*   **Returns**: A dictionary containing the AWS access key ID, secret access key, and default region that were loaded and set.

### 2. `upsert_regional_egress`

*   **Signature**: `upsert_regional_egress(prefix: str, public: bool, region_id: Optional[str] = None, openvpn_profile_content: Optional[str] = None) -> Optional[Dict[str, Any]]`
*   **Description**: Creates or updates regional egress resources in AWS.
    *   If `public` is `True`:
        *   If `openvpn_profile_content` (string content of an .ovpn file) is provided, it sets up an EC2 instance configured with OpenVPN to act as the egress point. This includes creating a public subnet, security group, and the EC2 instance itself.
        *   If `openvpn_profile_content` is `None`, it sets up a NAT Gateway for public egress. This includes creating a public subnet, allocating an Elastic IP, and creating the NAT Gateway.
    *   If `public` is `False`, it ensures an Internet Gateway is attached to the default VPC, facilitating controlled internet access rather than a dedicated public IP egress point.
*   **Arguments**:
    *   `prefix` (str): A unique prefix string used for naming and tagging AWS resources (e.g., VPCs, subnets, instances, security groups).
    *   `public` (bool): If `True`, sets up public internet egress. If `False`, configures for more controlled or private access.
    *   `region_id` (Optional[str]): The AWS region where resources should be created/updated. If `None`, uses the default region from `.env` or environment variables.
    *   `openvpn_profile_content` (Optional[str]): The string content of an OpenVPN client configuration file. Required if `public` is `True` and an OpenVPN EC2 instance is desired for egress.
*   **Returns**: A dictionary containing details of the created or updated resources (e.g., VPC ID, subnet ID, public IP if applicable, instance ID, NAT Gateway ID). Returns `None` on failure.

### 3. `delete_regional_egress`

*   **Signature**: `delete_regional_egress(instance_id: Optional[str], prefix: Optional[str] = None, region_id: Optional[str] = None, sg_group_name: Optional[str] = None, vpc_id: Optional[str] = None, instance_base_name: Optional[str] = None, subnet_id_to_delete: Optional[str] = None) -> bool`
*   **Description**: Deletes regional egress resources previously created by `upsert_regional_egress`. This can include an EC2 instance, its associated Elastic IP, its security group, and the subnet it was launched in. It can also clean up tagged EIPs even if an instance ID is not provided (e.g., if instance creation failed after EIP allocation).
*   **Arguments**:
    *   `instance_id` (Optional[str]): The ID of the EC2 instance to delete. If an OpenVPN instance was created, this is its ID. Can be `None` if only cleaning up other resources like tagged EIPs or a subnet.
    *   `prefix` (Optional[str]): The prefix used when the resources were created. Used to identify tagged resources like EIPs and to derive security group names if not explicitly provided.
    *   `region_id` (Optional[str]): The AWS region where the resources exist.
    *   `sg_group_name` (Optional[str]): The name of the security group to delete. If not provided, it can be derived using `prefix` and `instance_base_name`.
    *   `vpc_id` (Optional[str]): The VPC ID where the security group resides. Required for security group deletion.
    *   `instance_base_name` (Optional[str]): The base name used for the instance and related resources (e.g., "ovpn_egress"). Used for EIP tagging and deriving security group names.
    *   `subnet_id_to_delete` (Optional[str]): The ID of the subnet to delete.
*   **Returns**: `True` if all specified deletions were successful or if the resources were not found (assumed already deleted). `False` otherwise.

### 4. `get_aws_regions`

*   **Signature**: `get_aws_regions(only_opted_in_regions: bool = False) -> list`
*   **Description**: Retrieves a list of AWS regions.
*   **Arguments**:
    *   `only_opted_in_regions` (bool): If `True` (default is `False`), returns only regions that are opted-in or where opt-in is not required. Otherwise, returns all AWS regions.
*   **Returns**: A list of AWS region name strings (e.g., `['us-east-1', 'us-west-2']`). Returns an empty list on failure.

## Usage Example

Assuming this `aws` library is a subfolder in your project structure (e.g., `your_project_root/aws/aws_tools.py`):

```python
# In your parent project's code (e.g., your_project_root/main.py)

from aws.aws_tools import (
    refresh_aws_credentials_and_region,
    upsert_regional_egress,
    delete_regional_egress,
    get_aws_regions
)
import os

# Example: List available AWS regions
def list_my_regions():
    print("Fetching available AWS regions...")
    # Ensure .env is loaded if not already by refresh_aws_credentials_and_region
    # For get_aws_regions, direct boto3 client is used, so creds should be in env.
    refresh_aws_credentials_and_region() # Good practice to call this to ensure env is set up
    
    regions = get_aws_regions(only_opted_in_regions=True)
    if regions:
        print("Available (opted-in) regions:")
        for region in regions:
            print(f"- {region}")
    else:
        print("Could not retrieve regions.")

# Example: Setting up and tearing down an OpenVPN egress point
def manage_ovpn_egress_example():
    my_prefix = "my-test-egress"
    my_region = "us-west-2" # Example region

    # Ensure .env file is in the root of your_project_root
    # For example:
    # AWS_ACCESS_KEY_ID="YOUR_KEY"
    # AWS_SECRET_ACCESS_KEY="YOUR_SECRET"
    # AWS_DEFAULT_REGION="us-west-1"

    # Load OpenVPN profile content from a file
    ovpn_profile_content = None
    try:
        # Adjust path to your .ovpn file as needed
        with open("path/to/your/profile.ovpn", "r") as f:
            ovpn_profile_content = f.read()
    except FileNotFoundError:
        print("OpenVPN profile file not found. Cannot create OVPN egress.")
        return

    if not ovpn_profile_content:
        print("OpenVPN profile content is empty.")
        return

    print(f"Attempting to set up OpenVPN egress in {my_region} with prefix {my_prefix}...")
    egress_details = upsert_regional_egress(
        prefix=my_prefix,
        public=True,
        region_id=my_region,
        openvpn_profile_content=ovpn_profile_content
    )

    if egress_details and egress_details.get("ovpn_instance_id"):
        print("OpenVPN Egress setup successful!")
        print(f"  Instance ID: {egress_details.get('ovpn_instance_id')}")
        print(f"  Public IP: {egress_details.get('public_ip')}")
        print(f"  VPC ID: {egress_details.get('vpc_id')}")
        print(f"  Subnet ID: {egress_details.get('ovpn_instance_subnet_id')}")
        print(f"  Security Group ID: {egress_details.get('ovpn_instance_security_group_id')}")
        print(f"  Security Group Name: {egress_details.get('ovpn_instance_security_group_name')}")


        # ... use the egress point ...

        print("Attempting to delete the OpenVPN egress point...")
        delete_success = delete_regional_egress(
            instance_id=egress_details.get("ovpn_instance_id"),
            prefix=my_prefix,
            region_id=my_region,
            sg_group_name=egress_details.get("ovpn_instance_security_group_name"),
            vpc_id=egress_details.get("vpc_id"),
            instance_base_name=egress_details.get("instance_base_name"), # "ovpn_egress" by default
            subnet_id_to_delete=egress_details.get("ovpn_instance_subnet_id")
        )
        if delete_success:
            print("Egress point deleted successfully.")
        else:
            print("Failed to delete egress point completely.")
    elif egress_details:
        print("Egress setup initiated, but OVPN instance ID not found. Details:")
        for key, value in egress_details.items():
            print(f"  {key}: {value}")
    else:
        print("Failed to set up OpenVPN egress.")

if __name__ == "__main__":
    list_my_regions()
    # manage_ovpn_egress_example() # Uncomment to run the egress example
```

## For AI Tools / LLMs

When using this library with an AI tool:
-   **Key Functions**: `upsert_regional_egress` and `delete_regional_egress` are the primary functions for managing infrastructure. `get_aws_regions` can be used to discover valid regions. `refresh_aws_credentials_and_region` is crucial for setting up the AWS environment.
-   **Parameters**: Pay close attention to the required parameters for each function, especially `prefix`, `region_id`, and the conditional `openvpn_profile_content`. For deletion, providing all known identifiers (`instance_id`, `sg_group_name`, `vpc_id`, `subnet_id_to_delete`, `instance_base_name`) will lead to more reliable cleanup.
-   **Return Values**: The dictionary returned by `upsert_regional_egress` contains important identifiers (like `ovpn_instance_id`, `public_ip`, `ovpn_instance_security_group_name`, `vpc_id`, `instance_base_name`, `ovpn_instance_subnet_id`) that are needed for the `delete_regional_egress` function. Ensure these are captured and passed correctly.
-   **Idempotency**: The `upsert_` functions aim to be idempotent, meaning they can be called multiple times with the same parameters and should result in the same state without error (either by creating or finding existing resources). Deletion functions will typically succeed if the resource is already gone.
-   **Error Handling**: Check the return values. `upsert_regional_egress` returns `None` on critical failure. `delete_regional_egress` returns `False` if any part of the deletion fails. The `notes` field in the dictionary returned by `upsert_regional_egress` can contain useful diagnostic information.
-   **Dependencies**: Remember the `boto3` and `python-dotenv` pip packages, and the local `aws_boto3_apis.py` file.
