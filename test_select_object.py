import unittest
from unittest.mock import patch, MagicMock
import os
import json # Import json for creating JSON strings

# Adjust the path to import from the parent directory's 'connexa' package
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from connexa_openvpn_mcp_server.connexa.selected_object import select_object_tool, CURRENT_SELECTED_OBJECT, SelectedObject
from connexa_openvpn_mcp_server.connexa.connexa_api import call_api # Though we mock it, importing helps with context

# Pre-clear any existing selection from previous test runs or imports
CURRENT_SELECTED_OBJECT.clear()

class TestSelectObjectTool(unittest.TestCase):

    def setUp(self):
        # Reset the CURRENT_SELECTED_OBJECT before each test
        CURRENT_SELECTED_OBJECT.clear()
        # os.environ modification in setUp might not affect module-level CONNEXA_REGION
        # We will patch os.getenv directly in tests that need specific CONNEXA_REGION values.

    def tearDown(self):
        # Clean up environment variables if set specifically for a test
        # No longer setting os.environ directly for CONNEXA_REGION in setUp
        pass

    @patch('connexa_openvpn_mcp_server.connexa.selected_object.os.getenv')
    @patch('connexa_openvpn_mcp_server.connexa.selected_object.call_api')
    def test_select_network_no_networks_found(self, mock_call_api, mock_os_getenv):
        """Test behavior when the API returns no networks."""
        mock_os_getenv.return_value = "test-region-1" # Mock CONNEXA_REGION
        mock_call_api.return_value = {"status": 200, "data": []}
        
        # Pass kwargs as a JSON string or None
        found_names, message = select_object_tool(object_type="network", kwargs=None)
        
        self.assertEqual(found_names, ["No networks found."])
        self.assertEqual(message, "No networks available to select.")
        self.assertIsNone(CURRENT_SELECTED_OBJECT.object_type)
        self.assertIsNone(CURRENT_SELECTED_OBJECT.object_id)
        mock_call_api.assert_called_once_with(action="get", path="/api/v1/networks")
        mock_os_getenv.assert_any_call("CONNEXA_REGION", "us-west-1")


    @patch('connexa_openvpn_mcp_server.connexa.selected_object.os.getenv')
    @patch('connexa_openvpn_mcp_server.connexa.selected_object.call_api')
    def test_select_network_api_error(self, mock_call_api, mock_os_getenv):
        """Test behavior when the API call to fetch networks fails."""
        mock_os_getenv.return_value = "test-region-1" # Mock CONNEXA_REGION
        mock_call_api.return_value = {"status": 500, "message": "Internal Server Error", "data": None}
        
        # Pass kwargs as a JSON string or None
        found_names, message = select_object_tool(object_type="network", kwargs=None)
        
        self.assertEqual(found_names, [])
        self.assertTrue("Error fetching networks: Internal Server Error" in message)
        self.assertIsNone(CURRENT_SELECTED_OBJECT.object_type)
        mock_call_api.assert_called_once_with(action="get", path="/api/v1/networks")
        mock_os_getenv.assert_any_call("CONNEXA_REGION", "us-west-1")

    @patch('connexa_openvpn_mcp_server.connexa.selected_object.os.getenv')
    @patch('connexa_openvpn_mcp_server.connexa.selected_object.call_api')
    def test_select_network_default_selection_success(self, mock_call_api, mock_os_getenv):
        """Test default network selection when networks are available."""
        mock_os_getenv.return_value = "test-region-1" # This region should be selected
        mock_networks_data = [
            {"id": "net-1", "name": "Network Alpha", "region": "other-region"},
            {"id": "net-2", "name": "Network Bravo (Default)", "region": "test-region-1"},
            {"id": "net-3", "name": "Network Charlie", "region": "other-region"},
        ]
        mock_call_api.return_value = {"status": 200, "data": mock_networks_data}
        
        # Pass kwargs as a JSON string or None
        found_names, message = select_object_tool(object_type="network", kwargs=None)
        
        expected_found_names = ["Network Alpha", "Network Bravo (Default)", "Network Charlie"]
        self.assertCountEqual(found_names, expected_found_names) # Order might not be guaranteed by the tool
        # The default selection logic in select_object_tool prioritizes CONNEXA_REGION, then the first network.
        # The test data has a network in "test-region-1", which matches the mocked CONNEXA_REGION.
        self.assertEqual(message, "Selected Object is Network Bravo (Default)")
        self.assertEqual(CURRENT_SELECTED_OBJECT.object_type, "network")
        self.assertEqual(CURRENT_SELECTED_OBJECT.object_id, "net-2")
        self.assertEqual(CURRENT_SELECTED_OBJECT.object_name, "Network Bravo (Default)")
        self.assertEqual(CURRENT_SELECTED_OBJECT.details, mock_networks_data[1])
        mock_os_getenv.assert_any_call("CONNEXA_REGION", "us-west-1")

    @patch('connexa_openvpn_mcp_server.connexa.selected_object.os.getenv')
    @patch('connexa_openvpn_mcp_server.connexa.selected_object.call_api')
    def test_select_network_specific_name_match(self, mock_call_api, mock_os_getenv):
        """Test selecting a network by a specific name that has one match."""
        mock_os_getenv.return_value = "test-region-1" # Mock CONNEXA_REGION
        mock_networks_data = [
            {"id": "net-1", "name": "Alpha Network", "region": "test-region-1"},
            {"id": "net-2", "name": "SpecificNet", "region": "other-region"},
            {"id": "net-3", "name": "Gamma Network", "region": "test-region-1"},
        ]
        mock_call_api.return_value = {"status": 200, "data": mock_networks_data}
        
        # Pass kwargs as a JSON string or None
        found_names, message = select_object_tool(object_type="network", name_search="SpecificNet", kwargs=None)
        
        # When a specific search yields one result, found_names should contain only that one.
        # The current implementation returns all names if search yields one, let's adjust test or code.
        # For now, assuming the tool's current behavior: lists all, selects the specific one.
        # If tool is changed to return only matched name, this test part needs update.
        self.assertIn("SpecificNet", found_names)
        self.assertEqual(message, "Selected Object is SpecificNet")
        self.assertEqual(CURRENT_SELECTED_OBJECT.object_id, "net-2")
        self.assertEqual(CURRENT_SELECTED_OBJECT.object_name, "SpecificNet")
        mock_os_getenv.assert_any_call("CONNEXA_REGION", "us-west-1")

    @patch('connexa_openvpn_mcp_server.connexa.selected_object.os.getenv')
    @patch('connexa_openvpn_mcp_server.connexa.selected_object.call_api')
    def test_select_network_name_search_multiple_matches_selects_default(self, mock_call_api, mock_os_getenv):
        """Test name search yielding multiple results, should select default."""
        mock_os_getenv.return_value = "default-region" # Ensure default is distinct
        mock_networks_data = [
            {"id": "net-default", "name": "Default Main Network", "region": "default-region"},
            {"id": "net-match1", "name": "SearchMe Alpha", "region": "other"},
            {"id": "net-match2", "name": "SearchMe Bravo", "region": "another"},
        ]
        mock_call_api.return_value = {"status": 200, "data": mock_networks_data}

        # Pass kwargs as a JSON string or None
        found_names, message = select_object_tool(object_type="network", name_search="SearchMe", kwargs=None)
        
        # The filtering logic should now correctly find "SearchMe Alpha" and "SearchMe Bravo"
        self.assertIn("SearchMe Alpha", found_names)
        self.assertIn("SearchMe Bravo", found_names)
        self.assertEqual(message, "Selected Object is Default Main Network") # Default selected
        self.assertEqual(CURRENT_SELECTED_OBJECT.object_id, "net-default")
        mock_os_getenv.assert_any_call("CONNEXA_REGION", "us-west-1")

    @patch('connexa_openvpn_mcp_server.connexa.selected_object.os.getenv')
    @patch('connexa_openvpn_mcp_server.connexa.selected_object.call_api')
    def test_select_network_name_search_no_matches_selects_default(self, mock_call_api, mock_os_getenv):
        """Test name search yielding no results, should select default."""
        mock_os_getenv.return_value = "default-region" # Mock CONNEXA_REGION
        mock_networks_data = [
            {"id": "net-default", "name": "Default Main Network", "region": "default-region"},
            {"id": "net-other", "name": "Some Other Net", "region": "other"},
        ]
        mock_call_api.return_value = {"status": 200, "data": mock_networks_data}

        # Pass kwargs as a JSON string or None
        found_names, message = select_object_tool(object_type="network", name_search="NonExistent", kwargs=None)
        
        self.assertEqual(message, "Selected Object is Default Main Network") # Default selected
        self.assertEqual(CURRENT_SELECTED_OBJECT.object_id, "net-default")
        mock_os_getenv.assert_any_call("CONNEXA_REGION", "us-west-1")

    @patch('connexa_openvpn_mcp_server.connexa.selected_object.os.getenv')
    def test_select_unsupported_object_type(self, mock_os_getenv):
        """Test selecting an unsupported object type."""
        mock_os_getenv.return_value = "test-region-1" # Mock CONNEXA_REGION
        # Pass kwargs as a JSON string or None
        found_names, message = select_object_tool(object_type="unsupported_type", kwargs=None)
        self.assertEqual(found_names, [])
        self.assertEqual(message, "Unsupported object type: unsupported_type. Supported types: network.")
        self.assertIsNone(CURRENT_SELECTED_OBJECT.object_type)
        mock_os_getenv.assert_any_call("CONNEXA_REGION", "us-west-1")

    @patch('connexa_openvpn_mcp_server.connexa.selected_object.os.getenv')
    @patch('connexa_openvpn_mcp_server.connexa.selected_object.call_api')
    def test_select_network_with_kwargs_filter(self, mock_call_api, mock_os_getenv):
        """Test filtering networks using kwargs."""
        mock_networks_data = [
            {"id": "net-1", "name": "ActiveNet West", "region": "us-west-1", "status": "active"},
            {"id": "net-2", "name": "PendingNet East", "region": "us-east-1", "status": "pending"},
            {"id": "net-3", "name": "ActiveNet South", "region": "us-south-1", "status": "active"},
        ]
        mock_call_api.return_value = {"status": 200, "data": mock_networks_data}
        
        # Test 1: Name search with specific kwarg
        mock_os_getenv.return_value = "us-west-1" # Set default region for selection
        found_names, message = select_object_tool(
            object_type="network", 
            name_search="ActiveNet", 
            kwargs=json.dumps({"status": "active"}) 
        )
        
        self.assertIn("ActiveNet West", found_names)
        self.assertIn("ActiveNet South", found_names)
        self.assertNotIn("PendingNet East", found_names)
        self.assertEqual(message, "Selected Object is ActiveNet West")
        self.assertEqual(CURRENT_SELECTED_OBJECT.object_id, "net-1")
        mock_os_getenv.assert_any_call("CONNEXA_REGION", "us-west-1")


        # Test 2: No name search, just kwarg
        CURRENT_SELECTED_OBJECT.clear() # Reset selection
        mock_os_getenv.return_value = "us-east-1" # Change default for this part
        mock_networks_data_2 = [
            {"id": "net-p1", "name": "Pending Alpha", "region": "us-east-1", "status": "pending"},
            {"id": "net-a1", "name": "Active Alpha", "region": "us-west-1", "status": "active"},
        ]
        mock_call_api.return_value = {"status": 200, "data": mock_networks_data_2}

        # Pass kwargs as a JSON string
        found_names, message = select_object_tool(
            object_type="network", 
            kwargs=json.dumps({"status": "pending"})
        )
        self.assertIn("Pending Alpha", found_names)
        self.assertNotIn("Active Alpha", found_names)
        self.assertEqual(message, "Selected Object is Pending Alpha")
        self.assertEqual(CURRENT_SELECTED_OBJECT.object_id, "net-p1")
        # mock_os_getenv was called for CONNEXA_REGION in this test part too
        # The number of calls to os.getenv depends on how many times select_object_tool is called
        # and if CONNEXA_REGION is accessed multiple times within it.
        # For simplicity, we'll rely on assert_any_call.
        mock_os_getenv.assert_any_call("CONNEXA_REGION", "us-west-1")

    @patch('connexa_openvpn_mcp_server.connexa.selected_object.os.getenv') # For select_object_tool's os.getenv
    def test_create_select_update_delete_workflow(self, mock_os_getenv): # mock_call_api removed from args
        """Test a workflow: select a 'new' network, update it, delete it, verify deletion."""
        mock_os_getenv.return_value = "test-region-1" # Mock CONNEXA_REGION for select_object_tool

        shared_api_mock = MagicMock()

        new_network_id = "net-workflow-123"
        new_network_name = "WorkflowTestNetwork"
        initial_network_data = {
            "id": new_network_id,
            "name": new_network_name,
            "region": "test-region-1",
            "description": "Initial"
        }

        updated_network_name = "WorkflowTestNetworkUpdated"
        update_payload_sent = {"name": updated_network_name, "description": "Updated by API"}
        updated_network_data_from_api = {
            "id": new_network_id,
            "name": updated_network_name,
            "region": "test-region-1",
            "description": "Updated by API"
        }

        # Configure shared_api_mock side_effect for the sequence of API calls
        # This function now uses 'shared_api_mock.call_count'
        def call_api_side_effect_handler(*args, **kwargs):
            action = kwargs.get('action')
            path = kwargs.get('path')
            # value = kwargs.get('value') # For PUT/POST, available in kwargs

            # print(f"Shared API Mock called: action={action}, path={path}, call_count={shared_api_mock.call_count}")

            if action == "get" and path == "/api/v1/networks":
                if shared_api_mock.call_count == 1: # First call by select_object_tool
                    return {"status": 200, "data": [initial_network_data]}
                elif shared_api_mock.call_count == 4: # Call by select_object_tool after delete
                    return {"status": 200, "data": []}
                else:
                    self.fail(f"Unexpected GET /api/v1/networks call in mock at call_count {shared_api_mock.call_count}")
            elif action == "put" and path == f"/api/v1/networks/{new_network_id}":
                # This call comes from the test method directly, should be call_count 2
                self.assertEqual(shared_api_mock.call_count, 2, "PUT call was not the second call to shared mock")
                self.assertEqual(kwargs.get('value'), update_payload_sent, "PUT payload mismatch")
                return {"status": 200, "data": updated_network_data_from_api}
            elif action == "delete" and path == f"/api/v1/networks/{new_network_id}":
                # This call comes from the test method directly, should be call_count 3
                self.assertEqual(shared_api_mock.call_count, 3, "DELETE call was not the third call to shared mock")
                return {"status": 204, "data": None}
            
            # Fallback for unexpected calls
            self.fail(f"Unexpected call to shared_api_mock: action={action}, path={path}, args={args}, kwargs={kwargs}")

        shared_api_mock.side_effect = call_api_side_effect_handler
        
        # Patch 'call_api' where select_object_tool looks for it, and where this test file uses its own import.
        with patch('connexa_openvpn_mcp_server.connexa.selected_object.call_api', new=shared_api_mock):
            with patch('connexa_openvpn_mcp_server.test_select_object.call_api', new=shared_api_mock): # Target changed here
                # --- 1. Select the "newly created" network ---
                CURRENT_SELECTED_OBJECT.clear()
                # select_object_tool uses selected_object.call_api (which is now shared_api_mock)
                found_names, message = select_object_tool(object_type="network", name_search=new_network_name, kwargs=None)
                
                self.assertEqual(shared_api_mock.call_count, 1, "shared_api_mock not called once for initial selection")
                self.assertIn(new_network_name, found_names)
                self.assertEqual(message, f"Selected Object is {new_network_name}")
                self.assertEqual(CURRENT_SELECTED_OBJECT.object_type, "network")
                self.assertEqual(CURRENT_SELECTED_OBJECT.object_id, new_network_id)
                self.assertEqual(CURRENT_SELECTED_OBJECT.object_name, new_network_name)
                self.assertEqual(CURRENT_SELECTED_OBJECT.details, initial_network_data)

                # --- 2. "Update" the selected network (simulating direct API call from another tool) ---
                # This call uses the `call_api` imported in this test file (from connexa_api), now also shared_api_mock.
                update_response = call_api(action="put", path=f"/api/v1/networks/{CURRENT_SELECTED_OBJECT.object_id}", value=update_payload_sent)
                
                self.assertEqual(shared_api_mock.call_count, 2, "shared_api_mock not called for update (expected 2nd call)")
                self.assertEqual(update_response["status"], 200)
                self.assertEqual(update_response["data"], updated_network_data_from_api)

                # --- 3. "Delete" the selected network (simulating direct API call) ---
                delete_response = call_api(action="delete", path=f"/api/v1/networks/{CURRENT_SELECTED_OBJECT.object_id}")

                self.assertEqual(shared_api_mock.call_count, 3, "shared_api_mock not called for delete (expected 3rd call)")
                self.assertEqual(delete_response["status"], 204)

                # --- 4. Verify deletion by trying to select it again ---
                found_names_after_delete, message_after_delete = select_object_tool(object_type="network", name_search=new_network_name, kwargs=None)
                
                self.assertEqual(shared_api_mock.call_count, 4, "shared_api_mock not called for post-delete selection (expected 4th call)")
                self.assertEqual(found_names_after_delete, ["No networks found."]) # As per side_effect logic for 4th GET
                self.assertEqual(message_after_delete, "No networks available to select.")
                
                self.assertIsNone(CURRENT_SELECTED_OBJECT.object_type, "object_type not cleared")
                self.assertIsNone(CURRENT_SELECTED_OBJECT.object_id, "object_id not cleared")
                self.assertIsNone(CURRENT_SELECTED_OBJECT.object_name, "object_name not cleared")
                self.assertEqual(CURRENT_SELECTED_OBJECT.details, {}, "details not an empty dict after clearing")

        # Verify os.getenv was called by select_object_tool for CONNEXA_REGION
        mock_os_getenv.assert_any_call("CONNEXA_REGION", "us-west-1")
        self.assertTrue(mock_os_getenv.call_count >= 2) # Called by select_object_tool twice

    @patch('connexa_openvpn_mcp_server.connexa.selected_object.os.getenv')
    @patch('connexa_openvpn_mcp_server.connexa.selected_object.call_api')
    def test_select_network_with_real_data_failure(self, mock_call_api, mock_os_getenv):
        """Test select_object_tool with real API data that caused a failure."""
        mock_os_getenv.return_value = "test-region-1" # Mock CONNEXA_REGION
        
        # Real API response data from the previous failed call
        real_api_response = {
            'status': 200,
            'data': {
                'content': [
                    {
                        'id': '5f343585-72a5-4d0d-bf0d-5209245ed63e',
                        'name': 'California Office Network',
                        'egress': True,
                        'internetAccess': 'SPLIT_TUNNEL_ON',
                        'connectors': [
                            {
                                'id': '26669cdd-d3c9-4370-8dc6-4758e339f3dd',
                                'networkItemId': '5f343585-72a0-4d0d-bf0d-5209245ed63e',
                                'networkItemType': 'NETWORK',
                                'name': 'California Office Connector New',
                                'vpnRegionId': 'us-west-1',
                                'ipV4Address': '100.96.1.82/28',
                                'ipV6Address': 'fd:0:0:8105::2/64',
                                'tunnelingProtocol': 'OPENVPN',
                                'licensed': True
                            }
                        ],
                        'systemSubnets': ['100.96.1.80/28', 'fd:0:0:8105::/64'],
                        'tunnelingProtocol': 'OPENVPN'
                    },
                    {
                        'id': '50ee1d43-ced5-4894-81c4-f4c5819dfc99',
                        'name': 'Netflix Egress Network',
                        'egress': True,
                        'internetAccess': 'SPLIT_TUNNEL_ON',
                        'connectors': [
                            {
                                'id': '230c56bd-d2ea-49a7-995f-1e5402cf6893',
                                'networkItemId': '50ee1d43-ced5-4894-81c4-f4c5819dfc99',
                                'networkItemType': 'NETWORK',
                                'name': 'netflix connector',
                                'vpnRegionId': 'us-west-1',
                                'ipV4Address': '100.96.1.66/28',
                                'ipV6Address': 'fd:0:0:8104::2/64',
                                'tunnelingProtocol': 'OPENVPN',
                                'licensed': True
                            }
                        ],
                        'systemSubnets': ['100.96.1.64/28', 'fd:0:0:8104::/64'],
                        'tunnelingProtocol': 'OPENVPN'
                    }
                ],
                'totalElements': 2,
                'totalPages': 1,
                'numberOfElements': 2,
                'page': 0,
                'size': 10
            }
        }

        mock_call_api.return_value = real_api_response
        
        # Call the tool with the arguments that caused the failure
        found_names, message = select_object_tool(
            object_type="network",
            name_search="California Office Network", # This name should match one in the data
            kwargs=None
        )
        
        # Assert that the expected error message is returned
        # The exact message was "Error fetching networks: Unknown API error. Details: API call failed or returned unexpected data. Full response: ..."
        # We'll check for a significant part of it.
        self.assertIn("Error fetching networks: Unknown API error.", message)
        self.assertIn("Details: API call failed or returned unexpected data.", message)
        # Optionally, assert that the full response is included in the message
        # self.assertIn(str(real_api_response), message) # This might make the test brittle due to formatting

        # Assert that no object was selected
        self.assertIsNone(CURRENT_SELECTED_OBJECT.object_type)
        self.assertIsNone(CURRENT_SELECTED_OBJECT.object_id)
        self.assertIsNone(CURRENT_SELECTED_OBJECT.object_name)
        self.assertEqual(CURRENT_SELECTED_OBJECT.details, {})

        mock_call_api.assert_called_once_with(action="get", path="/api/v1/networks")
        mock_os_getenv.assert_any_call("CONNEXA_REGION", "us-west-1")


if __name__ == '__main__':
    unittest.main()
