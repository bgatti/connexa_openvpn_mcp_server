# complete_update_selected Tool - Common Errors and Solutions

This document outlines common errors encountered and their solutions while testing the `complete_update_selected` tool for the OpenVPN-Connexa-Server MCP.

## 1. Resource Access Errors (`asyncio.run() cannot be called from a running event loop`)

**Error:** Attempts to access MCP resources like `api_overview` or `creation_schema/{object_type}` fail with an `asyncio.run() cannot be called from a running event loop` error.

**Impact:** Prevents direct access to API documentation and update/creation schemas via MCP resources.

**Solution:** Infer the required payload structure for the `complete_update_selected` tool based on the details of the selected object (obtained via `select_object_tool`) and the creation tool schemas (if available or inferable from tool definitions).

## 2. User Update Failed for OWNER Role

**Error:** Attempting to update certain fields (e.g., email, role, status) for a user with the "OWNER" role results in a permission error ("You cannot update email, role, status, use temporary password or delete owner's account").

**Impact:** Restrictions on modifying OWNER user accounts.

**Solution:** Select and update a user with a different role (e.g., "MEMBER").

## 3. User Update Required `groupId`

**Error:** Updating a user fails with a "parameter is missing" error for `groupId`, even though `groupId` is optional during user creation.

**Impact:** User updates require the `groupId` to be included in the update payload.

**Solution:** Include the existing `groupId` of the user in the `updated_payload` when using `complete_update_selected`.

## 4. Usergroup Update Required All Fields

**Error:** Updating a usergroup fails if the `updated_payload` only includes the fields to be changed. An error related to `internetAccess` (e.g., "Such access to the internet cannot be selected") may occur.

**Impact:** The API seems to require all existing fields of the usergroup to be included in the update payload, even if their values are not being changed.

**Solution:** Include all fields from the selected usergroup's details in the `updated_payload` when using `complete_update_selected`, in addition to the fields being updated.

## 5. Device Update Failed (Missing `userId`)

**Error:** Attempting to update a device fails with a "parameter is missing" error for `userId`, despite including `userId` in the `updated_payload`.

**Impact:** Unable to update device objects using the `complete_update_selected` tool in its current implementation.

**Solution:** No workaround found within the scope of testing. This may indicate an issue with the tool's implementation or the API endpoint.

## 6. DNS Record Update Not Supported

**Error:** Attempting to update a dns-record results in an explicit message: "Error: Update functionality not defined for object type 'dns-record'".

**Impact:** DNS record objects cannot be updated using the `complete_update_selected` tool.

**Solution:** Update functionality is not available for this object type via this tool.

## 7. Unsupported Object Types for Selection/Update

**Observation:** Object types like `access-group`, `location-context`, and `device-posture` are not supported by the `select_object_tool`.

**Impact:** These object types cannot be selected or subsequently updated using the `complete_update_selected` tool.

**Solution:** These object types are not within the scope of the `select_object_tool` and `complete_update_selected` tool's current capabilities.

## Entity Representation Clarifications

- **VPN Region:** Listed as a main entity in the overview but is not directly selectable by the `select_object_tool`. VPN Region is primarily a list of service locations and not a distinct configurable object.
- **Connector:** Listed as a main entity in the overview but is not directly selectable by the `select_object_tool`; it requires a parent Network or Host to be selected first. Connector is not a top-level configurable entity.
- **Route, IP Service, and Application:** The overview mentions relationships involving these entities, but there are no corresponding direct selection or creation tools available. Updates related to these entities are typically managed through the schema of their parent objects (e.g., Networks or Hosts).
