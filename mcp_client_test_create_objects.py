# To run this file correctly from the project root (c:/GitRepos/python-sdk):
# PS C:\GitRepos\python-sdk> uv run python -m connexa_openvpn_mcp_server.mcp_client_test_create_objects

import asyncio
import logging
import uuid
import os # Added for path operations
import json # Added for parsing JSON in TextContent
from contextlib import AsyncExitStack # Added for session management
from typing import Any, Dict

# Corrected imports based on mcp_client_tester.py
from mcp import ClientSession, StdioServerParameters
from mcp.types import CallToolResult, TextContent # Added TextContent
from mcp.client.stdio import stdio_client # Corrected import
from pydantic import AnyUrl # Added for type casting URI

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Use a logger instance
# init_fastmcp_logging = lambda: None # Placeholder removed, using standard logging

# Import creation tool argument models and user creation args
# These imports are assumed to be correct for the project structure,
# Pylance errors for these might be path configuration issues.
from connexa_openvpn_mcp_server.connexa.creation_tools import (
    CreateUserGroupArgs,
    CreateUserArgs, # Moved import here
    CreateNetworkArgs,
    CreateHostArgs, # Added for host creation test
    CreateAccessGroupArgs, # Added for access group test
    AccessItemSourceRequestModel, # Added for access group test
    AccessItemDestinationRequestModel, # Added for access group test
    CreateDnsRecordArgs, # Added for DNS record test
    CreateLocationContextArgs, # Added for location context test
    IpCheckRequestModel, # Added for location context test
    IpRequestModel, # Added for location context test
    CountryCheckRequestModel, # Added for location context test
    DefaultCheckRequestModel, # Added for location context test
    CreateDevicePostureArgs, # Added for device posture test
    WindowsRequestModel, # Added for device posture test
    VersionPolicyModel, # Added for device posture test
    DiskEncryptionModel, # Added for device posture test
    # Add other *Args models as we implement tests
)
# from connexa_openvpn_mcp_server.user_tools import CreateUserArgs # Removed from here

# SERVER_NAME is not used when calling tools on an established session
# SERVER_NAME = "OpenVPN-Connexa-Server"

async def test_create_user_group(session: ClientSession, region_id_to_use: str) -> str | None:
    """Tests creating a user group."""
    logger.info("\n--- Testing User Group Creation ---")
    group_name = f"test-group-{str(uuid.uuid4()).split('-')[0]}"
    try:
        args = CreateUserGroupArgs(
            name=group_name, 
            vpnRegionIds=[region_id_to_use], # Use alias directly for instantiation
            internetAccess="SPLIT_TUNNEL_ON", # Provide a default
            maxDevice=5, # Provide a default
            connectAuth="ON_PRIOR_AUTH", # Provide a default
            allRegionsIncluded=False, # Provide a default
            gatewaysIds=[] # Provide a default
        )
        logger.info(f"Attempting to create user group: {group_name} with region {region_id_to_use} and other defaults.")
        
        result: CallToolResult = await session.call_tool(
            "create_user_group_tool", 
            {"args": args.model_dump(by_alias=True, exclude_none=True)}, # Ensure by_alias=True for API call
        )
        logger.info(f"Raw tool call result from create_user_group_tool: {result}")

        if not result.isError:
            if result.content and len(result.content) > 0:
                first_content = result.content[0]
                if isinstance(first_content, TextContent):
                    payload_text = first_content.text
                    try:
                        payload_data = json.loads(payload_text)
                        # Check for API-level error even if tool call itself didn't error
                        if isinstance(payload_data, dict) and payload_data.get("status") == "error":
                            logger.error(f"API returned an error for user group '{group_name}': {payload_data.get('message', 'No message')}")
                            logger.error(f"API error details: {payload_data.get('details', 'No details')}")
                            return None
                        
                        # Access the nested ID: payload_data['data']['id']
                        if isinstance(payload_data, dict) and \
                           "data" in payload_data and \
                           isinstance(payload_data["data"], dict) and \
                           "id" in payload_data["data"]:
                            created_id = payload_data["data"]["id"]
                            logger.info(f"Successfully created user group '{group_name}' with ID: {created_id}")
                            return created_id
                        else:
                            logger.warning(f"User group '{group_name}' creation: TextContent received, but 'id' not found in parsed_data['data'] or structure is unexpected.")
                            logger.warning(f"Parsed JSON: {payload_data}")
                            return None
                    except json.JSONDecodeError:
                        logger.error(f"User group '{group_name}' creation: Failed to parse TextContent as JSON. Content: {payload_text}")
                        return None
                else:
                    logger.warning(f"User group '{group_name}' creation: Content is not TextContent. Content type: {type(first_content)}, Content: {first_content}")
                    return None
            else:
                logger.warning(f"User group '{group_name}' creation: No error reported by tool, but no content returned.")
                return None
        else:  # result.isError is True
            error_message = "Unknown error from tool."
            if result.content and len(result.content) > 0 and isinstance(result.content[0], TextContent):
                error_message = result.content[0].text
            logger.error(f"Tool 'create_user_group_tool' for '{group_name}' reported an error.") # Corrected tool name in log
            logger.error(f"Tool error message: {error_message}")
            logger.error(f"Full error content from tool: {result.content}")
            return None
    except Exception as e: # Catches JSON-RPC errors, network issues, etc.
        logger.error(f"An exception occurred during user group '{group_name}' creation: {e}", exc_info=True)
        return None

