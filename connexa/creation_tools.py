# connexa_openvpn_mcp_server/connexa/creation_tools.py
import logging
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field

from .connexa_api import call_api
from .selected_object import CURRENT_SELECTED_OBJECT # Import for create_user_tool
from ..aws.aws_tools import upsert_regional_egress # Import the provisioning tool
# Removed: from .connector_tools import IpSecConfigRequestModel
# IpSecConfigRequestModel will be defined in this file.

logger = logging.getLogger(__name__)

# --- Pydantic Models for IPsec Configuration (derived from swagger.json) ---

class IkePhaseModel(BaseModel):
    encryption_algorithms: Optional[List[Literal["AES128", "AES256", "AES128_GCM_16", "AES256_GCM_16"]]] = Field(None, alias="encryptionAlgorithms")
    integrity_algorithms: Optional[List[Literal["SHA1", "SHA2_256", "SHA2_384", "SHA2_512"]]] = Field(None, alias="integrityAlgorithms")
    diffie_hellman_groups: Optional[List[Literal["G_1", "G_2", "G_5", "G_14", "G_15", "G_16", "G_19", "G_20", "G_24"]]] = Field(None, alias="diffieHellmanGroups")
    lifetime_sec: Optional[int] = Field(None, alias="lifetimeSec", description="Lifetime in seconds, e.g., 3600.")

    class Config:
        populate_by_name = True

class IkeRekeyModel(BaseModel):
    margin_time_sec: Optional[int] = Field(None, alias="marginTimeSec", description="Margin time in seconds, e.g., 270.")
    fuzz_percent: Optional[int] = Field(None, alias="fuzzPercent", description="Fuzz percent, e.g., 100.")
    replay_window_size: Optional[int] = Field(None, alias="replayWindowSize", description="Replay window size, e.g., 1024.")

    class Config:
        populate_by_name = True

class IkeDeadPeerDetectionModel(BaseModel):
    timeout_sec: Optional[int] = Field(None, alias="timeoutSec", description="Timeout in seconds, e.g., 30.")
    dead_peer_handling: Optional[Literal["RESTART", "NONE"]] = Field(None, alias="deadPeerHandling")

    class Config:
        populate_by_name = True

class IkeProtocolModel(BaseModel):
    protocol_version: Optional[Literal["IKE_V1", "IKE_V2"]] = Field(None, alias="protocolVersion")
    phase1: Optional[IkePhaseModel] = None
    phase2: Optional[IkePhaseModel] = None
    rekey: Optional[IkeRekeyModel] = None
    dead_peer_detection: Optional[IkeDeadPeerDetectionModel] = Field(None, alias="deadPeerDetection")
    startup_action: Optional[Literal["START", "ATTACH"]] = Field(None, alias="startupAction")

    class Config:
        populate_by_name = True

class IpSecConfigRequestModel(BaseModel):
    platform: Optional[Literal["AWS", "CISCO", "AZURE", "GCP", "OTHER"]] = None
    authentication_type: Optional[Literal["SHARED_SECRET", "CERTIFICATE"]] = Field(None, alias="authenticationType")
    remote_site_public_ip: Optional[str] = Field(None, alias="remoteSitePublicIp")
    pre_shared_key: Optional[str] = Field(None, alias="preSharedKey")
    ca_certificate: Optional[str] = Field(None, alias="caCertificate")
    peer_certificate: Optional[str] = Field(None, alias="peerCertificate")
    remote_gateway_certificate: Optional[str] = Field(None, alias="remoteGatewayCertificate")
    peer_certificate_private_key: Optional[str] = Field(None, alias="peerCertificatePrivateKey")
    peer_certificate_key_passphrase: Optional[str] = Field(None, alias="peerCertificateKeyPassphrase")
    ike_protocol: Optional[IkeProtocolModel] = Field(None, alias="ikeProtocol")
    hostname: Optional[str] = None # Not in IpSecConfigRequest in swagger, but in IpSecConfigResponse. Check if needed for request.
    domain: Optional[str] = None   # Not in IpSecConfigRequest in swagger, but in IpSecConfigResponse. Check if needed for request.

    class Config:
        populate_by_name = True


# --- Pydantic Models for Create Operations (derived from swagger.json) ---

class NetworkRouteRequestModel(BaseModel):
    value: str = Field(..., description="The route value, e.g., '10.0.0.0/24'.")
    description: Optional[str] = Field(None, description="Optional description for the route.")

class NetworkConnectorRequestModelForCreate(BaseModel): # Simplified for inline creation
    name: str = Field(..., description="Name for the connector.")
    vpn_region_id: str = Field(..., description="ID of the VPN region for the connector.")
    description: Optional[str] = Field(None, description="Optional description for the connector.")
    ip_sec_config: Optional[IpSecConfigRequestModel] = Field(None, description="IPsec configuration, if applicable.", alias="ipSecConfig")

    class Config:
        populate_by_name = True

class CreateNetworkArgs(BaseModel):
    name: str = Field(..., description="Name for the new network.")
    description: Optional[str] = Field(None, description="Optional description for the network.")
    internet_access: Optional[Literal["SPLIT_TUNNEL_ON", "SPLIT_TUNNEL_OFF", "RESTRICTED_INTERNET"]] = Field(None, description="Internet access mode.", alias="internetAccess")
    egress: Optional[bool] = Field(None, description="Whether this network is an egress network.")
    routes: Optional[List[NetworkRouteRequestModel]] = Field(None, description="List of routes for the network.")
    connectors: Optional[List[NetworkConnectorRequestModelForCreate]] = Field(None, description="List of connectors to create with the network.")
    tunneling_protocol: Optional[Literal["OPENVPN", "IPSEC"]] = Field(None, description="Tunneling protocol for the network.", alias="tunnelingProtocol")
    gateways_ids: Optional[List[str]] = Field(None, description="List of gateway IDs for the network.", alias="gatewaysIds")

    class Config:
        populate_by_name = True

class CreateNetworkConnectorArgs(BaseModel):
    network_id: str = Field(..., description="ID of the Network to create the connector in.", alias="networkId") # Path/Query param
    name: str = Field(..., description="Name for the new network connector.")
    vpn_region_id: str = Field(..., description="ID of the VPN region for the connector.", alias="vpnRegionId")
    description: Optional[str] = Field(None, description="Optional description for the connector.")
    ip_sec_config: Optional[IpSecConfigRequestModel] = Field(None, description="IPsec configuration for the connector, if applicable.", alias="ipSecConfig")

    class Config:
        populate_by_name = True

