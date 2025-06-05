import pytest
import anyio # Import anyio for async context
from mcp.client.session_group import ClientSessionGroup, StdioServerParameters

# Assuming the MCP server is running locally and communicating via stdio

@pytest.mark.asyncio
async def test_select_network_california_real_api():
    """
    Tests selecting a network named 'california' using the real API via MCP.
    """
    # Define server parameters for the local stdio server
    server_params = StdioServerParameters(
        command="uv run connexa_openvpn_mcp_server"
    )

    # Use ClientSessionGroup to manage the connection and call the tool
    async with ClientSessionGroup() as group:
        try:
            # Connect to the server
            await group.connect_to_server(server_params)

            # Use the group's call_tool method to execute the tool
            result = await group.call_tool(
                name="select_object_tool",
                args={
                    "object_type": "network",
                    "name_search": "california"
                }
            )

            # Assert that the tool call was successful
            assert result is not None
            # Further assertions can be added here based on the expected output structure
            # For example, checking if a network was selected and its name is 'california'
            # assert "selected_object" in result
            # assert result["selected_object"]["name"] == "california"

            print(f"Tool call successful: {result}")

        except Exception as e:
            pytest.fail(f"Tool call failed: {e}")