async def test_create_user(session: ClientSession, group_id: str | None) -> str | None:
    """Tests creating a user."""
    logger.info("\n--- Testing User Creation ---")
    if not group_id:
        logger.error("User creation skipped: No valid group_id provided.")
        return None

    user_name_prefix = f"test-user-{str(uuid.uuid4()).split('-')[0]}"
    args = None # Initialize args to None
    try:
        args = CreateUserArgs(
            firstName="Test",
            lastName="User",
            username=f"{user_name_prefix}",
            email=f"{user_name_prefix}@example.com",
            groupId=group_id,
            role="MEMBER"
        )
        logger.info(f"Attempting to create user: {args.username} in group {group_id}")
        
        # The create_user tool is defined in user_tools.py and registered with its function name
        result: CallToolResult = await session.call_tool(
            "create_user", 
            {"args": args.model_dump(exclude_none=True)},
        )
        logger.info(f"Raw tool call result from create_user: {result}")

        if not result.isError:
            if result.content and len(result.content) > 0:
                first_content = result.content[0]
                if isinstance(first_content, TextContent):
                    payload_text = first_content.text
                    try:
                        payload_data = json.loads(payload_text)
                        # User creation API returns the full user object, which has an 'id' field.
                        if isinstance(payload_data, dict) and "id" in payload_data:
                            created_id = payload_data["id"]
                            logger.info(f"Successfully created user '{args.username}' with ID: {created_id}")
                            return created_id
                        else:
                            logger.warning(f"User '{args.username}' creation: TextContent received, but 'id' not in parsed JSON or not a dict.")
                            logger.warning(f"Parsed JSON: {payload_data}")
                            return None
                    except json.JSONDecodeError:
                        logger.error(f"User '{args.username}' creation: Failed to parse TextContent as JSON. Content: {payload_text}")
                        return None
                else:
                    logger.warning(f"User '{args.username}' creation: Content is not TextContent. Content type: {type(first_content)}, Content: {first_content}")
                    return None
            else:
                logger.warning(f"User '{args.username}' creation: No error reported by tool, but no content returned.")
                return None
        else:  # result.isError is True
            error_message = "Unknown error from tool."
            if result.content and len(result.content) > 0 and isinstance(result.content[0], TextContent):
                error_message = result.content[0].text
            logger.error(f"Tool 'create_user' for '{args.username}' reported an error.")
            logger.error(f"Tool error message: {error_message}")
            logger.error(f"Full error content from tool: {result.content}")
            return None
    except Exception as e:
        username_for_log = user_name_prefix
        if args and hasattr(args, 'username'): # args is now guaranteed to be defined
            username_for_log = args.username
        logger.error(f"An exception occurred during user '{username_for_log}' creation: {e}", exc_info=True)
        return None