class CreateUserGroupArgs(BaseModel):
    name: str = Field(..., description="Unique name for the user group.")
    vpn_region_ids: Optional[List[str]] = Field(None, description="List of VPN Region IDs accessible to this group.", alias="vpnRegionIds")
    internet_access: Optional[Literal["SPLIT_TUNNEL_ON", "SPLIT_TUNNEL_OFF", "RESTRICTED_INTERNET"]] = Field(None, description="Internet access level.", alias="internetAccess")
    max_device: Optional[int] = Field(None, description="Maximum number of devices allowed per user in this group.", alias="maxDevice")
    connect_auth: Optional[Literal["NO_AUTH", "ON_PRIOR_AUTH", "EVERY_TIME"]] = Field(None, description="Connection authentication mode.", alias="connectAuth")
    all_regions_included: Optional[bool] = Field(None, description="True if all current and future regions are included by default.", alias="allRegionsIncluded")
    gateways_ids: Optional[List[str]] = Field(None, description="List of Gateway IDs. Required if internetAccess is SPLIT_TUNNEL_OFF.", alias="gatewaysIds")

    class Config:
        populate_by_name = True

class HostConnectorRequestModelForCreate(BaseModel):
    name: str = Field(..., description="Name for the host connector.")
    vpn_region_id: str = Field(..., description="ID of the VPN region for the connector.", alias="vpnRegionId")
    description: Optional[str] = Field(None, description="Optional description for the host connector.")

    class Config:
        populate_by_name = True

class CreateHostArgs(BaseModel):
    name: str = Field(..., description="Name for the new host.")
    description: Optional[str] = Field(None, description="Optional description for the host.")
    internet_access: Optional[Literal["SPLIT_TUNNEL_ON", "SPLIT_TUNNEL_OFF", "RESTRICTED_INTERNET"]] = Field(None, description="Internet access mode.", alias="internetAccess")
    domain: Optional[str] = Field(None, description="Domain for the host.")
    connectors: Optional[List[HostConnectorRequestModelForCreate]] = Field(None, description="List of connectors to create with the host.")
    gateways_ids: Optional[List[str]] = Field(None, description="List of gateway IDs for the host.", alias="gatewaysIds")

    class Config:
        populate_by_name = True

class CreateHostConnectorArgs(BaseModel):
    host_id: str = Field(..., description="ID of the Host to create the connector in.", alias="hostId") # Query param
    name: str = Field(..., description="Name for the new host connector.")
    vpn_region_id: str = Field(..., description="ID of the VPN region for the connector.", alias="vpnRegionId")
    description: Optional[str] = Field(None, description="Optional description for the host connector.")

    class Config:
        populate_by_name = True

class CreateDeviceArgs(BaseModel):
    user_id: str = Field(..., description="ID of the User to associate the device with.", alias="userId") # Query param
    name: str = Field(..., description="Name for the new device.")
    description: Optional[str] = Field(None, description="Optional description for the device.")
    client_uuid: Optional[str] = Field(None, description="Client UUID of the device.", alias="clientUUID")

    class Config:
        populate_by_name = True

class CreateDnsRecordArgs(BaseModel):
    domain: str = Field(..., description="The domain name for the DNS record (e.g., 'myserver.example.com').")
    description: Optional[str] = Field(None, description="Optional description for the DNS record.")
    ipv4_addresses: Optional[List[str]] = Field(None, description="List of IPv4 addresses for the record.", alias="ipv4Addresses")
    ipv6_addresses: Optional[List[str]] = Field(None, description="List of IPv6 addresses for the record.", alias="ipv6Addresses")

    class Config:
        populate_by_name = True

# --- Models for Access Group Creation ---
class AccessItemSourceRequestModel(BaseModel):
    type: Literal["USER_GROUP", "NETWORK_SERVICE", "HOST"]
    all_covered: Optional[bool] = Field(None, alias="allCovered")
    parent: Optional[str] = None
    children: Optional[List[str]] = None

    class Config:
        populate_by_name = True

class AccessItemDestinationRequestModel(BaseModel):
    type: Literal["USER_GROUP", "NETWORK_SERVICE", "HOST_SERVICE", "PUBLISHED_SERVICE"]
    all_covered: Optional[bool] = Field(None, alias="allCovered")
    parent: Optional[str] = None
    children: Optional[List[str]] = None

    class Config:
        populate_by_name = True

class CreateAccessGroupArgs(BaseModel):
    name: str = Field(..., description="Name for the new access group.")
    description: Optional[str] = Field(None, description="Optional description for the access group.")
    source: Optional[List[AccessItemSourceRequestModel]] = Field(None, description="List of source access items.")
    destination: Optional[List[AccessItemDestinationRequestModel]] = Field(None, description="List of destination access items.")

    class Config:
        populate_by_name = True

# --- Models for Location Context Creation ---
class IpRequestModel(BaseModel):
    ip: str
    description: Optional[str] = None

class IpCheckRequestModel(BaseModel):
    allowed: bool
    ips: Optional[List[IpRequestModel]] = None

class CountryCheckRequestModel(BaseModel):
    countries: Optional[List[str]] = None
    allowed: bool

class DefaultCheckRequestModel(BaseModel):
    allowed: bool

class CreateLocationContextArgs(BaseModel):
    name: str = Field(..., description="Name for the new location context policy.")
    description: Optional[str] = Field(None, description="Optional description.")
    user_groups_ids: Optional[List[str]] = Field(None, alias="userGroupsIds", description="List of user group IDs associated with this policy.")
    ip_check: Optional[IpCheckRequestModel] = Field(None, alias="ipCheck", description="IP check criteria.")
    country_check: Optional[CountryCheckRequestModel] = Field(None, alias="countryCheck", description="Country check criteria.")
    default_check: Optional[DefaultCheckRequestModel] = Field(None, alias="defaultCheck", description="Default check criteria for access.")

    class Config:
        populate_by_name = True

# --- Models for Device Posture Policy Creation ---
class VersionPolicyModel(BaseModel):
    version: Optional[str] = None
    condition: Optional[Literal["GTE", "LTE", "EQUAL"]] = None

class DiskEncryptionModel(BaseModel):
    type: Optional[Literal["FULL_DISK", "SPECIFIC_VOLUME"]] = None
    volume: Optional[str] = None

