#!/usr/bin/env python3
"""
Power BI Service Integration.

This module provides functionality to:
1. Upload reports to Power BI Service
2. Download reports as PBIX
3. Convert PBIP to PBIX via the cloud

Supports multiple authentication methods:
- Service Principal (for automation)
- Interactive browser login (for manual use)
- Device code flow (for headless environments)
"""

import os
import sys
import json
import time
import zipfile
import tempfile
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

try:
    import requests
except ImportError:
    print("Installing requests...")
    os.system(f"{sys.executable} -m pip install requests --quiet")
    import requests


class AuthMethod(Enum):
    """Authentication methods for Power BI."""
    SERVICE_PRINCIPAL = "service_principal"
    INTERACTIVE = "interactive"
    DEVICE_CODE = "device_code"


@dataclass
class PowerBIConfig:
    """Configuration for Power BI Service connection."""
    # Azure AD credentials (for service principal)
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tenant_id: Optional[str] = None
    
    # For interactive auth
    redirect_uri: str = "http://localhost:8080"
    
    # Power BI settings
    workspace_id: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'PowerBIConfig':
        """Load configuration from environment variables."""
        return cls(
            client_id=os.environ.get("AZURE_CLIENT_ID") or os.environ.get("POWERBI_CLIENT_ID"),
            client_secret=os.environ.get("AZURE_CLIENT_SECRET") or os.environ.get("POWERBI_CLIENT_SECRET"),
            tenant_id=os.environ.get("AZURE_TENANT_ID") or os.environ.get("POWERBI_TENANT_ID"),
            workspace_id=os.environ.get("POWERBI_WORKSPACE_ID"),
        )


