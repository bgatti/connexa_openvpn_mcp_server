# MCP Connexa Server Testing Notes

This file contains notes from testing the claims and assumptions made in the `connexa_objects_overview` resource of the OpenVPN-Connexa-Server.

## Object Selection Testing

Attempted to select objects using the `select_object_tool`:
- Object Type: User
  - Result: Successfully selected user 'benjamingatti@gmail.com'. Details include user ID, names, email, group ID, status, auth type, role, and a list of associated devices. Search matches included 'benjamingatti@gmail.com', 'alice', 'alice@testme.com', 'bob', 'charlie', 'testuser2'.
- Object Type: Device
  - Result: Successfully selected device 'alice_device'. Details include device ID, user ID, name, description, IP addresses, and connection status. Search matches included 'alice_device', 'bob_device', 'charlie_device', 'device_1748811406544', 'AliceLaptop'.
- Object Type: User Group
  - Result: Successfully selected user group 'Default' using type "usergroup". Details include group ID, name, associated VPN region IDs, internet access settings, max devices, connect auth settings, system subnets, and gateway IDs. Search matches included 'Default', 'Netflix Group', 'gottahave another group', and several 'conn-test-ug-' groups.
- Object Type: Network
  - Result: Successfully selected network 'California Office Network'. Details include network ID, name, description, egress status, internet access settings, a list of associated connectors, system subnets, and tunneling protocol. Search matches included 'California Office Network', 'Netflix Egress Network', 'San Jose Office Network', 'Test Network 2', 'Test Network for Reliability', 'TestNetworkForAlice'.
- Object Type: Host
  - Result: Successfully selected host 'Colorado heist'. Details include host ID, name, description, internet access settings, a list of associated connectors, system subnets, and gateway IDs. Search matches included 'Colorado heist', 'Test Host 2', 'Test Host for Reliability', 'TestHostForAlice', 'test-host-63327efe'.
- Object Type: Connector
  - Result: Failed to select directly. Received error: "Must select a network before searching for a connector." This suggests Connectors are sub-resources of Networks or Hosts and cannot be selected independently. This aligns with the overview stating Connectors belong to Networks or Hosts.
- Object Type: Access Group
  - Result: Successfully selected access group 'Default Full Mesh Access Group'. Details include access group ID, name, description, default group status, and source and destination configurations. Search matches included 'Default Full Mesh Access Group', 'Netflix Exclusive Access', 'Test Access Group', 'test-access-group-f0eeaeb9'.
- Object Type: VPN Region
  - Result: Failed to select using type "vpn region". Received error: "Unsupported object type: vpn region. Supported types: network, user, usergroup, connector, device, host, dns-record, access-group, location-context, device-posture." This object type does not appear to be directly selectable using `select_object_tool`.
- Object Type: Device Posture
  - Result: Successfully selected device posture 'test-device-posture-286cee74'. Details include device posture ID, name, description, associated user group IDs, and platform-specific posture settings (windows, macos, linux, android, ios). Search matches included 'test-device-posture-286cee74', 'test-device-posture-9b36a384', 'Test Device Posture Policy', 'Test Device Posture'.
- Object Type: DNS Record
  - Result: Successfully selected DNS record 'nas.cal-architects.com'. Details include DNS record ID, domain, description, and associated IPv4 addresses. Search matches included 'nas.cal-architects.com', 'test-dns-1695608e.example.com', 'test-dns-fe62eb5f.example.com'.

## Object Creation Testing

Attempted to create objects using the available creation tools:
- Tool: create_network_tool
  - Result: Successfully created a Network with name 'Test Network by MCP'. Received details including ID, name, egress status, internet access, system subnets, and tunneling protocol.
- Tool: create_user_group_tool
  - Result: Successfully created a User Group with name 'Test User Group by MCP'. Received details including ID, name, associated VPN region IDs, all regions included status, internet access settings, max devices, connect auth settings, system subnets, and gateway IDs.
- Tool: create_host_tool
  - Result: Successfully created a Host with name 'Test Host by MCP'. Received a warning about ID/name not found in the top-level response, but the 'data' field contains the new host's details including ID, name, internet access, connectors, system subnets, and gateway IDs.
- Tool: create_device_tool
  - Result: Failed to create a Device with name 'Test_Device_by_MCP' for user 'benjamingatti@gmail.com'. Received a 400 Bad Request error: "Device limit is exceeded". This indicates the user has reached the maximum number of allowed devices, which aligns with the 'maxDevice' setting mentioned for User Groups.