class WindowsRequestModel(BaseModel):
    allowed: Optional[bool] = None
    version: Optional[VersionPolicyModel] = None
    antiviruses: Optional[List[Literal["AVAST", "AVG", "AVIRA", "BITDEFENDER", "CROWDSTRIKE_FALCON", "ESET", "MALWAREBYTES", "MCAFEE", "MICROSOFT_DEFENDER", "NORTON", "SENTINEL_ONE"]]] = None
    disk_encryption: Optional[DiskEncryptionModel] = Field(None, alias="diskEncryption")
    certificate: Optional[str] = None

    class Config:
        populate_by_name = True

class MacOSRequestModel(BaseModel):
    allowed: Optional[bool] = None
    version: Optional[VersionPolicyModel] = None
    antiviruses: Optional[List[Literal["AVAST", "AVG", "AVIRA", "BITDEFENDER", "CROWDSTRIKE_FALCON", "ESET", "MALWAREBYTES", "MCAFEE", "MICROSOFT_DEFENDER", "NORTON", "SENTINEL_ONE"]]] = None
    disk_encrypted: Optional[bool] = Field(None, alias="diskEncrypted") # Note: swagger shows diskEncrypted for macOS
    certificate: Optional[str] = None

    class Config:
        populate_by_name = True

class LinuxRequestModel(BaseModel):
    allowed: Optional[bool] = None

class AndroidRequestModel(BaseModel):
    allowed: Optional[bool] = None

class IOSRequestModel(BaseModel):
    allowed: Optional[bool] = None

class CreateDevicePostureArgs(BaseModel):
    name: str = Field(..., description="Name for the new device posture policy.")
    description: Optional[str] = Field(None, description="Optional description.")
    user_groups_ids: Optional[List[str]] = Field(None, alias="userGroupsIds", description="List of user group IDs this policy applies to.")
    windows: Optional[WindowsRequestModel] = None
    macos: Optional[MacOSRequestModel] = None
    linux: Optional[LinuxRequestModel] = None
    android: Optional[AndroidRequestModel] = None
    ios: Optional[IOSRequestModel] = None

    class Config:
        populate_by_name = True

# --- Model for User Creation (to match user_tools.create_user signature) ---
class CreateUserArgs(BaseModel):
    firstName: str = Field(..., description="User's first name.")
    lastName: str = Field(..., description="User's last name.")
    username: str = Field(..., description="Username for the user. This will be used for login.")
    email: str = Field(..., description="User's email address.")
    groupId: Optional[str] = Field(None, description="ID of the group the user belongs to. If not provided, will attempt to use selected group.")
    role: Literal["OWNER", "MEMBER", "ADMIN"] = Field(..., description="Role of the user. Must be one of: OWNER, MEMBER, ADMIN.")

    class Config:
        populate_by_name = True

# +++ SIMPLE TEST FUNCTION FOR PYLANCE DIAGNOSTICS +++
def simple_creation_test_function() -> str:
    return "This is a simple test from creation_tools."
# +++ END SIMPLE TEST FUNCTION +++
        
# --- Tool Functions ---

def create_network_tool(args: CreateNetworkArgs) -> Dict[str, Any]:
    """
    Creates a new Network.
    Corresponds to POST /api/v1/networks.
    """
    logger.info(f"Attempting to create network '{args.name}'.")

    # Use model_dump to handle alias mapping and exclude_none by default
    # This correctly uses the field aliases for the API payload.
    payload = args.model_dump(by_alias=True, exclude_none=True)
    
    # Ensure 'name' is present as it's required by the CreateNetworkArgs model
    # but model_dump might not include it if it was None (though 'name' is not Optional here)
    # However, the CreateNetworkArgs has 'name' as non-optional, so it will always be there.
    # If 'name' was optional and None, we might need: payload["name"] = args.name or some default.
    # For this specific model, this is fine.

    api_path = "/api/v1/networks"
    
    try:
        response_data_full = call_api(action="post", path=api_path, value=payload) # This is the full API response object
        
        api_response_status = response_data_full.get("status") if isinstance(response_data_full, dict) else "Unknown"
        actual_network_data = response_data_full.get("data") if isinstance(response_data_full, dict) else None

        if actual_network_data and isinstance(actual_network_data, dict):
            created_id = actual_network_data.get("id")
            created_name = actual_network_data.get("name")

            if created_id and created_name:
                # Success case: API call was successful and we found id/name in the nested data
                logger.info(f"Successfully created network '{created_name}' (ID: {created_id}). API Response data: {actual_network_data}")
                CURRENT_SELECTED_OBJECT.select(
                    object_type="network", 
                    object_id=created_id,
                    object_name=created_name,
                    details=actual_network_data 
                )
                logger.info(f"Newly created network '{created_name}' (ID: {created_id}) has been selected.")
                # Return the actual network data object, not the whole API response
                return actual_network_data 
            else:
                # API call might have been "successful" (e.g., 201 status) but id/name missing in actual_network_data
                logger.warning(f"Network '{args.name}' creation API call reported status {api_response_status}, but 'id' or 'name' not found in the 'data' field. Actual data: {actual_network_data}. Full API Response: {response_data_full}")
                return {"status": "warning", "message": "Network created (API success) but ID or name not found in its data payload.", "details": response_data_full}
        else:
            # The structure of response_data_full was not as expected
            logger.warning(f"Network '{args.name}' creation API call reported status {api_response_status}, but the response format was unexpected. Full API Response: {response_data_full}")
            return {"status": "warning", "message": "Network created (API success) but API response format was unexpected.", "details": response_data_full}

    except Exception as e:
        logger.error(f"Exception during network creation for '{args.name}': {e}. Payload: {payload}", exc_info=True)
        error_message = str(e)
        if hasattr(e, 'args') and e.args:
            if isinstance(e.args[0], dict) and 'message' in e.args[0]:
                error_message = e.args[0]['message']
            elif isinstance(e.args[0], str):
                 error_message = e.args[0]
        return {"status": "error", "message": f"Exception during network creation: {error_message}", "details": str(e)}