async def test_create_network(session: ClientSession) -> str | None:
    """Tests creating a network."""
    logger.info("\n--- Testing Network Creation ---")
    network_name = f"test-network-{str(uuid.uuid4()).split('-')[0]}"
    try:
        args = CreateNetworkArgs(
            name=network_name,
            description=None,
            internetAccess="SPLIT_TUNNEL_OFF", # Default to no internet for safety - using ALIAS
            egress=False, 
            routes=[],    
            connectors=[],
            tunnelingProtocol="OPENVPN", # Using ALIAS
            gatewaysIds=[] # Using ALIAS
        )
        logger.info(f"Attempting to create network: {network_name} with specified defaults.")
        
        # Tool name confirmed from server registration snippet
        result: CallToolResult = await session.call_tool(
            "create_network_tool", 
            {"args": args.model_dump(by_alias=True, exclude_none=True)},
        )
        logger.info(f"Raw tool call result from create_network_tool: {result}")

        if not result.isError:
            if result.content and len(result.content) > 0:
                first_content = result.content[0]
                if isinstance(first_content, TextContent):
                    payload_text = first_content.text
                    try:
                        payload_data = json.loads(payload_text)
                        # Check for API-level error or non-success status
                        # create_network_tool returns the API response dict.
                        # A successful creation is HTTP 201.
                        # The dict returned by the tool would be the API response.
                        # Response structure from logs: {'status': 201, 'data': {'id': '...'}}
                        if isinstance(payload_data, dict) and payload_data.get("status") == 201:
                            if "data" in payload_data and isinstance(payload_data["data"], dict) and "id" in payload_data["data"]:
                                created_id = payload_data["data"]["id"]
                                logger.info(f"Successfully created network '{network_name}' with ID: {created_id}")
                                return created_id
                            else:
                                logger.warning(f"Network '{network_name}' creation: Status 201, but 'id' not found in payload_data['data'] or structure is unexpected.")
                                logger.warning(f"Parsed JSON: {payload_data}")
                                return None
                        elif isinstance(payload_data, dict) and payload_data.get("status") == "error": # Custom error from tool wrapper
                            logger.error(f"Tool returned an error for network '{network_name}': {payload_data.get('message', 'No message')}")
                            logger.error(f"Tool error details: {payload_data.get('details', 'No details')}")
                            return None
                        else: # Other non-201 status or unexpected structure
                            logger.error(f"Network '{network_name}' creation: API did not return 201. Full response: {payload_data}")
                            return None
                    except json.JSONDecodeError:
                        logger.error(f"Network '{network_name}' creation: Failed to parse TextContent as JSON. Content: {payload_text}")
                        return None
                else:
                    logger.warning(f"Network '{network_name}' creation: Content is not TextContent. Content type: {type(first_content)}, Content: {first_content}")
                    return None
            else:
                logger.warning(f"Network '{network_name}' creation: No error reported by tool, but no content returned.")
                return None
        else:  # result.isError is True
            error_message = "Unknown error from tool."
            if result.content and len(result.content) > 0 and isinstance(result.content[0], TextContent):
                error_message = result.content[0].text
            logger.error(f"Tool 'create_network_tool' for '{network_name}' reported an error.")
            logger.error(f"Tool error message: {error_message}")
            logger.error(f"Full error content from tool: {result.content}")
            return None
    except Exception as e:
        logger.error(f"An exception occurred during network '{network_name}' creation: {e}", exc_info=True)
        return None