- Tool: create_dns_record_tool
  - Result: Successfully created a DNS Record with domain 'test.mcp.com' and IPv4 address '192.168.1.100'. Received details including ID, domain, and IPv4 addresses. This confirms that at least one IP address is required for creation.
- Tool: create_access_group_tool
  - Result: Successfully created an Access Group with name 'Test Access Group by MCP' by providing the 'Default' User Group as both a source and a destination, and setting 'allCovered' to false for both. This confirms that both 'source' and 'destination' lists are required and cannot be empty, and 'allCovered' is also required within the access items, which contradicts the tool's schema.
- Tool: create_location_context_tool
  - Result: Successfully created a Location Context with name 'Test Location Context by MCP' by providing an 'ipCheck' with an IP address in CIDR format (192.168.1.1/32) and a 'defaultCheck'. This confirms that at least one of 'ipCheck' or 'countryCheck' is required, 'ips' within 'ipCheck' cannot be empty and must be in CIDR format, and 'defaultCheck' is required, all contradicting the tool's schema.
- Tool: create_device_posture_tool
  - Result: Successfully created a Device Posture with name 'Test Device Posture by MCP'. Received details including ID, name, associated user group IDs, and platform-specific posture settings.
- Tool: create_user_tool
  - Result: Successfully created a User with username 'testuserbymcp' and provided a 'groupId'. Received details including ID, names, username, email, group ID, status, auth type, role, and an empty list of devices. This confirms that 'groupId' is effectively required for user creation, contradicting the schema.

## Relationship Observations

Observations on how the available tools and resources reflect the described relationships:
- User to User Group (belongs to): Confirmed. `select_object_tool` for User returns `groupId`. `create_user_tool` effectively requires `groupId`.
- User to Device (has many): Confirmed. `select_object_tool` for User returns a list of `devices`. `create_device_tool` requires `userId`.
- User Group to VPN Region (access defined): Confirmed. `select_object_tool` for User Group returns `vpnRegionIds`.
- Network to Connector (has many): Confirmed. `select_object_tool` for Network returns a list of `connectors`.
- Network to Route (has many): Not directly supported by available tools/resources.
- Network to IP Service (has many): Not directly supported by available tools/resources.
- Network to Application (has many): Not directly supported by available tools/resources.
- Host to Connector (has many): Confirmed. `select_object_tool` for Host returns a list of `connectors`.
- Host to IP Service (has many): Not directly supported by available tools/resources.
- Host to Application (has many): Not directly supported by available tools/resources.
- Access Group (source/destination): Confirmed. `select_object_tool` for Access Group returns `source` and `destination`. `create_access_group_tool` requires non-empty `source` and `destination`.
- Connector to VPN Region (connects via): Confirmed. Details from selecting Network or Host (which include connectors) show `vpnRegionId` for connectors.
- Device to Device Posture (policy applies): Relationship appears to be indirect, via User Groups, as indicated by `select_object_tool` for Device Posture returning `userGroupsIds`. No direct link from Device to Device Posture observed.
- Device Posture to User Group (associated via): Confirmed. `select_object_tool` for Device Posture returns `userGroupsIds`.

## Points of Confusion

Any points of confusion or discrepancies found during testing:
- "VPN Region" is listed as a main entity in the overview but is not directly selectable by the `select_object_tool`.
- "Connector" is listed as a main entity but is not directly selectable by the `select_object_tool`; it requires a parent Network or Host to be selected first.
- The overview mentions relationships involving "Route", "IP Service", and "Application", but there are no corresponding direct selection or creation tools available for these entities.
- Several creation tools (`create_device_tool`, `create_dns_record_tool`, `create_access_group_tool`, `create_location_context_tool`, `create_user_tool`) have parameters that are listed as optional in their schemas but were found to be effectively required for successful API calls.
- The `ips` field within the `ipCheck` for `create_location_context_tool` requires IP addresses to be in CIDR format (e.g., "192.168.1.1/32"), which is not specified in the tool's schema.
- The `create_host_tool` returned a warning about ID/name not found in the top-level response, although the data was present in a nested field.
- The `create_device_tool` failed due to a "Device limit is exceeded" error for the test user, indicating a potential limitation or configuration issue in the environment rather than the tool itself.