if __name__ == "__main__":
    # Example usage (requires connexa_api.py and its dependencies to be configured for call_api)
    # This is a placeholder for actual testing within the MCP server environment.
    logging.basicConfig(level=logging.INFO)
    logger.info("Testing creation_tools.py standalone.")
    
    # Mock call_api for standalone testing if needed, or ensure config is loaded for live tests.
    # For now, this will just show the structure.
    
    test_network_args = CreateNetworkArgs(
        name="TestNet-From-Tool",
        description="A test network created by the new tool.",
        # Attempting to instantiate using aliases, since populate_by_name = True
        internetAccess="SPLIT_TUNNEL_ON", 
        egress=False,
        routes=[NetworkRouteRequestModel(value="192.168.100.0/24", description="Local LAN")],
        connectors=[
            NetworkConnectorRequestModelForCreate(
                name="TestConn-Inline", 
                vpn_region_id="us-west-1", # Replace with actual region ID
                description="Inline test connector",
                ipSecConfig=None # Using alias for instantiation
            )
        ],
        tunnelingProtocol="OPENVPN", # Using alias
        gatewaysIds=[] # Using alias
    )
    logger.info(f"Example CreateNetworkArgs: {test_network_args.model_dump_json(indent=2, by_alias=True)}")

    # --- create_network_connector_tool ---
    # Placeholder for actual testing, requires valid network_id and vpn_region_id
    test_connector_args = CreateNetworkConnectorArgs(
        networkId="net_replace_with_actual_network_id", 
        name="TestConnectorViaTool",
        vpnRegionId="reg_replace_with_actual_region_id",
        description="A test network connector created by the new tool.",
        ipSecConfig=None 
    )
    logger.info(f"Example CreateNetworkConnectorArgs: {test_connector_args.model_dump_json(indent=2, by_alias=True)}")

    # --- create_user_group_tool ---
    test_user_group_args = CreateUserGroupArgs(
        name="TestDevelopersGroup",
        vpnRegionIds=["reg_id_1", "reg_id_2"], # Replace with actual region IDs
        internetAccess="SPLIT_TUNNEL_ON",
        maxDevice=3,
        connectAuth="ON_PRIOR_AUTH",
        allRegionsIncluded=False,
        gatewaysIds=[]
    )
    logger.info(f"Example CreateUserGroupArgs: {test_user_group_args.model_dump_json(indent=2, by_alias=True)}")

    # --- create_host_tool ---
    test_host_args = CreateHostArgs(
        name="TestWebServerHost",
        description="Primary web server host.",
        internetAccess="SPLIT_TUNNEL_ON",
        domain="internal.example.com",
        connectors=[
            HostConnectorRequestModelForCreate(
                name="WebServerMainConnector",
                vpnRegionId="us-east-1", # Replace with actual region ID
                description="Main connector for web server host"
            )
        ],
        gatewaysIds=[]
    )
    logger.info(f"Example CreateHostArgs: {test_host_args.model_dump_json(indent=2, by_alias=True)}")

    # --- create_host_connector_tool ---
    test_host_connector_args = CreateHostConnectorArgs(
        hostId="host_replace_with_actual_host_id",
        name="TestHostConnectorViaTool",
        vpnRegionId="reg_replace_with_actual_region_id",
        description="A test host connector created by the new tool."
    )
    logger.info(f"Example CreateHostConnectorArgs: {test_host_connector_args.model_dump_json(indent=2, by_alias=True)}")

    # --- create_device_tool ---
    test_device_args = CreateDeviceArgs(
        userId="user_replace_with_actual_id",
        name="MyLaptopDevice",
        description="Primary work laptop",
        clientUUID="optional-client-uuid-if-known"
    )
    logger.info(f"Example CreateDeviceArgs: {test_device_args.model_dump_json(indent=2, by_alias=True)}")

    # --- create_dns_record_tool ---
    test_dns_record_args = CreateDnsRecordArgs(
        domain="printer.internal.mycompany.com",
        description="Network printer DNS record",
        ipv4Addresses=["192.168.1.100"],
        ipv6Addresses=[]
    )
    logger.info(f"Example CreateDnsRecordArgs: {test_dns_record_args.model_dump_json(indent=2, by_alias=True)}")

    # --- create_access_group_tool ---
    test_access_group_args = CreateAccessGroupArgs(
        name="DevTeamFullAccess",
        description="Access group for development team with full mesh.",
        source=[
            AccessItemSourceRequestModel(type="USER_GROUP", allCovered=True)
        ],
        destination=[
            AccessItemDestinationRequestModel(type="NETWORK_SERVICE", allCovered=True),
            AccessItemDestinationRequestModel(type="HOST_SERVICE", allCovered=True)
        ]
    )
    logger.info(f"Example CreateAccessGroupArgs: {test_access_group_args.model_dump_json(indent=2, by_alias=True)}")

    # --- create_location_context_tool ---
    test_location_context_args = CreateLocationContextArgs(
        name="OfficeNetworkOnly",
        description="Allow access only from office IPs.",
        userGroupsIds=["group_id_1"], # Replace with actual group ID
        ipCheck=IpCheckRequestModel(
            allowed=True,
            ips=[IpRequestModel(ip="203.0.113.42", description="Main Office IP")]
        ),
        countryCheck=CountryCheckRequestModel(countries=["US"], allowed=True), # Example: Allow US
        defaultCheck=DefaultCheckRequestModel(allowed=False) # Deny by default if no other rule matches
    )
    logger.info(f"Example CreateLocationContextArgs: {test_location_context_args.model_dump_json(indent=2, by_alias=True)}")

    # --- create_device_posture_tool ---
    test_device_posture_args = CreateDevicePostureArgs(
        name="SecureWorkstationPolicy",
        description="Ensures workstations meet security standards.",
        userGroupsIds=["group_id_1"], # Replace with actual group ID
        windows=WindowsRequestModel(
            allowed=True,
            version=VersionPolicyModel(version="10.0.19045", condition="GTE"),
            antiviruses=["MICROSOFT_DEFENDER"],
            diskEncryption=DiskEncryptionModel(type="FULL_DISK")
        ),
        macos=MacOSRequestModel(allowed=True, diskEncrypted=True),
        linux=LinuxRequestModel(allowed=False) # Example: Disallow Linux for this policy
    )
    logger.info(f"Example CreateDevicePostureArgs: {test_device_posture_args.model_dump_json(indent=2, by_alias=True)}")

    # --- create_user_tool ---
    test_user_args = CreateUserArgs(
        firstName="John",
        lastName="Doe",
        username="johndoe",
        email="john.doe@example.com",
        groupId="group_replace_with_actual_id", # This would come from a selected group
        role="MEMBER"
    )
    logger.info(f"Example CreateUserArgs: {test_user_args.model_dump_json(indent=2, by_alias=True)}")