async def test_create_host(session: ClientSession) -> str | None:
    """Tests creating a host."""
    logger.info("\n--- Testing Host Creation ---")
    # network_id_param is removed as CreateHostArgs does not take it.

    host_name = f"test-host-{str(uuid.uuid4()).split('-')[0]}"
    try:
        args = CreateHostArgs(
            name=host_name,
            description=f"Test host {host_name}",
            internetAccess="SPLIT_TUNNEL_OFF", # Using alias for instantiation
            domain=f"{host_name}.test.local",    # No alias, use field name
            connectors=[],                       # No alias, use field name
            gatewaysIds=[]                      # Using alias for instantiation
        )
        logger.info(f"Attempting to create host: {host_name} with specified defaults.")
        
        # Assuming the tool for creating a host is named 'create_host_tool'
        result: CallToolResult = await session.call_tool(
            "create_host_tool", 
            {"args": args.model_dump(by_alias=True, exclude_none=True)},
        )
        logger.info(f"Raw tool call result from create_host_tool: {result}")

        if not result.isError:
            if result.content and len(result.content) > 0:
                first_content = result.content[0]
                if isinstance(first_content, TextContent):
                    payload_text = first_content.text
                    try:
                        payload_data = json.loads(payload_text)
                        # Assuming host creation success is status 201 and ID is in response.data.id
                        if isinstance(payload_data, dict) and payload_data.get("status") == 201:
                            if "data" in payload_data and isinstance(payload_data["data"], dict) and "id" in payload_data["data"]:
                                created_id = payload_data["data"]["id"]
                                logger.info(f"Successfully created host '{host_name}' with ID: {created_id}")
                                return created_id
                            else:
                                logger.warning(f"Host '{host_name}' creation: Status 201, but 'id' not found in payload_data['data'] or structure is unexpected.")
                                logger.warning(f"Parsed JSON: {payload_data}")
                                return None
                        elif isinstance(payload_data, dict) and payload_data.get("status") == "error": # Custom error from tool wrapper
                            logger.error(f"Tool returned an error for host '{host_name}': {payload_data.get('message', 'No message')}")
                            logger.error(f"Tool error details: {payload_data.get('details', 'No details')}")
                            return None
                        else: # Other non-201 status or unexpected structure
                            logger.error(f"Host '{host_name}' creation: API did not return 201 or expected success. Full response: {payload_data}")
                            return None
                    except json.JSONDecodeError:
                        logger.error(f"Host '{host_name}' creation: Failed to parse TextContent as JSON. Content: {payload_text}")
                        return None
                else:
                    logger.warning(f"Host '{host_name}' creation: Content is not TextContent. Content type: {type(first_content)}, Content: {first_content}")
                    return None
            else:
                logger.warning(f"Host '{host_name}' creation: No error reported by tool, but no content returned.")
                return None
        else:  # result.isError is True
            error_message = "Unknown error from tool."
            if result.content and len(result.content) > 0 and isinstance(result.content[0], TextContent):
                error_message = result.content[0].text
            logger.error(f"Tool 'create_host_tool' for '{host_name}' reported an error.")
            logger.error(f"Tool error message: {error_message}")
            logger.error(f"Full error content from tool: {result.content}")
            return None
    except Exception as e:
        logger.error(f"An exception occurred during host '{host_name}' creation: {e}", exc_info=True)
        return None

async def test_create_access_group(session: ClientSession) -> str | None:
    """Tests creating an access group."""
    logger.info("\n--- Testing Access Group Creation ---")
    access_group_name = f"test-access-group-{str(uuid.uuid4()).split('-')[0]}"
    try:
        # Define source and destination items for the access group
        # These are examples; actual values might depend on existing user groups, networks, hosts, etc.
        # For a basic test, we can use 'allCovered' or specific (but potentially non-existent) IDs.
        # Using 'allCovered' for simplicity in this initial test.
        source_items = [
            AccessItemSourceRequestModel(type="USER_GROUP", allCovered=True)
        ]
        destination_items = [
            AccessItemDestinationRequestModel(type="NETWORK_SERVICE", allCovered=True),
            AccessItemDestinationRequestModel(type="HOST_SERVICE", allCovered=True) # Corrected to HOST_SERVICE
        ]

        args = CreateAccessGroupArgs(
            name=access_group_name,
            description=f"Test access group {access_group_name}",
            source=source_items,
            destination=destination_items
        )
        logger.info(f"Attempting to create access group: {access_group_name} with specified defaults.")
        
        result: CallToolResult = await session.call_tool(
            "create_access_group_tool", 
            {"args": args.model_dump(by_alias=True, exclude_none=True)},
        )
        logger.info(f"Raw tool call result from create_access_group_tool: {result}")

        if not result.isError:
            if result.content and len(result.content) > 0:
                first_content = result.content[0]
                if isinstance(first_content, TextContent):
                    payload_text = first_content.text
                    try:
                        payload_data = json.loads(payload_text)
                        # Access group creation API returns 201 and the object with an 'id'.
                        # Based on create_network_tool, it might be nested under 'data'.
                        # Let's assume it's payload_data['data']['id'] for now.
                        # If the API returns the ID directly at the top level of the payload,
                        # this will need adjustment (e.g., payload_data.get("id")).
                        if isinstance(payload_data, dict) and payload_data.get("status") == 201:
                            if "data" in payload_data and isinstance(payload_data["data"], dict) and "id" in payload_data["data"]:
                                created_id = payload_data["data"]["id"]
                                logger.info(f"Successfully created access group '{access_group_name}' with ID: {created_id}")
                                return created_id
                            # Check if ID is directly in payload_data (alternative structure)
                            elif "id" in payload_data: # Check for direct ID if not in data.id
                                created_id = payload_data["id"]
                                logger.info(f"Successfully created access group '{access_group_name}' with ID: {created_id} (found directly in response).")
                                return created_id
                            else:
                                logger.warning(f"Access group '{access_group_name}' creation: Status 201, but 'id' not found in expected location (payload_data['data']['id'] or payload_data['id']).")
                                logger.warning(f"Parsed JSON: {payload_data}")
                                return None
                        elif isinstance(payload_data, dict) and payload_data.get("status") == "error": # Custom error from tool wrapper
                            logger.error(f"Tool returned an error for access group '{access_group_name}': {payload_data.get('message', 'No message')}")
                            logger.error(f"Tool error details: {payload_data.get('details', 'No details')}")
                            return None
                        else: # Other non-201 status or unexpected structure
                            logger.error(f"Access group '{access_group_name}' creation: API did not return 201 or expected success. Full response: {payload_data}")
                            return None
                    except json.JSONDecodeError:
                        logger.error(f"Access group '{access_group_name}' creation: Failed to parse TextContent as JSON. Content: {payload_text}")
                        return None
                else:
                    logger.warning(f"Access group '{access_group_name}' creation: Content is not TextContent. Content type: {type(first_content)}, Content: {first_content}")
                    return None
            else:
                logger.warning(f"Access group '{access_group_name}' creation: No error reported by tool, but no content returned.")
                return None
        else:  # result.isError is True
            error_message = "Unknown error from tool."
            if result.content and len(result.content) > 0 and isinstance(result.content[0], TextContent):
                error_message = result.content[0].text
            logger.error(f"Tool 'create_access_group_tool' for '{access_group_name}' reported an error.")
            logger.error(f"Tool error message: {error_message}")
            logger.error(f"Full error content from tool: {result.content}")
            return None
    except Exception as e:
        logger.error(f"An exception occurred during access group '{access_group_name}' creation: {e}", exc_info=True)
        return None

