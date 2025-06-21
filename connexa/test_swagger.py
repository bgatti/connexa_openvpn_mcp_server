import unittest
import os
import json
from unittest.mock import patch, mock_open, MagicMock
import sys

# Adjust the path to import from the project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Mock the mcp package and its relevant modules
# This prevents ImportErrors when running tests outside the MCP environment
sys.modules['mcp'] = MagicMock()
sys.modules['mcp.server'] = MagicMock()
sys.modules['mcp.server.fastmcp'] = MagicMock()
sys.modules['mcp.types'] = MagicMock()
sys.modules['mcp.server.lowlevel'] = MagicMock()
sys.modules['mcp.shared'] = MagicMock()
sys.modules['mcp.shared._httpx_utils'] = MagicMock()


# Assuming update_tools is in the same directory or accessible via sys.path
# Import after mocking to avoid immediate import errors
from connexa_openvpn_mcp_server.connexa.update_tools import _get_swagger_content, get_schema_for_object_type, CURRENT_SELECTED_OBJECT

# Define a mock swagger content for testing
MOCK_SWAGGER_CONTENT = {
    "components": {
        "schemas": {
            "DnsRecordRequest": {"type": "object", "properties": {"domain": {"type": "string"}}},
            "AccessGroupRequest": {"type": "object", "properties": {"name": {"type": "string"}}},
            "DevicePostureRequest": {"type": "object", "properties": {"name": {"type": "string"}}},
            "NetworkUpdateRequest": {"type": "object", "properties": {"name": {"type": "string"}}},
            "UserUpdateRequest": {"type": "object", "properties": {"firstName": {"type": "string"}}},
            "UserGroupRequest": {"type": "object", "properties": {"name": {"type": "string"}}},
            "HostUpdateRequest": {"type": "object", "properties": {"name": {"type": "string"}}},
            "DeviceRequest": {"type": "object", "properties": {"name": {"type": "string"}}},
            "NetworkConnectorRequest": {"type": "object", "properties": {"name": {"type": "string"}}},
            "HostConnectorRequest": {"type": "object", "properties": {"name": {"type": "string"}}},
            "LocationContextRequest": {"type": "object", "properties": {"name": {"type": "string"}}}
        }
    }
}

class TestSwaggerLoadingAndSchemaRetrieval(unittest.TestCase):

    @patch('connexa.update_tools.open', new_callable=mock_open, read_data=json.dumps(MOCK_SWAGGER_CONTENT))
    @patch('connexa.update_tools.os.path.join')
    @patch('connexa.update_tools._CACHED_SWAGGER_CONTENT', None) # Ensure cache is initially None
    def test_get_swagger_content_success(self, mock_path_join, mock_file_open):
        """Tests if _get_swagger_content loads swagger.json correctly."""
        mock_path_join.return_value = '/fake/path/swagger.json'
        swagger_content = _get_swagger_content()
        self.assertEqual(swagger_content, MOCK_SWAGGER_CONTENT)
        mock_file_open.assert_called_once_with('/fake/path/swagger.json', 'r')

    @patch('connexa.update_tools.open', side_effect=FileNotFoundError)
    @patch('connexa.update_tools.os.path.join')
    @patch('connexa.update_tools._CACHED_SWAGGER_CONTENT', None) # Ensure cache is initially None
    def test_get_swagger_content_file_not_found(self, mock_path_join, mock_file_open):
        """Tests if _get_swagger_content handles FileNotFoundError."""
        mock_path_join.return_value = '/fake/path/swagger.json'
        swagger_content = _get_swagger_content()
        self.assertIn("error", swagger_content)
        self.assertIn("Failed to load swagger.json", swagger_content["error"])
        mock_file_open.assert_called_once_with('/fake/path/swagger.json', 'r')

    @patch('connexa.update_tools._get_swagger_content', return_value=MOCK_SWAGGER_CONTENT)
    def test_get_schema_for_object_type_success(self, mock_get_swagger):
        """Tests if get_schema_for_object_type retrieves schemas correctly."""
        test_cases = {
            "dns-record": "DnsRecordRequest",
            "access-group": "AccessGroupRequest",
            "device-posture": "DevicePostureRequest",
            "network": "NetworkUpdateRequest",
            "user": "UserUpdateRequest",
            "usergroup": "UserGroupRequest",
            "host": "HostUpdateRequest",
            "device": "DeviceRequest",
            "connector": "NetworkConnectorRequest", # Assuming this is the schema for connector updates
            "location-context": "LocationContextRequest"
        }
        for object_type, schema_name in test_cases.items():
            schema = get_schema_for_object_type(object_type, request_type="update")
            self.assertIsNotNone(schema, f"Schema not found for {object_type}")
            self.assertEqual(schema, MOCK_SWAGGER_CONTENT["components"]["schemas"][schema_name])

    @patch('connexa.update_tools._get_swagger_content', return_value=MOCK_SWAGGER_CONTENT)
    def test_get_schema_for_object_type_not_found(self, mock_get_swagger):
        """Tests if get_schema_for_object_type returns None for unknown types."""
        schema = get_schema_for_object_type("unknown_type", request_type="update")
        self.assertIsNone(schema)

    @patch('connexa.update_tools._get_swagger_content', return_value={"components": {}}) # Missing schemas key
    def test_get_schema_for_object_type_malformed_swagger(self, mock_get_swagger):
        """Tests if get_schema_for_object_type handles malformed swagger."""
        schema = get_schema_for_object_type("dns-record", request_type="update")
        self.assertIsNone(schema)

    @patch('connexa.update_tools.CURRENT_SELECTED_OBJECT')
    @patch('connexa.update_tools.get_schema_for_object_type')
    def test_get_selected_schema_tool_success(self, mock_get_schema_for_object_type, mock_current_selected_object):
        """Tests if get_selected_schema_tool returns schema for selected object."""
        mock_current_selected_object.object_type = "dns-record"
        mock_get_schema_for_object_type.return_value = {"some": "schema"}
        result = get_selected_schema_tool()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["object_type"], "dns-record")
        self.assertEqual(result["schema"], {"some": "schema"})
        mock_get_schema_for_object_type.assert_called_once_with("dns-record", request_type="update")

    @patch('connexa.update_tools.CURRENT_SELECTED_OBJECT')
    def test_get_selected_schema_tool_no_selection(self, mock_current_selected_object):
        """Tests if get_selected_schema_tool handles no selected object."""
        mock_current_selected_object.object_type = None
        result = get_selected_schema_tool()
        self.assertEqual(result["status"], "error")
        self.assertIn("No object is currently selected", result["message"])

    @patch('connexa.update_tools.CURRENT_SELECTED_OBJECT')
    @patch('connexa.update_tools.get_schema_for_object_type', return_value=None)
    def test_get_selected_schema_tool_schema_not_found(self, mock_get_schema_for_object_type, mock_current_selected_object):
        """Tests if get_selected_schema_tool handles schema not found."""
        mock_current_selected_object.object_type = "unknown_type"
        result = get_selected_schema_tool()
        self.assertEqual(result["status"], "not_found")
        self.assertIn("Update schema not found for object type: unknown_type", result["message"])
        mock_get_schema_for_object_type.assert_called_once_with("unknown_type", request_type="update")


if __name__ == '__main__':
    unittest.main()
