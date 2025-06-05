import unittest
from typing import Dict, Any, List

# Assuming the test file is in connexa_openvpn_mcp_server/
# and dynamic_connector.py is in connexa_openvpn_mcp_server/connexa/
from connexa.dynamic_connector import get_connector_command_definitions

class TestDynamicConnector(unittest.TestCase):

    def test_get_ovpn_connector_commands(self):
        """Test command definitions for a standard OpenVPN connector."""
        connector_id = "conn_ovpn123"
        connector_name = "TestOVPNConnector"
        connector_details: Dict[str, Any] = {
            "id": connector_id,
            "name": connector_name,
            "networkItemId": "net_abc",
            "networkItemType": "NETWORK",
            "tunnelingProtocol": "OPENVPN",
            "vpnRegionId": "us-west-1"
        }

        commands = get_connector_command_definitions(connector_id, connector_name, connector_details)
        self.assertIsInstance(commands, list)
        self.assertTrue(len(commands) >= 4) # generate, revoke, encrypt, bundle

        expected_commands = {
            "generate_profile": {
                "method": "post", 
                "path_template": f"/api/v1/networks/connectors/{connector_id}/profile",
                "params_for_call_api": ["vpn_region_id"]
            },
            "revoke_profile": {
                "method": "delete",
                "path_template": f"/api/v1/networks/connectors/{connector_id}/profile"
            },
            "encrypt_profile": {
                "method": "post",
                "path_template": f"/api/v1/networks/connectors/{connector_id}/profile/encrypt"
            },
            "get_bundled_app": {
                "method": "post",
                "path_template": f"/api/v1/networks/connectors/{connector_id}/profile/bundle",
                "params_for_call_api": ["type"]
            }
        }

        for cmd_name, expected_attrs in expected_commands.items():
            command_def = next((cmd for cmd in commands if cmd["name"] == cmd_name), None)
            self.assertIsNotNone(command_def, f"Command '{cmd_name}' not found.")
            self.assertEqual(command_def["method"], expected_attrs["method"])
            self.assertEqual(command_def["path_template"], expected_attrs["path_template"])
            if "params_for_call_api" in expected_attrs:
                self.assertEqual(command_def["params_for_call_api"], expected_attrs["params_for_call_api"])
        
        # Check that IPsec commands are NOT present
        ipsec_cmds = ["ipsec_start", "ipsec_stop"]
        for ipsec_cmd_name in ipsec_cmds:
            command_def = next((cmd for cmd in commands if cmd["name"] == ipsec_cmd_name), None)
            self.assertIsNone(command_def, f"IPsec command '{ipsec_cmd_name}' should not be present for OVPN connector.")


    def test_get_ipsec_connector_commands(self):
        """Test command definitions for an IPsec connector."""
        connector_id = "conn_ipsec789"
        connector_name = "TestIPSECConnector"
        connector_details: Dict[str, Any] = {
            "id": connector_id,
            "name": connector_name,
            "networkItemId": "net_xyz",
            "networkItemType": "NETWORK",
            "tunnelingProtocol": "IPSEC",
            "vpnRegionId": "eu-central-1"
        }

        commands = get_connector_command_definitions(connector_id, connector_name, connector_details)
        self.assertIsInstance(commands, list)
        # Should have the 4 base + 2 IPsec commands
        self.assertTrue(len(commands) >= 6) 

        # Check for IPsec specific commands
        expected_ipsec_commands = {
            "ipsec_start": {
                "method": "post",
                "path_template": f"/api/v1/networks/connectors/{connector_id}/ipsec/start"
            },
            "ipsec_stop": {
                "method": "post",
                "path_template": f"/api/v1/networks/connectors/{connector_id}/ipsec/stop"
            }
        }

        for cmd_name, expected_attrs in expected_ipsec_commands.items():
            command_def = next((cmd for cmd in commands if cmd["name"] == cmd_name), None)
            self.assertIsNotNone(command_def, f"IPsec command '{cmd_name}' not found for IPsec connector.")
            self.assertEqual(command_def["method"], expected_attrs["method"])
            self.assertEqual(command_def["path_template"], expected_attrs["path_template"])

        # Also check one of the base commands to ensure they are still there
        generate_profile_cmd = next((cmd for cmd in commands if cmd["name"] == "generate_profile"), None)
        self.assertIsNotNone(generate_profile_cmd)
        self.assertEqual(generate_profile_cmd["path_template"], f"/api/v1/networks/connectors/{connector_id}/profile")


if __name__ == "__main__":
    unittest.main()
