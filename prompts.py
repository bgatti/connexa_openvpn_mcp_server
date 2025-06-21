import mcp.types as types
import sys # For logging to stderr

# Source data for the guidelines
CONNEXA_API_GUIDELINES = [
    {
        "id": "available_object_types",
        "text": "You can interact with the following object types: network, user, usergroup, connector, device, host, dns-record, access-group, location-context, device-posture. Use `select_object_tool` to select an existing object or a `create_*_tool` to create a new one."
    },
    {
        "id": "basic_workflow",
        "text": "The basic workflow for managing objects is: 1. Select an object using `select_object_tool`. 2. Perform an action on the selected object (e.g., update using `complete_update_selected` or delete using `delete_selected_object`). 3. To create a new object, use the appropriate `create_*_tool`."
    },
    {
        "id": "get_schema",
        "text": "To understand the required fields and structure for creating or updating an object, you can access the schema. Use the `get_selected_schema` tool to get the update schema for the currently selected object. For creation schemas, use `access_mcp_resource` with the URI `mcp://resources/creation_schema/{object_type}`."
    },
    {
        "id": "updating_objects",
        "text": "When updating a selected object using `complete_update_selected`, you must provide the complete payload of the object, including all fields you wish to retain, even if their values are not changing. Obtain the current object details using `mcp://resources/current_selection` before constructing your update payload."
    },
    {
        "id": "domain_name_routing",
        "text": "For applications (Network Applications and Host Applications), routing can be configured using domain names instead of IP addresses. This allows users to access the application using a friendly domain name, which is then resolved by the WPC to the actual IP address of the application."
    }
]

async def list_guideline_prompts() -> list[types.Prompt]:
    """Lists available guideline prompts for OpenVPN Connexa."""
    prompts = []
    for guideline in CONNEXA_API_GUIDELINES:
        description_text = guideline['text']
        if len(description_text) > 100:
            description_text = description_text[:97] + "..."
        
        prompts.append(
            types.Prompt(
                name=guideline['id'],
                description=description_text,
                arguments=[],
            )
        )
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