async def test_create_dns_record(session: ClientSession) -> str | None:
    """Tests creating a DNS record."""
    logger.info("\n--- Testing DNS Record Creation ---")
    domain_name = f"test-dns-{str(uuid.uuid4()).split('-')[0]}.example.com"
    try:
        args = CreateDnsRecordArgs(
            domain=domain_name,
            description=f"Test DNS record for {domain_name}",
            ipv4Addresses=["192.0.2.1"], # Using alias
            ipv6Addresses=[] # Using alias
        )
        logger.info(f"Attempting to create DNS record for domain: {domain_name}")
        
        result: CallToolResult = await session.call_tool(
            "create_dns_record_tool", 
            {"args": args.model_dump(by_alias=True, exclude_none=True)},
        )
        logger.info(f"Raw tool call result from create_dns_record_tool: {result}")

        if not result.isError:
            if result.content and len(result.content) > 0:
                first_content = result.content[0]
                if isinstance(first_content, TextContent):
                    payload_text = first_content.text
                    try:
                        payload_data = json.loads(payload_text)
                        # Assuming success is status 201 and ID is in response.data.id
                        if isinstance(payload_data, dict) and payload_data.get("status") == 201:
                            if "data" in payload_data and isinstance(payload_data["data"], dict) and "id" in payload_data["data"]:
                                created_id = payload_data["data"]["id"]
                                logger.info(f"Successfully created DNS record for '{domain_name}' with ID: {created_id}")
                                return created_id
                            else:
                                logger.warning(f"DNS record '{domain_name}' creation: Status 201, but 'id' not found in payload_data['data'] or structure is unexpected.")
                                logger.warning(f"Parsed JSON: {payload_data}")
                                return None
                        elif isinstance(payload_data, dict) and payload_data.get("status") == "error":
                            logger.error(f"Tool returned an error for DNS record '{domain_name}': {payload_data.get('message', 'No message')}")
                            logger.error(f"Tool error details: {payload_data.get('details', 'No details')}")
                            return None
                        else:
                            logger.error(f"DNS record '{domain_name}' creation: API did not return 201 or expected success. Full response: {payload_data}")
                            return None
                    except json.JSONDecodeError:
                        logger.error(f"DNS record '{domain_name}' creation: Failed to parse TextContent as JSON. Content: {payload_text}")
                        return None
                else:
                    logger.warning(f"DNS record '{domain_name}' creation: Content is not TextContent. Content type: {type(first_content)}, Content: {first_content}")
                    return None
            else:
                logger.warning(f"DNS record '{domain_name}' creation: No error reported by tool, but no content returned.")
                return None
        else:
            error_message = "Unknown error from tool."
            if result.content and len(result.content) > 0 and isinstance(result.content[0], TextContent):
                error_message = result.content[0].text
            logger.error(f"Tool 'create_dns_record_tool' for '{domain_name}' reported an error.")
            logger.error(f"Tool error message: {error_message}")
            logger.error(f"Full error content from tool: {result.content}")
            return None
    except Exception as e:
        logger.error(f"An exception occurred during DNS record '{domain_name}' creation: {e}", exc_info=True)
        return None

