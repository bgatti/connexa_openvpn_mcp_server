import pytest
import anyio
from mcp.client.session_group import ClientSessionGroup, StdioServerParameters

# Assuming the MCP server is running locally and communicating via stdio

@pytest.mark.asyncio
async def test_list_tools_real_api():
    """
    Tests listing available tools from the real API via MCP.
    """
    server_params = StdioServerParameters(
        command="uv run connexa_openvpn_mcp_server"
    )

    async with ClientSessionGroup() as group:
        try:
            await group.connect_to_server(server_params)

            # List available tools
            tools = group.tools

            assert isinstance(tools, dict)
            assert len(tools) > 0 # Assuming there is at least one tool available

            print(f"Successfully listed {len(tools)} tools.")
            # print("Available tools:", list(tools.keys())) # Optional: print tool names

        except Exception as e:
            pytest.fail(f"Failed to list tools: {e}")