def create_user_tool(args: CreateUserArgs) -> Dict[str, Any]:
    """
    Creates a new User.
    Corresponds to POST /api/v1/users.
    The request body is UserRequest (represented by CreateUserArgs).
    The groupId within CreateUserArgs links the user to a specific group.
    If groupId is not provided in args, it attempts to use the currently selected user group.
    """
    logger.info(f"Attempting to create user '{args.username}' with email '{args.email}'. Provided groupId: {args.groupId}")

    final_group_id: Optional[str] = args.groupId

    if not final_group_id:
        logger.info("groupId not provided in args, checking selected object.")
        # Log the instance ID and current state of CURRENT_SELECTED_OBJECT from within create_user_tool
        logger.info(f"create_user_tool: CURRENT_SELECTED_OBJECT instance ID: {id(CURRENT_SELECTED_OBJECT)}")
        selected_info = CURRENT_SELECTED_OBJECT.get_selected_object_info()
        logger.info(f"create_user_tool: selected_info from CURRENT_SELECTED_OBJECT: {selected_info}")

        # Check if a usergroup is selected and has an ID
        if selected_info and selected_info.get("type") == "usergroup" and selected_info.get("id"):
            final_group_id = selected_info["id"]
            logger.info(f"Using groupId '{final_group_id}' from selected user group '{selected_info.get('name')}'.")
        else:
            logger.warning(f"No groupId provided and no user group selected, or selection is invalid. Selected info: {selected_info}")
            # This error message should match ERROR_USER_GROUP_REQUIRED from the test script for consistency.
            # The test script expects this specific string.
            return {
                "status": "error",
                "message": "Please Select a User Group before creating a user.",
                "details": "groupId was not provided in the arguments, and no valid user group is currently selected."
            }

    # Create a new payload dictionary ensuring all required fields for the API are present.
    # The CreateUserArgs model now has groupId as Optional, but the API expects it.
    api_payload = {
        "firstName": args.firstName,
        "lastName": args.lastName,
        "username": args.username,
        "email": args.email,
        "groupId": final_group_id, # This is now guaranteed to be a string if we reached here
        "role": args.role
    }
    
    # model_dump could also be used if we re-construct an object with the final_group_id,
    # but direct dict construction is also clear here.
    # Example with model_dump:
    # temp_user_data_for_api = args.model_copy(update={"groupId": final_group_id})
    # payload = temp_user_data_for_api.model_dump(by_alias=True, exclude_none=True)
    # For now, direct dict is fine.
    payload = api_payload # Using the directly constructed dict

    api_path = "/api/v1/users"

    try:
        api_response = call_api(action="post", path=api_path, value=payload)

        # Check if the API call itself was successful (status 2xx)
        if isinstance(api_response, dict) and api_response.get("status", 0) >= 200 and api_response.get("status", 0) < 300:
            # Extract the actual user data from the 'data' field of the API response
            user_data = api_response.get("data")

            if isinstance(user_data, dict):
                created_id = user_data.get("id")
                created_username = user_data.get("username")

                if created_id and created_username:
                    logger.info(f"Successfully created user '{created_username}' (ID: {created_id}). User Data: {user_data}")
                    CURRENT_SELECTED_OBJECT.select(
                        object_type="user",
                        object_id=created_id,
                        object_name=created_username,
                        details=user_data # Store the actual user data as details
                    )
                    logger.info(f"Newly created user '{created_username}' (ID: {created_id}) has been selected.")
                    return user_data # Return the actual user data on success
                else:
                    # This case should be rare if API returns 201 with expected body
                    logger.warning(f"User '{args.username}' creation API call successful (status {api_response.get('status')}), but 'id' or 'username' not found in the 'data' payload. Cannot select. API Response: {api_response}")
                    return {"status": "warning", "message": "User created (API success) but ID or username not found in its data payload.", "details": api_response}
            else:
                 # This case indicates an unexpected response format from the API
                 logger.warning(f"User '{args.username}' creation API call successful (status {api_response.get('status')}), but the 'data' field is not a dictionary. Cannot select. API Response: {api_response}")
                 return {"status": "warning", "message": "User created (API success) but API response data format was unexpected.", "details": api_response}
        else:
            # The API call itself returned an error status
            logger.error(f"User '{args.username}' creation API call failed with status {api_response.get('status')}. API Response: {api_response}")
            # Return the error structure provided by call_api
            return api_response

    except Exception as e:
        logger.error(f"Exception during user creation for '{args.username}': {e}. Payload: {payload}", exc_info=True)
        # This catch block handles exceptions from call_api or processing its result
        error_message = str(e)
        # Attempt to extract a more specific message if the exception has one
        if hasattr(e, 'args') and e.args:
            if isinstance(e.args[0], dict) and 'message' in e.args[0]:
                error_message = e.args[0]['message']
            elif isinstance(e.args[0], str):
                 error_message = e.args[0]
        return {"status": "error", "message": f"Exception during user creation: {error_message}", "details": str(e)}


def create_device_posture_tool(args: CreateDevicePostureArgs) -> Dict[str, Any]:
    """
    Creates a new Device Posture policy.
    Corresponds to POST /api/v1/device-postures.
    The request body is DevicePostureRequest.
    """
    logger.info(f"Attempting to create device posture policy '{args.name}'.")

    payload = args.model_dump(by_alias=True, exclude_none=True)
    api_path = "/api/v1/device-postures"

    try:
        response_data = call_api(action="post", path=api_path, value=payload)
        
        created_id = response_data.get("id")
        created_name = response_data.get("name") 

        if created_id and created_name:
            logger.info(f"Successfully created device posture policy '{created_name}' (ID: {created_id}). API Response: {response_data}")
            CURRENT_SELECTED_OBJECT.select(
                object_type="deviceposture", 
                object_id=created_id,
                object_name=created_name,
                details=response_data 
            )
            logger.info(f"Newly created device posture policy '{created_name}' (ID: {created_id}) has been selected.")
            return response_data 
        else:
            logger.warning(f"Device posture policy '{args.name}' creation API call successful, but 'id' or 'name' not found in response. Cannot select. Response: {response_data}")
            return {"status": "warning", "message": "Device posture policy created but ID or name not found in response.", "data": response_data}

    except Exception as e:
        logger.error(f"Exception during device posture policy creation for '{args.name}': {e}. Payload: {payload}", exc_info=True)
        error_message = str(e)
        if hasattr(e, 'args') and e.args:
            if isinstance(e.args[0], dict) and 'message' in e.args[0]:
                error_message = e.args[0]['message']
            elif isinstance(e.args[0], str):
                 error_message = e.args[0]
        return {"status": "error", "message": f"Exception during device posture policy creation: {error_message}", "details": str(e)}