async def test_create_location_context(session: ClientSession) -> str | None:
    """Tests creating a location context policy."""
    logger.info("\n--- Testing Location Context Policy Creation ---")
    policy_name = f"test-location-policy-{str(uuid.uuid4()).split('-')[0]}"
    try:
        args = CreateLocationContextArgs(
            name=policy_name,
            description=f"Test location context policy {policy_name}",
            userGroupsIds=[], # Using alias
            ipCheck=IpCheckRequestModel( # Using alias
                allowed=True,
                ips=[IpRequestModel(ip="192.0.2.100/32", description="Test Allowed IP with subnet")]
            ),
            countryCheck=CountryCheckRequestModel( # Using alias
                countries=["US"], 
                allowed=True
            ),
            defaultCheck=DefaultCheckRequestModel(allowed=False) # Using alias
        )
        logger.info(f"Attempting to create location context policy: {policy_name}")
        
        result: CallToolResult = await session.call_tool(
            "create_location_context_tool", 
            {"args": args.model_dump(by_alias=True, exclude_none=True)},
        )
        logger.info(f"Raw tool call result from create_location_context_tool: {result}")

        if not result.isError:
            if result.content and len(result.content) > 0:
                first_content = result.content[0]
                if isinstance(first_content, TextContent):
                    payload_text = first_content.text
                    try:
                        payload_data = json.loads(payload_text)
                        # Assuming success is status 200 and ID is in response.data.id (as per creation_tools.py)
                        if isinstance(payload_data, dict) and payload_data.get("status") == 200:
                            if "data" in payload_data and isinstance(payload_data["data"], dict) and "id" in payload_data["data"]:
                                created_id = payload_data["data"]["id"]
                                logger.info(f"Successfully created location context policy '{policy_name}' with ID: {created_id}")
                                return created_id
                            else:
                                logger.warning(f"Location context policy '{policy_name}' creation: Status 200, but 'id' not found in payload_data['data'] or structure is unexpected.")
                                logger.warning(f"Parsed JSON: {payload_data}")
                                return None
                        elif isinstance(payload_data, dict) and payload_data.get("status") == "error":
                            logger.error(f"Tool returned an error for location context policy '{policy_name}': {payload_data.get('message', 'No message')}")
                            logger.error(f"Tool error details: {payload_data.get('details', 'No details')}")
                            return None
                        else:
                            logger.error(f"Location context policy '{policy_name}' creation: API did not return 200 or expected success. Full response: {payload_data}")
                            return None
                    except json.JSONDecodeError:
                        logger.error(f"Location context policy '{policy_name}' creation: Failed to parse TextContent as JSON. Content: {payload_text}")
                        return None
                else:
                    logger.warning(f"Location context policy '{policy_name}' creation: Content is not TextContent. Content type: {type(first_content)}, Content: {first_content}")
                    return None
            else:
                logger.warning(f"Location context policy '{policy_name}' creation: No error reported by tool, but no content returned.")
                return None
        else:
            error_message = "Unknown error from tool."
            if result.content and len(result.content) > 0 and isinstance(result.content[0], TextContent):
                error_message = result.content[0].text
            logger.error(f"Tool 'create_location_context_tool' for '{policy_name}' reported an error.")
            logger.error(f"Tool error message: {error_message}")
            logger.error(f"Full error content from tool: {result.content}")
            return None
    except Exception as e:
        logger.error(f"An exception occurred during location context policy '{policy_name}' creation: {e}", exc_info=True)
        return None

