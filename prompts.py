import mcp.types as types

# Source data for the guidelines
CONNEXA_API_GUIDELINES = [
    {
        "id": "update_strategy",
        "text": "When updating an item (e.g., user, device, group), always follow this pattern: 1. First, use the 'get_<item>' tool to fetch the current details of the item. 2. Modify the retrieved JSON object with the desired changes. 3. Finally, pass the entire updated JSON object to the 'update_<item>' tool."
    },
    {
        "id": "user_group_association",
        "text": "Users belong to one user_group. If no specific group is assigned, they are typically part of a 'Default' user group. Check the 'groupId' field in user details and use 'get_user_group' to find group information."
    },
    {
        "id": "user_device_relationship",
        "text": "Users may have multiple devices. Devices can also be associated with users. Use 'get_devices' (optionally with a 'user_id') to list devices. Device details can be fetched with 'get_device_details'."
    },
    {
        "id": "networks_connectors_resources_prompt", # Renamed id for clarity
        "text": "The concept of 'networks' in OpenVPN Connexa often involves 'connectors'. Connectors can be thought of as autologin users or specific configurations that provide access to a resource (e.g., a printer, NAS, or an internal service). Managing these might involve specific tools or configurations related to network services or routes, though direct 'network' or 'connector' tools might not be explicitly listed and could be part of broader configurations like 'Hosts' or 'Services' if available."
    },
    {
        "id": "pagination_awareness",
        "text": "Many listing operations (e.g., get_users, get_devices, get_user_groups) are paginated. Use the 'page' (0-indexed) and 'size' (default 10, typically 1-1000) parameters to retrieve all items. Check responses for fields like 'totalElements', 'totalPages', and 'numberOfElements' to manage pagination."
    },
    {
        "id": "regions_concept",
        "text": "Regions are geographic points-of-presence for Cloud Connexa. A 'regionId' is often required when creating resources like Connectors or generating Device profiles (e.g., for 'generate_device_profile'). The API endpoint /api/v1/regions (getVpnRegions) lists available regions."
    },
    {
        "id": "device_posture_overview",
        "text": "Device Posture policies enforce security rules for devices (checking OS version, antivirus, disk encryption, certificates). Policies are created and then can be associated with User Groups. Relevant tools include 'get_device_posture_policies', 'create_device_posture_policy', 'get_device_posture_policy_details', 'update_device_posture_policy_details', and 'delete_device_posture_policy_record'."
    },
    {
        "id": "dns_log_functionality",
        "text": "DNS Log tools ('enable_dns_log', 'disable_dns_log', 'get_user_dns_resolutions') allow managing and retrieving DNS resolution logs. 'get_user_dns_resolutions' requires 'startHour' (ISO 8601 format, UTC) and can use 'hoursBack' (1 or 2), 'page', and 'size' for querying logs."
    },
    {
        "id": "access_groups_concept",
        "text": "Access Groups are a key OpenVPN Connexa feature for defining access control by linking Sources (who: User Groups, Networks, Hosts) to Destinations (what: Network Services, Host Services). While specific MCP tools for direct Access Group management might not be listed, understanding this concept is vital for network security design."
    },
    {
        "id": "networks_hosts_connectors_concept_detail", # Renamed id for clarity
        "text": "Networks and Hosts represent your private infrastructure. They use Connectors (OpenVPN or IPsec) to link to Cloud Connexa. Routes, IP services, and applications can be defined within them. The API offers extensive management for these entities, which may be partially exposed via MCP tools."
    },
    {
        "id": "user_attributes_roles_auth",
        "text": "Users have key attributes like 'role' (OWNER, MEMBER, ADMIN) defining permissions, and 'authType' (INTERNAL, SAML, LDAP, GOOGLE, MICROSOFT) indicating their authentication method. Status can be INVITED, ACTIVE, SUSPENDED, etc."
    },
    {
        "id": "device_attributes_status_platform",
        "text": "Devices have attributes like 'name', 'description', 'clientUUID', and report 'platform' (OS, version) and 'connectionStatus' (ONLINE, OFFLINE, ONLINE_WITH_ISSUES). Each device is associated with a 'userId'."
    },
    {
        "id": "profile_management",
        "text": "For Devices and Connectors (Network/Host based), .ovpn profiles can be managed. 'generate_device_profile' (needs userId, deviceId, regionId) creates a profile. 'revoke_device_profile' deactivates it. Similar operations exist for connectors."
    },
    {
        "id": "settings_api_overview",
        "text": "The OpenVPN Connexa API includes numerous 'Settings' endpoints for configuring global WPC aspects like topology, subnets, DNS (zones, proxy, suffix, custom servers), and authentication (2FA, trusted devices). Refer to the API documentation for specifics if direct MCP tools are not available for a particular setting."
    },
    {
        "id": "user_group_settings",
        "text": "User Groups allow bulk management of settings like 'internetAccess' (SPLIT_TUNNEL_ON, SPLIT_TUNNEL_OFF, RESTRICTED_INTERNET), 'maxDevice', 'connectAuth' (NO_AUTH, ON_PRIOR_AUTH, EVERY_TIME), 'vpnRegionIds', and 'allRegionsIncluded'."
    },
    {
        "id": "cyber_shield_domain_filtering_api",
        "text": "The API supports Cyber Shield for DNS-based domain filtering, allowing management of block lists and allow lists (e.g., blockListAddDomains, allowListRemoveDomains). This provides an additional layer of security by controlling access to websites based on their domain names."
    }
]

_formatted_guidelines_text = "OpenVPN Connexa API Interaction Guidelines:\n\n" + \
                             "\n\n".join([f"- {p['id']}: {p['text']}" for p in CONNEXA_API_GUIDELINES])

async def list_guideline_prompts() -> list[types.Prompt]:
    """Lists available guideline prompts for OpenVPN Connexa."""
    return [
        types.Prompt(
            name="connexa_api_guidelines",
            description="Provides a set of guidelines and important concepts for interacting with the OpenVPN Connexa API via MCP tools.",
            arguments=[], # This prompt takes no arguments
        )
    ]

async def get_guideline_prompt(name: str, arguments: dict[str, str] | None = None) -> types.GetPromptResult:
    """Retrieves the specified guideline prompt."""
    if name == "connexa_api_guidelines":
        return types.GetPromptResult(
            messages=[
                types.PromptMessage(
                    role="user", # Changed to "user" as "system" might not be a valid Role for PromptMessage
                    content=types.TextContent(type="text", text=_formatted_guidelines_text)
                )
            ],
            # No specific model or parameters needed for this system message prompt
        )
    else:
        raise ValueError(f"Unknown prompt name: {name}")
