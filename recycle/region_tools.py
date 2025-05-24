import httpx
import sys
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR # Using INTERNAL_ERROR for now
from .user_tools import get_async_client # Changed import

# BASE_URL is no longer needed as it's part of the async client

async def get_vpn_regions():
    """
    Fetches VPN regions from the Cloud Connexa API.
    Corresponds to the getVpnRegions operationId in swagger.json.
    """
    print("get_vpn_regions: Entered function", file=sys.stderr)
    client: httpx.AsyncClient | None = None # Initialize client to None, type hint allows None
    try:
        client = await get_async_client() # Use the new async client
        # The client now has base_url configured
        url = "/api/v1/regions" # Relative URL
        print(f"get_vpn_regions: Requesting URL: {client.base_url}{url}", file=sys.stderr)
        
        response = await client.get(url)
        print(f"get_vpn_regions: Response status code: {response.status_code}", file=sys.stderr)
        
        response.raise_for_status() # Raise an exception for HTTP error codes
        
        regions_data = response.json()
        print(f"get_vpn_regions: Successfully fetched regions data: {type(regions_data)}", file=sys.stderr)
        return regions_data # Swagger indicates this returns an array of VpnRegionResponse

    except McpError: # Re-raise McpError from get_async_client
        raise
    except httpx.HTTPStatusError as e:
        print(f"get_vpn_regions: HTTPStatusError: {e.response.status_code} - {e.response.text}", file=sys.stderr)
        error_message = f"API request failed with status {e.response.status_code}"
        try:
            error_details = e.response.json()
            error_message += f": {error_details.get('errorMessage', e.response.text)}"
        except Exception: # If parsing error_details fails
            error_message += f": {e.response.text}"
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=error_message)) # Removed details
    except httpx.RequestError as e:
        print(f"get_vpn_regions: RequestError: {e}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"API request failed: {str(e)}")) # Removed details
    except Exception as e:
        print(f"get_vpn_regions: Unexpected exception: {e}", file=sys.stderr)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"An unexpected error occurred while fetching VPN regions: {str(e)}")) # Removed details
    finally:
        if client: # client can be None if get_async_client() fails before assignment
            await client.aclose()