class PowerBIServiceClient:
    """
    Client for Power BI REST API operations.
    
    Provides methods to:
    - List workspaces and reports
    - Import reports (including from PBIP)
    - Export reports as PBIX
    """
    
    BASE_URL = "https://api.powerbi.com/v1.0/myorg"
    AUTH_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0"
    SCOPE = "https://analysis.windows.net/powerbi/api/.default"
    
    def __init__(self, config: Optional[PowerBIConfig] = None):
        """Initialize the client."""
        self.config = config or PowerBIConfig.from_env()
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0
    
    @property
    def access_token(self) -> str:
        """Get or refresh access token."""
        if not self._access_token or time.time() >= self._token_expiry:
            self._authenticate()
        return self._access_token
    
    @property
    def headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def _authenticate(self) -> None:
        """Authenticate with Azure AD."""
        if not self.config.tenant_id:
            raise ValueError("Tenant ID is required. Set AZURE_TENANT_ID environment variable.")
        
        if self.config.client_id and self.config.client_secret:
            self._authenticate_service_principal()
        else:
            self._authenticate_device_code()
    
    def _authenticate_service_principal(self) -> None:
        """Authenticate using service principal credentials."""
        url = f"https://login.microsoftonline.com/{self.config.tenant_id}/oauth2/v2.0/token"
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "scope": self.SCOPE
        }
        
        response = requests.post(url, data=data)
        
        if response.status_code != 200:
            raise Exception(f"Authentication failed: {response.text}")
        
        token_data = response.json()
        self._access_token = token_data["access_token"]
        self._token_expiry = time.time() + token_data.get("expires_in", 3600) - 60
        
        print("✓ Authenticated with service principal")
    
    def _authenticate_device_code(self) -> None:
        """Authenticate using device code flow (interactive)."""
        # Use default Microsoft Power BI public client ID
        client_id = self.config.client_id or "ea0616ba-638b-4df5-95b9-636659ae5121"
        
        # Step 1: Get device code
        device_code_url = f"https://login.microsoftonline.com/{self.config.tenant_id}/oauth2/v2.0/devicecode"
        
        response = requests.post(device_code_url, data={
            "client_id": client_id,
            "scope": "https://analysis.windows.net/powerbi/api/Report.ReadWrite.All "
                    "https://analysis.windows.net/powerbi/api/Dataset.ReadWrite.All "
                    "https://analysis.windows.net/powerbi/api/Workspace.ReadWrite.All offline_access"
        })
        
        if response.status_code != 200:
            raise Exception(f"Failed to get device code: {response.text}")
        
        device_data = response.json()
        
        print("\n" + "="*60)
        print("AUTHENTICATION REQUIRED")
        print("="*60)
        print(f"\n{device_data['message']}\n")
        print("="*60 + "\n")
        
        # Step 2: Poll for token
        token_url = f"https://login.microsoftonline.com/{self.config.tenant_id}/oauth2/v2.0/token"
        
        interval = device_data.get("interval", 5)
        expires_in = device_data.get("expires_in", 900)
        start_time = time.time()
        
        while time.time() - start_time < expires_in:
            time.sleep(interval)
            
            response = requests.post(token_url, data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": client_id,
                "device_code": device_data["device_code"]
            })
            
            if response.status_code == 200:
                token_data = response.json()
                self._access_token = token_data["access_token"]
                self._token_expiry = time.time() + token_data.get("expires_in", 3600) - 60
                print("✓ Authentication successful!")
                return
            
            error = response.json().get("error")
            if error == "authorization_pending":
                continue
            elif error == "authorization_declined":
                raise Exception("Authorization was declined by user")
            elif error == "expired_token":
                raise Exception("Device code expired. Please try again.")
            else:
                # Some other error
                continue
        
        raise Exception("Authentication timed out. Please try again.")
    
    # =========================================================================
    # Workspace Operations
    # =========================================================================
    
    def list_workspaces(self) -> List[Dict[str, Any]]:
        """Get list of workspaces the user has access to."""
        response = requests.get(
            f"{self.BASE_URL}/groups",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json().get("value", [])
    
    def get_workspace(self, workspace_id: str) -> Dict[str, Any]:
        """Get workspace details."""
        response = requests.get(
            f"{self.BASE_URL}/groups/{workspace_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    # =========================================================================
    # Report Operations
    # =========================================================================
    
    def list_reports(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List reports in a workspace."""
        if workspace_id:
            url = f"{self.BASE_URL}/groups/{workspace_id}/reports"
        else:
            url = f"{self.BASE_URL}/reports"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json().get("value", [])
    
    def get_report(self, report_id: str, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """Get report details."""
        if workspace_id:
            url = f"{self.BASE_URL}/groups/{workspace_id}/reports/{report_id}"
        else:
            url = f"{self.BASE_URL}/reports/{report_id}"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def delete_report(self, report_id: str, workspace_id: Optional[str] = None) -> bool:
        """Delete a report."""
        if workspace_id:
            url = f"{self.BASE_URL}/groups/{workspace_id}/reports/{report_id}"
        else:
            url = f"{self.BASE_URL}/reports/{report_id}"
        
        response = requests.delete(url, headers=self.headers)
        return response.status_code == 200
    
    # =========================================================================
    # Import Operations
    # =========================================================================
    
    def import_pbix(self, pbix_path: str, report_name: str,
                    workspace_id: Optional[str] = None,
                    overwrite: bool = True) -> Dict[str, Any]:
        """
        Import a PBIX file to Power BI Service.
        
        Args:
            pbix_path: Path to the PBIX file
            report_name: Name for the report in Power BI
            workspace_id: Target workspace (None for My Workspace)
            overwrite: Whether to overwrite if report exists
            
        Returns:
            Import result with report and dataset IDs
        """
        if workspace_id:
            url = f"{self.BASE_URL}/groups/{workspace_id}/imports"
        else:
            url = f"{self.BASE_URL}/imports"
        
        params = {
            "datasetDisplayName": report_name,
            "nameConflict": "CreateOrOverwrite" if overwrite else "Abort"
        }
        
        with open(pbix_path, 'rb') as f:
            files = {'file': (f"{report_name}.pbix", f, 'application/octet-stream')}
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            response = requests.post(url, params=params, files=files, headers=headers)
        
        if response.status_code not in [200, 202]:
            raise Exception(f"Import failed: {response.status_code} - {response.text}")
        
        import_info = response.json()
        
        # Poll for import completion
        return self._poll_import(import_info["id"], workspace_id)
    
    def _poll_import(self, import_id: str, workspace_id: Optional[str] = None,
                     timeout: int = 300) -> Dict[str, Any]:
        """Poll for import completion."""
        if workspace_id:
            url = f"{self.BASE_URL}/groups/{workspace_id}/imports/{import_id}"
        else:
            url = f"{self.BASE_URL}/imports/{import_id}"
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                time.sleep(2)
                continue
            
            import_info = response.json()
            status = import_info.get("importState")
            
            if status == "Succeeded":
                print(f"✓ Import completed successfully")
                return import_info
            elif status == "Failed":
                raise Exception(f"Import failed: {import_info}")
            
            print(f"  Import status: {status}...")
            time.sleep(3)
        
        raise Exception("Import timed out")
    
    # =========================================================================
    # Export Operations
    # =========================================================================
    
    def export_report_to_pbix(self, report_id: str, output_path: str,
                              workspace_id: Optional[str] = None) -> str:
        """
        Export a report as PBIX file.
        
        Args:
            report_id: ID of the report to export
            output_path: Path to save the PBIX file
            workspace_id: Workspace containing the report
            
        Returns:
            Path to the saved PBIX file
        """
        if workspace_id:
            url = f"{self.BASE_URL}/groups/{workspace_id}/reports/{report_id}/Export"
        else:
            url = f"{self.BASE_URL}/reports/{report_id}/Export"
        
        print(f"  Exporting report {report_id}...")
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            # Direct download
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"✓ Exported to: {output_path}")
            return output_path
        
        elif response.status_code == 202:
            # Async export - need to poll
            export_info = response.json()
            return self._poll_export(
                report_id, export_info.get("id"), 
                output_path, workspace_id
            )
        
        else:
            raise Exception(f"Export failed: {response.status_code} - {response.text}")
    
    def _poll_export(self, report_id: str, export_id: str, 
                     output_path: str, workspace_id: Optional[str] = None,
                     timeout: int = 300) -> str:
        """Poll for export completion and download."""
        if workspace_id:
            status_url = f"{self.BASE_URL}/groups/{workspace_id}/reports/{report_id}/exports/{export_id}"
        else:
            status_url = f"{self.BASE_URL}/reports/{report_id}/exports/{export_id}"
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = requests.get(status_url, headers=self.headers)
            
            if response.status_code != 200:
                time.sleep(2)
                continue
            
            export_info = response.json()
            status = export_info.get("status")
            
            if status == "Succeeded":
                # Download the file
                file_url = export_info.get("resourceLocation")
                file_response = requests.get(file_url, headers=self.headers)
                
                with open(output_path, 'wb') as f:
                    f.write(file_response.content)
                
                print(f"✓ Exported to: {output_path}")
                return output_path
            
            elif status == "Failed":
                raise Exception(f"Export failed: {export_info}")
            
            print(f"  Export status: {status}...")
            time.sleep(3)
        
        raise Exception("Export timed out")
    
    # =========================================================================
    # PBIP to PBIX Conversion
    # =========================================================================
    
    def convert_pbip_to_pbix(self, pbip_path: str, output_path: str,
                             workspace_id: Optional[str] = None,
                             cleanup: bool = True) -> str:
        """
        Convert a PBIP folder to PBIX by uploading to Power BI Service
        and downloading as PBIX.
        
        Args:
            pbip_path: Path to the PBIP folder
            output_path: Path to save the PBIX file
            workspace_id: Workspace to use for conversion
            cleanup: Whether to delete the temporary report after conversion
            
        Returns:
            Path to the saved PBIX file
        """
        workspace_id = workspace_id or self.config.workspace_id
        
        if not workspace_id:
            # Use the first workspace available
            workspaces = self.list_workspaces()
            if not workspaces:
                raise Exception("No workspaces available. Create a workspace in Power BI Service first.")
            workspace_id = workspaces[0]["id"]
            print(f"Using workspace: {workspaces[0]['name']}")
        
        pbip_dir = Path(pbip_path)
        report_name = pbip_dir.stem + "_temp_conversion"
        
        print(f"\nConverting PBIP to PBIX via Power BI Service...")
        print(f"  Source: {pbip_path}")
        print(f"  Target: {output_path}")
        
        # Step 1: Create a temporary PBIX from PBIP
        # Note: We need to package the PBIP as PBIX-like structure
        temp_pbix = self._package_pbip_for_upload(pbip_dir)
        
        try:
            # Step 2: Import to Power BI Service
            print("\n[1/3] Uploading to Power BI Service...")
            import_result = self.import_pbix(
                temp_pbix, report_name, workspace_id, overwrite=True
            )
            
            report_id = None
            if import_result.get("reports"):
                report_id = import_result["reports"][0]["id"]
            
            if not report_id:
                raise Exception("No report ID returned from import")
            
            # Step 3: Export as PBIX
            print("\n[2/3] Exporting as PBIX...")
            self.export_report_to_pbix(report_id, output_path, workspace_id)
            
            # Step 4: Cleanup
            if cleanup:
                print("\n[3/3] Cleaning up temporary report...")
                self.delete_report(report_id, workspace_id)
                print("✓ Cleanup complete")
            
            print(f"\n{'='*60}")
            print(f"✓ CONVERSION COMPLETE")
            print(f"  Output: {output_path}")
            print(f"{'='*60}\n")
            
            return output_path
            
        finally:
            # Clean up temp file
            if Path(temp_pbix).exists():
                os.remove(temp_pbix)
    
    def _package_pbip_for_upload(self, pbip_dir: Path) -> str:
        """
        Package PBIP folder into a format that can be uploaded.
        
        Note: This creates a minimal PBIX-like structure. For full
        functionality, you may need to use Power BI Desktop.
        """
        # Find the semantic model and report folders
        semantic_model_dir = None
        report_dir = None
        
        for item in pbip_dir.iterdir():
            if item.is_dir():
                if "SemanticModel" in item.name:
                    semantic_model_dir = item
                elif "Report" in item.name:
                    report_dir = item
        
        if not report_dir:
            raise Exception("No Report folder found in PBIP")
        
        # Create a temporary PBIX (which is a ZIP file)
        temp_dir = tempfile.mkdtemp()
        temp_pbix = os.path.join(temp_dir, "temp_upload.pbix")
        
        with zipfile.ZipFile(temp_pbix, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add [Content_Types].xml
            content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="json" ContentType="application/json"/>
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Override PartName="/Report/Layout" ContentType="application/json"/>
    <Override PartName="/Settings" ContentType="application/json"/>
    <Override PartName="/Metadata" ContentType="application/json"/>
    <Override PartName="/DiagramState" ContentType="application/json"/>
</Types>'''
            zf.writestr('[Content_Types].xml', content_types)
            
            # Add _rels/.rels
            rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.microsoft.com/packaging/2006/relationships/report" Target="/Report/Layout"/>
</Relationships>'''
            zf.writestr('_rels/.rels', rels)
            
            # Find and add report layout
            layout_file = report_dir / "definition" / "report.json"
            if layout_file.exists():
                with open(layout_file, 'r') as f:
                    layout_content = f.read()
                zf.writestr('Report/Layout', layout_content)
            
            # Add minimal Settings
            settings = '{"version":"1.0"}'
            zf.writestr('Settings', settings)
            
            # Add Metadata
            metadata = '{"version":"1.0","type":"report"}'
            zf.writestr('Metadata', metadata)
        
        return temp_pbix


def main():
    """CLI for Power BI Service operations."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Power BI Service Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available workspaces
  python powerbi_service.py workspaces
  
  # Convert PBIP to PBIX
  python powerbi_service.py convert output/myreport.pbip -o myreport.pbix
  
  # List reports in a workspace
  python powerbi_service.py reports --workspace <workspace-id>

Environment Variables:
  AZURE_TENANT_ID       Your Azure AD tenant ID (required)
  AZURE_CLIENT_ID       Service principal client ID (optional)
  AZURE_CLIENT_SECRET   Service principal secret (optional)
  POWERBI_WORKSPACE_ID  Default workspace ID (optional)
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Workspaces command
    ws_parser = subparsers.add_parser("workspaces", help="List workspaces")
    
    # Reports command
    reports_parser = subparsers.add_parser("reports", help="List reports")
    reports_parser.add_argument("--workspace", "-w", help="Workspace ID")
    
    # Convert command
    convert_parser = subparsers.add_parser("convert", help="Convert PBIP to PBIX")
    convert_parser.add_argument("pbip_path", help="Path to PBIP folder")
    convert_parser.add_argument("-o", "--output", help="Output PBIX path")
    convert_parser.add_argument("--workspace", "-w", help="Workspace ID to use")
    convert_parser.add_argument("--no-cleanup", action="store_true", 
                                help="Don't delete temporary report after conversion")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export report as PBIX")
    export_parser.add_argument("report_id", help="Report ID to export")
    export_parser.add_argument("-o", "--output", required=True, help="Output PBIX path")
    export_parser.add_argument("--workspace", "-w", help="Workspace ID")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Check for tenant ID
    if not os.environ.get("AZURE_TENANT_ID"):
        print("\n" + "="*60)
        print("SETUP REQUIRED")
        print("="*60)
        print("\nYou need to set the AZURE_TENANT_ID environment variable.")
        print("\nTo find your tenant ID:")
        print("  1. Go to https://portal.azure.com")
        print("  2. Search for 'Azure Active Directory'")
        print("  3. Copy the 'Tenant ID' from the Overview page")
        print("\nThen run:")
        print("  export AZURE_TENANT_ID='your-tenant-id-here'")
        print("\nFor automated/service use, also set:")
        print("  export AZURE_CLIENT_ID='your-client-id'")
        print("  export AZURE_CLIENT_SECRET='your-client-secret'")
        print("="*60 + "\n")
        return
    
    # Create client
    client = PowerBIServiceClient()
    
    try:
        if args.command == "workspaces":
            workspaces = client.list_workspaces()
            print("\nAvailable Workspaces:")
            print("-" * 60)
            for ws in workspaces:
                print(f"  {ws['name']}")
                print(f"    ID: {ws['id']}")
                print()
        
        elif args.command == "reports":
            reports = client.list_reports(args.workspace)
            print("\nReports:")
            print("-" * 60)
            for report in reports:
                print(f"  {report['name']}")
                print(f"    ID: {report['id']}")
                print()
        
        elif args.command == "convert":
            output_path = args.output or args.pbip_path.replace(".pbip", ".pbix")
            client.convert_pbip_to_pbix(
                args.pbip_path,
                output_path,
                workspace_id=args.workspace,
                cleanup=not args.no_cleanup
            )
        
        elif args.command == "export":
            client.export_report_to_pbix(
                args.report_id,
                args.output,
                workspace_id=args.workspace
            )
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
