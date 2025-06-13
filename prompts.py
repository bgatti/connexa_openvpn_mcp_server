import mcp.types as types
import sys # For logging to stderr

# Source data for the guidelines
CONNEXA_API_GUIDELINES = [
    {
        "id": "object_relationships",
        "text": "Understanding object relationships is key in OpenVPN Connexa. Users must be added to User Groups. Devices are associated with Users. Connectors can be added to either Hosts or Networks. Egress functionality, which provides internet connectivity, requires a specific chain: a User connected to a Network, which has a Connector with the 'egress' property set to true. Creating a Network with `egress=true` and then creating a Connector for that Network will automatically trigger the provisioning of an AWS instance to handle the egress traffic. To bring an egress connector online after creation, it must be deleted and then recreated."
    },
    {
        "id": "available_tools_overview",
        "text": "The available tools allow for selecting, deleting, creating, and updating various objects. The selection tool is `select_object_tool`. To delete a selected object, use `delete_selected_object`. Creation tools include: `create_network_tool`, `create_network_connector_tool`, `create_user_group_tool`, `create_host_tool`, `create_host_connector_tool`, `create_device_tool`, `create_dns_record_tool`, `create_access_group_tool`, `create_location_context_tool`, `create_device_posture_tool`, `create_user_tool`. When creating dependent objects (like Connectors within a Network or Devices for a User), the creation tools will often use derivative names by default based on the parent object. To update a selected object, first use `select_object_tool`, then retrieve the object's current data and schema (e.g., via the `mcp://resources/current_selection` and `mcp://resources/selected_object_schema` resources, or by using the `act_on_selected_object` tool with the 'update' command), modify the data, and finally use the `complete_update_selected` tool with the modified data as the payload."
    },
    {
        "id": "select_and_update_workflow",
        "text": "The standard workflow for managing existing objects involves selecting the object first. Use the `select_object_tool` with the `object_type` and optionally `name_search` to make an object the current selection. Once an object is selected, you can perform actions on it. To update the selected object, you need its current data and the schema defining the valid structure for updates. You can get this information by accessing the `mcp://resources/current_selection` resource (for current data) and the `mcp://resources/selected_object_schema` resource (for the schema). Alternatively, you can use the `act_on_selected_object` tool with the command name 'update', which will return both the current data and the schema. **IMPORTANT:** When using the `complete_update_selected` tool, you must provide the *entire* object payload with your desired modifications. Any data fields that are omitted from the payload will be deleted from the object on the server. After obtaining the current data and schema, modify the data according to your needs, ensuring it conforms to the schema and includes all fields you wish to retain. Finally, use the `complete_update_selected` tool, providing the complete modified data as the `updated_payload` argument. This will send a PUT request to the API to update the selected object."
    },
  {
    "id": "default_aws_region",
    "text": "When creating resources that require an AWS region, such as connectors, leaving the 'vpnRegionId' field blank will use the default AWS region configured in the OpenVPN Connexa server."
  },
  {
    "id": "enable_egress_internet",
    "text": "To enable egress internet connectivity for a network, ensure the network has 'egress' set to true. Then, create a connector for the network using the `create_network_connector_tool`. You can often leave the 'name' field blank to use a derivative name and the 'vpnRegionId' field blank to use the default AWS region. After creating the connector, you must delete and then recreate it to bring the egress connector online and activate internet connectivity."
  },
  {
    "id": "derivative_object_naming",
    "text": "When creating derivative objects such as connectors or devices, they will be given derivative names by default, typically in the format '(parentObjectName) objectType'. For example, a connector created within a network named 'MyNetwork' might be named 'MyNetwork connector'. It is important to keep these names short to avoid potential errors."
  }
]

async def list_guideline_prompts() -> list[types.Prompt]:
    """Lists available guideline prompts for OpenVPN Connexa."""
    print("DEBUG: list_guideline_prompts called", file=sys.stderr) # ADDED DEBUG
    prompts = []
    for guideline in CONNEXA_API_GUIDELINES:
        # Use the first 100 chars of text for description, or full text if shorter
        description_text = guideline['text']
        if len(description_text) > 100:
            description_text = description_text[:97] + "..."
        
        prompts.append(
            types.Prompt(
                name=guideline['id'], # Use the guideline ID as the prompt name
                description=description_text, # Use full/partial text as description
                arguments=[], # Assuming these prompts don't take arguments
            )
        )
    # ADDED DEBUG: Log the prompts being returned
    print(f"DEBUG: list_guideline_prompts returning {len(prompts)} prompts:", file=sys.stderr)
    for p in prompts:
        print(f"DEBUG:   Prompt name='{p.name}', description='{p.description[:50]}...'", file=sys.stderr)
    return prompts

async def get_guideline_prompt(name: str, arguments: dict[str, str] | None = None) -> types.GetPromptResult:
    """Retrieves the specified guideline prompt by its ID."""
    for guideline in CONNEXA_API_GUIDELINES:
        if guideline['id'] == name:
            return types.GetPromptResult(
                messages=[
                    types.PromptMessage(
                        role="user", 
                        content=types.TextContent(type="text", text=guideline['text'])
                    )
                ]
            )
    
    raise ValueError(f"Unknown prompt name: {name}")
