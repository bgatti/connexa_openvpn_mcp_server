import unittest
import os
import sys

# Add the parent directory to the sys.path to allow importing connexa
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the actual function and global object
from connexa_openvpn_mcp_server.connexa.selected_object import select_object_tool, CURRENT_SELECTED_OBJECT

# Note: This test requires valid API credentials to be configured in the environment
# or accessible by the call_api function for it to fetch real data.

class TestSelectObjectDirectRealAPI(unittest.TestCase):

    def setUp(self):
        """Reset the global selected object before each test."""
        CURRENT_SELECTED_OBJECT.clear()
        # Set a default region for testing default selection logic
        # Ensure this region exists in your Connexa setup for the test to pass reliably
        os.environ["CONNEXA_REGION"] = "us-west-1" 

    def tearDown(self):
        """Clean up environment variables after each test."""
        if "CONNEXA_REGION" in os.environ:
            del os.environ["CONNEXA_REGION"]

    def test_select_network_by_name_real_api(self):
        """Test selecting a network by name search using the real API."""
        # Call the function with the specified arguments
        # This will now make a real API call via the imported call_api
        found_names, selection_msg = select_object_tool(
            object_type="network",
            name_search="test-network-71c7398d" # Assuming you have networks with "california" in their name
        )

        # Assertions based on expected real API behavior
        # We can't assert on exact names or counts without knowing your API data,
        # but we can assert on the type of the result and that a selection was attempted.
        self.assertIsInstance(found_names, list)
        self.assertIsInstance(selection_msg, str)
        
        # Check if an object was selected (assuming the API call was successful and found matches)
        # This assertion might need adjustment based on your actual API data and expected outcome
        # For example, if "california" always yields multiple results and your default region
        # has a network with "california" in its name, the default should be selected.
        # If "california" yields exactly one result, that one should be selected.
        # If no networks match "california", the default should be selected (if available).

        # A basic check: if the API call was successful (implied by no exception),
        # either a specific object was selected or the default was attempted.
        # Check if CURRENT_SELECTED_OBJECT has been populated
        self.assertIsNotNone(CURRENT_SELECTED_OBJECT.object_type)
        self.assertIsNotNone(CURRENT_SELECTED_OBJECT.object_id)
        self.assertIsNotNone(CURRENT_SELECTED_OBJECT.object_name)
        self.assertIsInstance(CURRENT_SELECTED_OBJECT.details, dict)

        print(f"\n--- Real API Test Results ---")
        print(f"Found Names: {found_names}")
        print(f"Selection Message: {selection_msg}")
        selected_info = CURRENT_SELECTED_OBJECT.get_selected_object_info()
        print(f"Selected Object Info: {selected_info}")
        
        # Get and print available commands for the selected object
        available_commands = CURRENT_SELECTED_OBJECT.get_available_commands()
        print(f"Available Commands: {available_commands}")
        
        print(f"-----------------------------")

    def test_select_host_default_real_api(self):
        """Test selecting a host, expecting default selection using the real API."""
        found_names, selection_msg = select_object_tool(
            object_type="host"
            # No name_search, so default selection logic will apply
        )

        self.assertIsInstance(found_names, list)
        self.assertIsInstance(selection_msg, str)
        
        self.assertIsNotNone(CURRENT_SELECTED_OBJECT.object_type, "Host object_type should be set")
        self.assertEqual(CURRENT_SELECTED_OBJECT.object_type, "host", "Selected object_type should be 'host'")
        self.assertIsNotNone(CURRENT_SELECTED_OBJECT.object_id, "Host object_id should be set")
        self.assertIsNotNone(CURRENT_SELECTED_OBJECT.object_name, "Host object_name should be set")
        self.assertIsInstance(CURRENT_SELECTED_OBJECT.details, dict, "Host details should be a dict")

        print(f"\n--- Real API Test Results (Host - Default) ---")
        print(f"Found Names: {found_names}")
        print(f"Selection Message: {selection_msg}")
        selected_info_host = CURRENT_SELECTED_OBJECT.get_selected_object_info()
        print(f"Selected Object Info: {selected_info_host}")
        available_commands = CURRENT_SELECTED_OBJECT.get_available_commands()
        print(f"Available Commands: {available_commands}")
        print(f"-----------------------------")

    def test_select_usergroup_by_name_real_api(self):
        """Test selecting a user group by name search using the real API."""
        # Assuming you have a user group with "admin" or "default" in its name, or a default group exists.
        search_term = "admin" 
        found_names, selection_msg = select_object_tool(
            object_type="usergroup",
            name_search=search_term 
        )

        self.assertIsInstance(found_names, list)
        self.assertIsInstance(selection_msg, str)

        self.assertIsNotNone(CURRENT_SELECTED_OBJECT.object_type, "UserGroup object_type should be set")
        self.assertEqual(CURRENT_SELECTED_OBJECT.object_type, "usergroup", "Selected object_type should be 'usergroup'")
        self.assertIsNotNone(CURRENT_SELECTED_OBJECT.object_id, "UserGroup object_id should be set")
        self.assertIsNotNone(CURRENT_SELECTED_OBJECT.object_name, "UserGroup object_name should be set")
        self.assertIsInstance(CURRENT_SELECTED_OBJECT.details, dict, "UserGroup details should be a dict")
        
        # If a specific group named 'admin' was found and selected, its name should be in the message.
        # Otherwise, the default group's name will be there.
        # self.assertTrue(search_term in selection_msg.lower() or "default" in selection_msg.lower(), 
        #                 f"Selection message '{selection_msg}' did not indicate selection of '{search_term}' or a default.")

        print(f"\n--- Real API Test Results (UserGroup - Name Search: '{search_term}') ---")
        print(f"Found Names: {found_names}")
        print(f"Selection Message: {selection_msg}")
        selected_info_usergroup = CURRENT_SELECTED_OBJECT.get_selected_object_info()
        print(f"Selected Object Info: {selected_info_usergroup}")
        available_commands = CURRENT_SELECTED_OBJECT.get_available_commands()
        print(f"Available Commands: {available_commands}")
        print(f"-----------------------------")

    # You can add more test cases here for default selection, exact match, etc.
    # adapting them to expect real API behavior.

if __name__ == '__main__':
    # Note: Running this requires your environment to be configured
    # to connect to the OpenVPN Connexa API.
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