def create_location_context_tool(args: CreateLocationContextArgs) -> Dict[str, Any]:
    """
    Creates a new Location Context policy.
    Corresponds to POST /api/v1/location-contexts.
    The request body is LocationContextRequest.
    """
    logger.info(f"Attempting to create location context policy '{args.name}'.")

    payload = args.model_dump(by_alias=True, exclude_none=True)
    api_path = "/api/v1/location-contexts"

    try:
        response_data = call_api(action="post", path=api_path, value=payload)
        
        created_id = response_data.get("id")
        created_name = response_data.get("name") 

        if created_id and created_name:
            logger.info(f"Successfully created location context policy '{created_name}' (ID: {created_id}). API Response: {response_data}")
            CURRENT_SELECTED_OBJECT.select(
                object_type="locationcontext", 
                object_id=created_id,
                object_name=created_name,
                details=response_data 
            )
            logger.info(f"Newly created location context policy '{created_name}' (ID: {created_id}) has been selected.")
            return response_data 
        else:
            logger.warning(f"Location context policy '{args.name}' creation API call successful, but 'id' or 'name' not found in response. Cannot select. Response: {response_data}")
            return {"status": "warning", "message": "Location context policy created but ID or name not found in response.", "data": response_data}

    except Exception as e:
        logger.error(f"Exception during location context policy creation for '{args.name}': {e}. Payload: {payload}", exc_info=True)
        error_message = str(e)
        if hasattr(e, 'args') and e.args:
            if isinstance(e.args[0], dict) and 'message' in e.args[0]:
                error_message = e.args[0]['message']
            elif isinstance(e.args[0], str):
                 error_message = e.args[0]
        return {"status": "error", "message": f"Exception during location context policy creation: {error_message}", "details": str(e)}


def create_access_group_tool(args: CreateAccessGroupArgs) -> Dict[str, Any]:
    """
    Creates a new Access Group.
    Corresponds to POST /api/v1/access-groups.
    The request body is AccessGroupRequest.
    """
    logger.info(f"Attempting to create access group '{args.name}'.")

    payload = args.model_dump(by_alias=True, exclude_none=True)
    api_path = "/api/v1/access-groups"

    try:
        response_data = call_api(action="post", path=api_path, value=payload)
        
        created_id = response_data.get("id")
        created_name = response_data.get("name") 

        if created_id and created_name:
            logger.info(f"Successfully created access group '{created_name}' (ID: {created_id}). API Response: {response_data}")
            CURRENT_SELECTED_OBJECT.select(
                object_type="accessgroup", 
                object_id=created_id,
                object_name=created_name,
                details=response_data 
            )
            logger.info(f"Newly created access group '{created_name}' (ID: {created_id}) has been selected.")
            return response_data 
        else:
            logger.warning(f"Access group '{args.name}' creation API call successful, but 'id' or 'name' not found in response. Cannot select. Response: {response_data}")
            return {"status": "warning", "message": "Access group created but ID or name not found in response.", "data": response_data}

    except Exception as e:
        logger.error(f"Exception during access group creation for '{args.name}': {e}. Payload: {payload}", exc_info=True)
        error_message = str(e)
        if hasattr(e, 'args') and e.args:
            if isinstance(e.args[0], dict) and 'message' in e.args[0]:
                error_message = e.args[0]['message']
            elif isinstance(e.args[0], str):
                 error_message = e.args[0]
        return {"status": "error", "message": f"Exception during access group creation: {error_message}", "details": str(e)}


def create_device_tool(args: CreateDeviceArgs) -> Dict[str, Any]:
    """
    Creates a new Device for a given User.
    Corresponds to POST /api/v1/devices?userId={userId}
    The request body is DeviceRequest.
    """
    logger.info(f"Attempting to create device '{args.name}' for user '{args.user_id}'.")

    # user_id is part of the query, not the body.
    payload_args = args.model_dump(exclude={"user_id"}, by_alias=True, exclude_none=True)
    
    api_path = f"/api/v1/devices?userId={args.user_id}"

    try:
        response_data = call_api(action="post", path=api_path, value=payload_args)
        
        created_id = response_data.get("id")
        created_name = response_data.get("name") 

        if created_id and created_name:
            logger.info(f"Successfully created device '{created_name}' (ID: {created_id}). API Response: {response_data}")
            CURRENT_SELECTED_OBJECT.select(
                object_type="device", 
                object_id=created_id,
                object_name=created_name,
                details=response_data 
            )
            logger.info(f"Newly created device '{created_name}' (ID: {created_id}) has been selected.")
            return response_data 
        else:
            logger.warning(f"Device '{args.name}' creation API call successful, but 'id' or 'name' not found in response. Cannot select. Response: {response_data}")
            return {"status": "warning", "message": "Device created but ID or name not found in response.", "data": response_data}

    except Exception as e:
        logger.error(f"Exception during device creation for '{args.name}': {e}. Payload: {payload_args}", exc_info=True)
        error_message = str(e)
        if hasattr(e, 'args') and e.args:
            if isinstance(e.args[0], dict) and 'message' in e.args[0]:
                error_message = e.args[0]['message']
            elif isinstance(e.args[0], str):
                 error_message = e.args[0]
        return {"status": "error", "message": f"Exception during device creation: {error_message}", "details": str(e)}


def create_dns_record_tool(args: CreateDnsRecordArgs) -> Dict[str, Any]:
    """
    Creates a new DNS Record.
    Corresponds to POST /api/v1/dns-records.
    The request body is DnsRecordRequest.
    """
    logger.info(f"Attempting to create DNS record for domain '{args.domain}'.")

    payload = args.model_dump(by_alias=True, exclude_none=True)
    api_path = "/api/v1/dns-records"

    try:
        response_data = call_api(action="post", path=api_path, value=payload)
        
        created_id = response_data.get("id")
        created_domain = response_data.get("domain") 

        if created_id and created_domain:
            logger.info(f"Successfully created DNS record for '{created_domain}' (ID: {created_id}). API Response: {response_data}")
            CURRENT_SELECTED_OBJECT.select(
                object_type="dnsrecord", 
                object_id=created_id,
                object_name=created_domain, # Use domain as name for DNS records
                details=response_data 
            )
            logger.info(f"Newly created DNS record '{created_domain}' (ID: {created_id}) has been selected.")
            return response_data 
        else:
            logger.warning(f"DNS record for '{args.domain}' creation API call successful, but 'id' or 'domain' not found in response. Cannot select. Response: {response_data}")
            return {"status": "warning", "message": "DNS record created but ID or domain not found in response.", "data": response_data}

    except Exception as e:
        logger.error(f"Exception during DNS record creation for '{args.domain}': {e}. Payload: {payload}", exc_info=True)
        error_message = str(e)
        if hasattr(e, 'args') and e.args:
            if isinstance(e.args[0], dict) and 'message' in e.args[0]:
                error_message = e.args[0]['message']
            elif isinstance(e.args[0], str):
                 error_message = e.args[0]
        return {"status": "error", "message": f"Exception during DNS record creation: {error_message}", "details": str(e)}