async def test_create_device_posture(session: ClientSession) -> str | None:
    """Tests creating a device posture policy."""
    logger.info("\n--- Testing Device Posture Policy Creation ---")
    policy_name = f"test-device-posture-{str(uuid.uuid4()).split('-')[0]}"
    try:
        args = CreateDevicePostureArgs(
            name=policy_name,
            description=f"Test device posture policy {policy_name}",
            userGroupsIds=[], # Using alias
            windows=WindowsRequestModel( # Using field name (no alias for 'windows' itself)
                allowed=True,
                version=VersionPolicyModel(version="10.0.0", condition="GTE"), # Field names
                antiviruses=["MICROSOFT_DEFENDER"], # Field name
                diskEncryption=DiskEncryptionModel(type="FULL_DISK") # Using alias for diskEncryption
            )
            # Add other OS policies as needed for more comprehensive tests
        )
        logger.info(f"Attempting to create device posture policy: {policy_name}")
        
        result: CallToolResult = await session.call_tool(
            "create_device_posture_tool", 
            {"args": args.model_dump(by_alias=True, exclude_none=True)},
        )
        logger.info(f"Raw tool call result from create_device_posture_tool: {result}")

        if not result.isError:
            if result.content and len(result.content) > 0:
                first_content = result.content[0]
                if isinstance(first_content, TextContent):
                    payload_text = first_content.text
                    try:
                        payload_data = json.loads(payload_text)
                        # Assuming success is status 200 and ID is in response.data.id (as per creation_tools.py)
                        if isinstance(payload_data, dict) and payload_data.get("status") == 200:
                            if "data" in payload_data and isinstance(payload_data["data"], dict) and "id" in payload_data["data"]:
                                created_id = payload_data["data"]["id"]
                                logger.info(f"Successfully created device posture policy '{policy_name}' with ID: {created_id}")
                                return created_id
                            else:
                                logger.warning(f"Device posture policy '{policy_name}' creation: Status 200, but 'id' not found in payload_data['data'] or structure is unexpected.")
                                logger.warning(f"Parsed JSON: {payload_data}")
                                return None
                        elif isinstance(payload_data, dict) and payload_data.get("status") == "error":
                            logger.error(f"Tool returned an error for device posture policy '{policy_name}': {payload_data.get('message', 'No message')}")
                            logger.error(f"Tool error details: {payload_data.get('details', 'No details')}")
                            return None
                        else:
                            logger.error(f"Device posture policy '{policy_name}' creation: API did not return 200 or expected success. Full response: {payload_data}")
                            return None
                    except json.JSONDecodeError:
                        logger.error(f"Device posture policy '{policy_name}' creation: Failed to parse TextContent as JSON. Content: {payload_text}")
                        return None
                else:
                    logger.warning(f"Device posture policy '{policy_name}' creation: Content is not TextContent. Content type: {type(first_content)}, Content: {first_content}")
                    return None
            else:
                logger.warning(f"Device posture policy '{policy_name}' creation: No error reported by tool, but no content returned.")
                return None
        else:
            error_message = "Unknown error from tool."
            if result.content and len(result.content) > 0 and isinstance(result.content[0], TextContent):
                error_message = result.content[0].text
            logger.error(f"Tool 'create_device_posture_tool' for '{policy_name}' reported an error.")
            logger.error(f"Tool error message: {error_message}")
            logger.error(f"Full error content from tool: {result.content}")
            return None
    except Exception as e:
        logger.error(f"An exception occurred during device posture policy '{policy_name}' creation: {e}", exc_info=True)
        return None

