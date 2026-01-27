#!/usr/bin/env python3
"""
Upload Power BI report to Power BI Service and download as PBIX.

This script uses the Power BI REST API to:
1. Upload a report definition to Power BI Service
2. Download it back as a PBIX file

Requirements:
- Azure AD app registration with Power BI permissions
- Power BI Pro or Premium license
- pbipy or requests library
"""

import os
import sys
import json
import time
import base64
from pathlib import Path
from typing import Optional, Dict, Any

try:
    import requests
except ImportError:
    print("Please install requests: pip install requests")
    sys.exit(1)


class PowerBIServiceClient:
    """Client for Power BI REST API operations."""
    
    BASE_URL = "https://api.powerbi.com/v1.0/myorg"
    
    def __init__(self, access_token: str):
        """
        Initialize with an access token.
        
        Get token via Azure AD authentication:
        https://docs.microsoft.com/en-us/power-bi/developer/embedded/get-azuread-access-token
        """
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def get_workspaces(self) -> list:
        """Get list of workspaces."""
        response = requests.get(
            f"{self.BASE_URL}/groups",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json().get("value", [])
    
    def create_report_from_pbip(self, workspace_id: str, pbip_path: str, 
                                 report_name: str) -> Dict[str, Any]:
        """
        Create a report in Power BI Service from PBIP files.
        
        Note: This is a simplified version. Full implementation would need
        to handle the semantic model separately.
        """
        # Read the report definition
        pbip_dir = Path(pbip_path)
        
        # Find report.json
        report_json_path = None
        for path in pbip_dir.rglob("report.json"):
            report_json_path = path
            break
        
        if not report_json_path:
            raise FileNotFoundError("report.json not found in PBIP")
        
        with open(report_json_path, 'r') as f:
            report_def = json.load(f)
        
        # This endpoint creates an import
        # In practice, you'd need to create a proper PBIX or use Import API
        print(f"Report definition loaded: {report_def.get('name', 'Unknown')}")
        
        return {"status": "Note: Full upload requires PBIX format or Power BI Embedded API"}
    
    def download_report_as_pbix(self, workspace_id: str, report_id: str, 
                                 output_path: str) -> bool:
        """Download a report as PBIX file."""
        url = f"{self.BASE_URL}/groups/{workspace_id}/reports/{report_id}/Export"
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded to: {output_path}")
            return True
        elif response.status_code == 202:
            # Export is async, need to poll
            export_id = response.json().get("id")
            return self._poll_export(workspace_id, report_id, export_id, output_path)
        else:
            print(f"Export failed: {response.status_code} - {response.text}")
            return False
    
    def _poll_export(self, workspace_id: str, report_id: str, 
                     export_id: str, output_path: str) -> bool:
        """Poll for export completion."""
        url = f"{self.BASE_URL}/groups/{workspace_id}/reports/{report_id}/exports/{export_id}"
        
        for _ in range(60):  # Max 5 minutes
            response = requests.get(url, headers=self.headers)
            status = response.json().get("status")
            
            if status == "Succeeded":
                # Get the file
                file_url = response.json().get("resourceLocation")
                file_response = requests.get(file_url, headers=self.headers)
                with open(output_path, 'wb') as f:
                    f.write(file_response.content)
                print(f"Downloaded to: {output_path}")
                return True
            elif status == "Failed":
                print("Export failed")
                return False
            
            print(f"Export status: {status}...")
            time.sleep(5)
        
        print("Export timed out")
        return False


def get_azure_ad_token(client_id: str, client_secret: str, tenant_id: str) -> str:
    """
    Get Azure AD access token for Power BI.
    
    Requires an Azure AD app registration with Power BI API permissions.
    """
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://analysis.windows.net/powerbi/api/.default"
    }
    
    response = requests.post(url, data=data)
    response.raise_for_status()
    
    return response.json()["access_token"]


def print_setup_instructions():
    """Print setup instructions for Power BI API access."""
    print("""
================================================================================
                Power BI Service API Setup Instructions
================================================================================

To use this script, you need:

1. AZURE AD APP REGISTRATION
   - Go to https://portal.azure.com
   - Navigate to Azure Active Directory → App registrations
   - Click "New registration"
   - Name: "Power BI Converter" (or any name)
   - Register the app
   - Note the Application (client) ID and Directory (tenant) ID

2. ADD API PERMISSIONS
   - In your app registration, go to "API permissions"
   - Add permission → Power BI Service
   - Add these permissions:
     * Report.ReadWrite.All
     * Dataset.ReadWrite.All
     * Workspace.ReadWrite.All
   - Grant admin consent

3. CREATE CLIENT SECRET
   - Go to "Certificates & secrets"
   - New client secret
   - Note the secret value (only shown once!)

4. SET ENVIRONMENT VARIABLES
   export AZURE_CLIENT_ID="your-client-id"
   export AZURE_CLIENT_SECRET="your-client-secret"
   export AZURE_TENANT_ID="your-tenant-id"

5. RUN THIS SCRIPT
   python powerbi_service_upload.py <pbip_path> <workspace_id>

================================================================================
""")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print_setup_instructions()
        print("\nUsage: python powerbi_service_upload.py <pbip_path> [workspace_id]")
        sys.exit(1)
    
    # Check for credentials
    client_id = os.environ.get("AZURE_CLIENT_ID")
    client_secret = os.environ.get("AZURE_CLIENT_SECRET")
    tenant_id = os.environ.get("AZURE_TENANT_ID")
    
    if not all([client_id, client_secret, tenant_id]):
        print_setup_instructions()
        print("\nError: Azure AD credentials not found in environment variables.")
        sys.exit(1)
    
    pbip_path = sys.argv[1]
    
    # Get access token
    print("Getting Azure AD access token...")
    token = get_azure_ad_token(client_id, client_secret, tenant_id)
    
    # Create client
    client = PowerBIServiceClient(token)
    
    # List workspaces if no workspace ID provided
    if len(sys.argv) < 3:
        print("\nAvailable workspaces:")
        workspaces = client.get_workspaces()
        for ws in workspaces:
            print(f"  - {ws['name']}: {ws['id']}")
        print("\nRe-run with workspace ID to upload.")
        sys.exit(0)
    
    workspace_id = sys.argv[2]
    print(f"\nUploading to workspace: {workspace_id}")
    
    # Upload (note: this is a placeholder - full implementation needed)
    result = client.create_report_from_pbip(workspace_id, pbip_path, "Converted Report")
    print(result)


if __name__ == "__main__":
    main()