def create_host_connector_tool(args: CreateHostConnectorArgs) -> Dict[str, Any]:
    """
    Creates a new Host Connector within a specified Host.
    Corresponds to POST /api/v1/hosts/connectors?hostId={hostId}
    The request body is HostConnectorRequest.
    """
    logger.info(f"Attempting to create host connector '{args.name}' for host '{args.host_id}'.")

    # host_id is part of the query, not the body.
    payload_args = args.model_dump(exclude={"host_id"}, by_alias=True, exclude_none=True)
    
    api_path = f"/api/v1/hosts/connectors?hostId={args.host_id}"

    try:
        response_data = call_api(action="post", path=api_path, value=payload_args)
        
        created_id = response_data.get("id")
        created_name = response_data.get("name") 

        if created_id and created_name:
            logger.info(f"Successfully created host connector '{created_name}' (ID: {created_id}). API Response: {response_data}")
            CURRENT_SELECTED_OBJECT.select(
                object_type="hostconnector", 
                object_id=created_id,
                object_name=created_name,
                details=response_data 
            )
            logger.info(f"Newly created host connector '{created_name}' (ID: {created_id}) has been selected.")

            # --- Provision the connector in AWS ---
            logger.info(f"Attempting to provision AWS resources for host connector '{created_name}' (ID: {created_id}).")

            # Fetch the OpenVPN profile content for the newly created connector
            profile_api_path = f"/api/v1/connectors/{created_id}/profile" # Assuming this is the correct API path
            logger.info(f"Fetching profile from API: {profile_api_path}")
            profile_response = call_api(action="get", path=profile_api_path)

            openvpn_profile_content = None
            if isinstance(profile_response, dict) and profile_response.get("status", 0) >= 200 and profile_response.get("status", 0) < 300:
                 openvpn_profile_content = profile_response.get("data")
                 if openvpn_profile_content:
                     logger.info(f"Successfully fetched OpenVPN profile for host connector '{created_name}'.")
                 else:
                     logger.warning(f"Fetched profile data is empty for host connector '{created_name}'. Profile API Response: {profile_response}")
            else:
                 logger.error(f"Failed to fetch OpenVPN profile for host connector '{created_name}'. Profile API Response: {profile_response}")
                 # Continue without provisioning if profile fetch fails

            if openvpn_profile_content:
                # Call the provisioning tool
                provisioning_result = upsert_regional_egress(
                    prefix=created_name, # Use connector name as prefix
                    public=True, # Assuming public egress based on task context
                    region_id=None, # Use region from .env as per user instruction
                    openvpn_profile_content=openvpn_profile_content
                )
                logger.info(f"Provisioning result for host connector '{created_name}': {provisioning_result}")
                # You might want to include provisioning_result in the return value or log it differently
            else:
                logger.warning(f"Skipping AWS provisioning for host connector '{created_name}' due to missing OpenVPN profile content.")

            return response_data 
        else:
            logger.warning(f"Host connector '{args.name}' creation API call successful, but 'id' or 'name' not found in response. Cannot select. Response: {response_data}")
            return {"status": "warning", "message": "Host connector created but ID or name not found in response.", "data": response_data}

    except Exception as e:
        logger.error(f"Exception during host connector creation for '{args.name}': {e}. Payload: {payload_args}", exc_info=True)
        error_message = str(e)
        if hasattr(e, 'args') and e.args:
            if isinstance(e.args[0], dict) and 'message' in e.args[0]:
                error_message = e.args[0]['message']
            elif isinstance(e.args[0], str):
                 error_message = e.args[0]
        return {"status": "error", "message": f"Exception during host connector creation: {error_message}", "details": str(e)}


def create_host_tool(args: CreateHostArgs) -> Dict[str, Any]:
    """
    Creates a new Host.
    Corresponds to POST /api/v1/hosts.
    """
    logger.info(f"Attempting to create host '{args.name}'.")

    payload = args.model_dump(by_alias=True, exclude_none=True)
    api_path = "/api/v1/hosts"

    try:
        response_data = call_api(action="post", path=api_path, value=payload)
        
        created_id = response_data.get("id")
        created_name = response_data.get("name") 

        if created_id and created_name:
            logger.info(f"Successfully created host '{created_name}' (ID: {created_id}). API Response: {response_data}")
            CURRENT_SELECTED_OBJECT.select(
                object_type="host", 
                object_id=created_id,
                object_name=created_name,
                details=response_data 
            )
            logger.info(f"Newly created host '{created_name}' (ID: {created_id}) has been selected.")
            return response_data 
        else:
            logger.warning(f"Host '{args.name}' creation API call successful, but 'id' or 'name' not found in response. Cannot select. Response: {response_data}")
            return {"status": "warning", "message": "Host created but ID or name not found in response.", "data": response_data}

    except Exception as e:
        logger.error(f"Exception during host creation for '{args.name}': {e}. Payload: {payload}", exc_info=True)
        error_message = str(e)
        if hasattr(e, 'args') and e.args:
            if isinstance(e.args[0], dict) and 'message' in e.args[0]:
                error_message = e.args[0]['message']
            elif isinstance(e.args[0], str):
                 error_message = e.args[0]
        return {"status": "error", "message": f"Exception during host creation: {error_message}", "details": str(e)}


