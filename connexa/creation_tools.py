# connexa_openvpn_mcp_server/connexa/creation_tools.py
import logging
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field

from .connexa_api import call_api
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
    groupId: str = Field(..., description="ID of the group the user belongs to.")
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
        response = call_api(action="post", path=api_path, value=payload)
        if response.get("status") == 201: # HTTP 201 Created
            logger.info(f"Successfully created network '{args.name}'. Response: {response}")
        else:
            logger.error(f"Failed to create network '{args.name}'. Payload: {payload}, Response: {response}")
        return response
    except Exception as e:
        logger.error(f"Exception during network creation for '{args.name}': {e}. Payload: {payload}", exc_info=True)
        return {"status": "error", "message": f"Exception during network creation: {str(e)}", "details": str(e)}

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
        response = call_api(action="post", path=api_path, value=payload)
        if response.get("status") == 200:  # Swagger shows 200 OK for this POST
            logger.info(f"Successfully created device posture policy '{args.name}'. Response: {response}")
        else:
            logger.error(f"Failed to create device posture policy '{args.name}'. Payload: {payload}, Response: {response}")
        return response
    except Exception as e:
        logger.error(f"Exception during device posture policy creation for '{args.name}': {e}. Payload: {payload}", exc_info=True)
        return {"status": "error", "message": f"Exception during device posture policy creation: {str(e)}", "details": str(e)}


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
        response = call_api(action="post", path=api_path, value=payload)
        if response.get("status") == 200: # Swagger shows 200 OK for this POST
            logger.info(f"Successfully created location context policy '{args.name}'. Response: {response}")
        else:
            logger.error(f"Failed to create location context policy '{args.name}'. Payload: {payload}, Response: {response}")
        return response
    except Exception as e:
        logger.error(f"Exception during location context policy creation for '{args.name}': {e}. Payload: {payload}", exc_info=True)
        return {"status": "error", "message": f"Exception during location context policy creation: {str(e)}", "details": str(e)}


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
        response = call_api(action="post", path=api_path, value=payload)
        if response.get("status") == 201:  # HTTP 201 Created
            logger.info(f"Successfully created access group '{args.name}'. Response: {response}")
        else:
            logger.error(f"Failed to create access group '{args.name}'. Payload: {payload}, Response: {response}")
        return response
    except Exception as e:
        logger.error(f"Exception during access group creation for '{args.name}': {e}. Payload: {payload}", exc_info=True)
        return {"status": "error", "message": f"Exception during access group creation: {str(e)}", "details": str(e)}


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
        response = call_api(action="post", path=api_path, value=payload_args)
        if response.get("status") == 201:  # HTTP 201 Created
            logger.info(f"Successfully created device '{args.name}'. Response: {response}")
        else:
            logger.error(f"Failed to create device '{args.name}'. Payload: {payload_args}, Response: {response}")
        return response
    except Exception as e:
        logger.error(f"Exception during device creation for '{args.name}': {e}. Payload: {payload_args}", exc_info=True)
        return {"status": "error", "message": f"Exception during device creation: {str(e)}", "details": str(e)}


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
        response = call_api(action="post", path=api_path, value=payload)
        if response.get("status") == 201:  # HTTP 201 Created
            logger.info(f"Successfully created DNS record for '{args.domain}'. Response: {response}")
        else:
            logger.error(f"Failed to create DNS record for '{args.domain}'. Payload: {payload}, Response: {response}")
        return response
    except Exception as e:
        logger.error(f"Exception during DNS record creation for '{args.domain}': {e}. Payload: {payload}", exc_info=True)
        return {"status": "error", "message": f"Exception during DNS record creation: {str(e)}", "details": str(e)}


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
        response = call_api(action="post", path=api_path, value=payload_args)
        if response.get("status") == 201:  # HTTP 201 Created
            logger.info(f"Successfully created host connector '{args.name}'. Response: {response}")
        else:
            logger.error(f"Failed to create host connector '{args.name}'. Payload: {payload_args}, Response: {response}")
        return response
    except Exception as e:
        logger.error(f"Exception during host connector creation for '{args.name}': {e}. Payload: {payload_args}", exc_info=True)
        return {"status": "error", "message": f"Exception during host connector creation: {str(e)}", "details": str(e)}


def create_host_tool(args: CreateHostArgs) -> Dict[str, Any]:
    """
    Creates a new Host.
    Corresponds to POST /api/v1/hosts.
    """
    logger.info(f"Attempting to create host '{args.name}'.")

    payload = args.model_dump(by_alias=True, exclude_none=True)
    api_path = "/api/v1/hosts"

    try:
        response = call_api(action="post", path=api_path, value=payload)
        if response.get("status") == 201:  # HTTP 201 Created
            logger.info(f"Successfully created host '{args.name}'. Response: {response}")
        else:
            logger.error(f"Failed to create host '{args.name}'. Payload: {payload}, Response: {response}")
        return response
    except Exception as e:
        logger.error(f"Exception during host creation for '{args.name}': {e}. Payload: {payload}", exc_info=True)
        return {"status": "error", "message": f"Exception during host creation: {str(e)}", "details": str(e)}


def create_user_group_tool(args: CreateUserGroupArgs) -> Dict[str, Any]:
    """
    Creates a new User Group.
    Corresponds to POST /api/v1/user-groups.
    """
    logger.info(f"Attempting to create user group '{args.name}'.")

    payload = args.model_dump(by_alias=True, exclude_none=True)
    api_path = "/api/v1/user-groups"

    try:
        response = call_api(action="post", path=api_path, value=payload)
        if response.get("status") == 201:  # HTTP 201 Created
            logger.info(f"Successfully created user group '{args.name}'. Response: {response}")
        else:
            logger.error(f"Failed to create user group '{args.name}'. Payload: {payload}, Response: {response}")
        return response
    except Exception as e:
        logger.error(f"Exception during user group creation for '{args.name}': {e}. Payload: {payload}", exc_info=True)
        return {"status": "error", "message": f"Exception during user group creation: {str(e)}", "details": str(e)}


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
        response = call_api(action="post", path=api_path, value=payload_args)
        if response.get("status") == 201: # HTTP 201 Created
            logger.info(f"Successfully created network connector '{args.name}'. Response: {response}")
        else:
            logger.error(f"Failed to create network connector '{args.name}'. Payload: {payload_args}, Response: {response}")
        return response
    except Exception as e:
        logger.error(f"Exception during network connector creation for '{args.name}': {e}. Payload: {payload_args}", exc_info=True)
        return {"status": "error", "message": f"Exception during network connector creation: {str(e)}", "details": str(e)}

    
    # To actually run:
    # from connexa_openvpn_mcp_server.connexa.config_manager import initialize_config
    # if initialize_config():
    #     logger.info("Config initialized.")
    #     result = create_network_tool(test_network_args)
    #     logger.info(f"Result of create_network_tool: {result}")
    # else:
    #     logger.error("Failed to initialize config. Cannot run live test.")