async def main():
    """Main function to run tests."""
    logger.info("Starting MCP client tester for creation tools...")

    # Command to start the MCP server.
    # Using python -m with PYTHONPATH set, and server logs to stdout.
    server_command_parts = ["python", "-m", "connexa_openvpn_mcp_server.server"]
    command_executable = server_command_parts[0]
    command_args = server_command_parts[1:]

    # Determine server CWD and PYTHONPATH base
    # This script is in 'c:/GitRepos/python-sdk/connexa_openvpn_mcp_server/'
    # The project root (python-sdk) is one level up.
    project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    logger.info(f"Calculated project root for CWD and PYTHONPATH: {project_root_dir}")

    # Set environment for the subprocess, ensuring local project path is preferred.
    # Copy current environment and prepend project_root_dir to PYTHONPATH
    current_env = os.environ.copy()
    existing_pythonpath = current_env.get("PYTHONPATH")
    new_pythonpath = project_root_dir
    if existing_pythonpath:
        new_pythonpath = f"{project_root_dir}{os.pathsep}{existing_pythonpath}"
    current_env["PYTHONPATH"] = new_pythonpath
    logger.info(f"Setting PYTHONPATH for server subprocess to: {new_pythonpath}")

    server_params = StdioServerParameters(
        command=command_executable,
        args=command_args,
        cwd=project_root_dir, # Server's working directory is the project root
        env=current_env # Pass modified environment
    )

    async with AsyncExitStack() as stack:
        try:
            logger.info(f"Initializing stdio client for command: {' '.join(server_command_parts)} in CWD: {server_params.cwd}")
            # logger.info(f"Server CWD will be: {server_params.cwd}") # Redundant with above

            stdio_transport = await stack.enter_async_context(
                stdio_client(server_params)
            )
            read_stream, write_stream = stdio_transport
            logger.info("Stdio transport established.")

            session = await stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            logger.info("MCP ClientSession created. Initializing session...")
            await session.initialize()
            logger.info("Session initialized.")

            # Optional: Wait for server to fully initialize tools
            logger.info("Waiting a few seconds for server to be ready...")
            await asyncio.sleep(5)

            user_group_id = None
            region_id_to_use = "us-west-1" # Mocking region ID as per user request
            # logger.info(f"Using mocked region ID for user group creation: {region_id_to_use}")
            # user_group_id = await test_create_user_group(session, region_id_to_use)

            # if user_group_id:
            #     logger.info(f"User Group creation test successful. ID: {user_group_id}")
            # else:
            #     logger.error("User Group creation test failed or ID not retrieved.")

            # Test User creation
            # user_id = await test_create_user(session, user_group_id)
            # if user_id:
            #     logger.info(f"User creation test successful. ID: {user_id}")
            # else:
            #     logger.error("User creation test failed or ID not retrieved.")
            
            # Test Network creation (disabled as per request)
            # network_id = await test_create_network(session)
            # if network_id:
            #     logger.info(f"Network creation test successful. ID: {network_id}")
            # else:
            #     logger.error("Network creation test failed or ID not retrieved.")
            
            # For host creation, a network_id is needed.
            # Using the ID from your previous successful test log as test_create_network is currently disabled.
            # This ID 'da735f7c-b4e0-4d69-8a1a-854992b3c6dc' might be ephemeral.
            # If this test fails due to an invalid network ID, test_create_network may need to be re-enabled,
            # or a known persistent network ID should be used.
            # network_id_for_host_test = "da735f7c-b4e0-4d69-8a1a-854992b3c6dc" # No longer needed for test_create_host
            # logger.info(f"Using network ID for host test: {network_id_for_host_test} (Note: Actual network creation call is currently disabled in this script)") # No longer relevant

            # Test Host creation (disabled as per request)
            # host_id = await test_create_host(session) # Call without network_id_for_host_test
            # if host_id:
            #     logger.info(f"Host creation test successful. ID: {host_id}")
            # else:
            #     logger.error("Host creation test failed or ID not retrieved.")

            # Test Access Group creation
            # access_group_id = await test_create_access_group(session)
            # if access_group_id:
            #     logger.info(f"Access Group creation test successful. ID: {access_group_id}")
            # else:
            #     logger.error("Access Group creation test failed or ID not retrieved.")
            
            # Test DNS Record creation
            dns_record_id = await test_create_dns_record(session)
            if dns_record_id:
                logger.info(f"DNS Record creation test successful. ID: {dns_record_id}")
            else:
                logger.error("DNS Record creation test failed or ID not retrieved.")

            # Test Location Context Policy creation
            location_context_id = await test_create_location_context(session)
            if location_context_id:
                logger.info(f"Location Context Policy creation test successful. ID: {location_context_id}")
            else:
                logger.error("Location Context Policy creation test failed or ID not retrieved.")

            # Test Device Posture Policy creation
            device_posture_id = await test_create_device_posture(session)
            if device_posture_id:
                logger.info(f"Device Posture Policy creation test successful. ID: {device_posture_id}")
            else:
                logger.error("Device Posture Policy creation test failed or ID not retrieved.")

            # Future tests will be added here

        except Exception as e:
            logger.error(f"An error occurred in main: {e}", exc_info=True)
        finally:
            logger.info("Client operations finished. AsyncExitStack will handle cleanup.")

if __name__ == "__main__":
    asyncio.run(main())