def create_user_group_tool(args: CreateUserGroupArgs) -> Dict[str, Any]:
    """
    Creates a new User Group.
    Corresponds to POST /api/v1/user-groups.
    """
    logger.info(f"Attempting to create user group '{args.name}'.")

    payload = args.model_dump(by_alias=True, exclude_none=True)
    api_path = "/api/v1/user-groups"

    try:
        response_data = call_api(action="post", path=api_path, value=payload) # This is the full API response object
        
        # The actual user group data is expected to be in response_data["data"]
        api_response_status = response_data.get("status") if isinstance(response_data, dict) else "Unknown"
        actual_group_data = response_data.get("data") if isinstance(response_data, dict) else None

        if actual_group_data and isinstance(actual_group_data, dict):
            created_id = actual_group_data.get("id")
            created_name = actual_group_data.get("name")

            if created_id and created_name:
                # Success case: API call was successful and we found id/name in the nested data
                logger.info(f"Successfully created user group '{created_name}' (ID: {created_id}). API Response data: {actual_group_data}")
                CURRENT_SELECTED_OBJECT.select(
                    object_type="usergroup", 
                    object_id=created_id,
                    object_name=created_name,
                    details=actual_group_data 
                )
                logger.info(f"Newly created user group '{created_name}' (ID: {created_id}) has been selected.")
                # Return the actual group data object, not the whole API response
                return actual_group_data 
            else:
                # API call might have been "successful" (e.g., 201 status) but id/name missing in actual_group_data
                logger.warning(f"User group '{args.name}' creation API call reported status {api_response_status}, but 'id' or 'name' not found in the 'data' field. Actual data: {actual_group_data}. Full API Response: {response_data}")
                # Return a warning structure, but include the full API response for debugging
                return {"status": "warning", "message": "User group created (API success) but ID or name not found in its data payload.", "details": response_data}
        else:
            # The structure of response_data was not as expected (e.g., no "data" field or "data" is not a dict)
            logger.warning(f"User group '{args.name}' creation API call reported status {api_response_status}, but the response format was unexpected (e.g., 'data' field missing or not a dict). Full API Response: {response_data}")
            return {"status": "warning", "message": "User group created (API success) but API response format was unexpected.", "details": response_data}

    except Exception as e:
        logger.error(f"Exception during user group creation for '{args.name}': {e}. Payload: {payload}", exc_info=True)
        error_message = str(e)
        if hasattr(e, 'args') and e.args:
            if isinstance(e.args[0], dict) and 'message' in e.args[0]:
                error_message = e.args[0]['message']
            elif isinstance(e.args[0], str):
                 error_message = e.args[0]
        return {"status": "error", "message": f"Exception during user group creation: {error_message}", "details": str(e)}


def create_network_connector_tool(args: CreateNetworkConnectorArgs) -> Dict[str, Any]:
    """
    Creates a new Network Connector within a specified Network.
    Corresponds to POST /api/v1/networks/connectors?networkId={networkId}
    The request body is NetworkConnectorRequest.
    """
    logger.info(f"Attempting to create network connector '{args.name}' in network '{args.network_id}'.")

    # network_id is part of the path/query, not the body for this specific API endpoint.
    # The body will be built from other fields.
    payload_args = args.model_dump(exclude={"network_id"}, by_alias=True, exclude_none=True)


    api_path = f"/api/v1/networks/connectors?networkId={args.network_id}"
    
    try:
        response_data = call_api(action="post", path=api_path, value=payload_args)
        
        created_id = response_data.get("id")
        created_name = response_data.get("name") 

        if created_id and created_name:
            logger.info(f"Successfully created network connector '{created_name}' (ID: {created_id}). API Response: {response_data}")
            CURRENT_SELECTED_OBJECT.select(
                object_type="networkconnector", 
                object_id=created_id,
                object_name=created_name,
                details=response_data 
            )
            logger.info(f"Newly created network connector '{created_name}' (ID: {created_id}) has been selected.")

            # --- Provision the connector in AWS ---
            logger.info(f"Attempting to provision AWS resources for connector '{created_name}' (ID: {created_id}).")
            
            # Fetch the OpenVPN profile content for the newly created connector
            profile_api_path = f"/api/v1/connectors/{created_id}/profile" # Assuming this is the correct API path
            logger.info(f"Fetching profile from API: {profile_api_path}")
            profile_response = call_api(action="get", path=profile_api_path)

            openvpn_profile_content = None
            if isinstance(profile_response, dict) and profile_response.get("status", 0) >= 200 and profile_response.get("status", 0) < 300:
                 openvpn_profile_content = profile_response.get("data")
                 if openvpn_profile_content:
                     logger.info(f"Successfully fetched OpenVPN profile for connector '{created_name}'.")
                 else:
                     logger.warning(f"Fetched profile data is empty for connector '{created_name}'. Profile API Response: {profile_response}")
            else:
                 logger.error(f"Failed to fetch OpenVPN profile for connector '{created_name}'. Profile API Response: {profile_response}")
                 # Continue without provisioning if profile fetch fails

            if openvpn_profile_content:
                # Call the provisioning tool
                provisioning_result = upsert_regional_egress(
                    prefix=created_name, # Use connector name as prefix
                    public=True, # Assuming public egress based on task context
                    region_id=None, # Use region from .env as per user instruction
                    openvpn_profile_content=openvpn_profile_content
                )
                logger.info(f"Provisioning result for connector '{created_name}': {provisioning_result}")
                # You might want to include provisioning_result in the return value or log it differently
            else:
                logger.warning(f"Skipping AWS provisioning for connector '{created_name}' due to missing OpenVPN profile content.")

            return response_data 
        else:
            logger.warning(f"Network connector '{args.name}' creation API call successful, but 'id' or 'name' not found in response. Cannot select. Response: {response_data}")
            return {"status": "warning", "message": "Network connector created but ID or name not found in response.", "data": response_data}

    except Exception as e:
        logger.error(f"Exception during network connector creation for '{args.name}': {e}. Payload: {payload_args}", exc_info=True)
        error_message = str(e)
        if hasattr(e, 'args') and e.args:
            if isinstance(e.args[0], dict) and 'message' in e.args[0]:
                error_message = e.args[0]['message']
            elif isinstance(e.args[0], str):
                 error_message = e.args[0]
        return {"status": "error", "message": f"Exception during network connector creation: {error_message}", "details": str(e)}

    
    # To actually run:
    # from connexa_openvpn_mcp_server.connexa.config_manager import initialize_config
    # if initialize_config():
    #     logger.info("Config initialized.")
    #     result = create_network_tool(test_network_args)
    #     logger.info(f"Result of create_network_tool: {result}")
    # else:
    #     logger.error("Failed to initialize config. Cannot run live test.")
