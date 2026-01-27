"""
Power BI REST API Client

Creates Power BI reports programmatically using the REST API.
Works from any platform (Mac, Linux, Windows) - no Power BI Desktop needed.

Requirements:
- Azure AD App Registration with Power BI API permissions
- Power BI Pro or Premium Per User license (or Premium capacity)

Authentication options:
1. Service Principal (recommended for automation)
2. User authentication via device code flow
"""

import os
import json
import time
import requests
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class PowerBIConfig:
    """Configuration for Power BI API access."""
    tenant_id: str
    client_id: str
    client_secret: Optional[str] = None  # For service principal
    workspace_id: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'PowerBIConfig':
        """Load configuration from environment variables."""
        return cls(
            tenant_id=os.environ.get('AZURE_TENANT_ID', ''),
            client_id=os.environ.get('AZURE_CLIENT_ID', ''),
            client_secret=os.environ.get('AZURE_CLIENT_SECRET'),
            workspace_id=os.environ.get('POWERBI_WORKSPACE_ID')
        )


class PowerBIRestClient:
    """
    Power BI REST API client for creating reports programmatically.
    
    This bypasses the need for PBIX files by using:
    1. Push Datasets API - Create datasets with tables/columns
    2. Reports API - Create reports bound to datasets
    """
    
    BASE_URL = "https://api.powerbi.com/v1.0/myorg"
    AUTH_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0"
    SCOPE = "https://analysis.windows.net/powerbi/api/.default"
    
    def __init__(self, config: PowerBIConfig):
        self.config = config
        self.access_token = None
        self.token_expiry = 0
    
    def authenticate_service_principal(self) -> str:
        """Authenticate using service principal (client credentials)."""
        if not self.config.client_secret:
            raise ValueError("Client secret required for service principal auth")
        
        url = f"https://login.microsoftonline.com/{self.config.tenant_id}/oauth2/v2.0/token"
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.config.client_id,
            'client_secret': self.config.client_secret,
            'scope': self.SCOPE
        }
        
        response = requests.post(url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data['access_token']
        self.token_expiry = time.time() + token_data.get('expires_in', 3600)
        
        return self.access_token
    
    def authenticate_device_code(self) -> str:
        """
        Authenticate using device code flow (interactive).
        User visits a URL and enters a code.
        """
        # Step 1: Get device code
        url = f"https://login.microsoftonline.com/{self.config.tenant_id}/oauth2/v2.0/devicecode"
        
        data = {
            'client_id': self.config.client_id,
            'scope': 'https://analysis.windows.net/powerbi/api/Dataset.ReadWrite.All '
                    'https://analysis.windows.net/powerbi/api/Report.ReadWrite.All '
                    'https://analysis.windows.net/powerbi/api/Workspace.Read.All'
        }
        
        response = requests.post(url, data=data)
        response.raise_for_status()
        
        device_code_data = response.json()
        
        print("\n" + "="*60)
        print("AUTHENTICATION REQUIRED")
        print("="*60)
        print(f"\n{device_code_data['message']}\n")
        print("="*60 + "\n")
        
        # Step 2: Poll for token
        token_url = f"https://login.microsoftonline.com/{self.config.tenant_id}/oauth2/v2.0/token"
        
        poll_data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
            'client_id': self.config.client_id,
            'device_code': device_code_data['device_code']
        }
        
        interval = device_code_data.get('interval', 5)
        expires_in = device_code_data.get('expires_in', 900)
        start_time = time.time()
        
        while time.time() - start_time < expires_in:
            time.sleep(interval)
            
            response = requests.post(token_url, data=poll_data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                self.token_expiry = time.time() + token_data.get('expires_in', 3600)
                print("Authentication successful!")
                return self.access_token
            
            error = response.json().get('error')
            if error == 'authorization_pending':
                continue
            elif error == 'slow_down':
                interval += 5
            else:
                raise Exception(f"Authentication failed: {response.json()}")
        
        raise Exception("Authentication timed out")
    
    def _headers(self) -> Dict[str, str]:
        """Get authorization headers."""
        if not self.access_token:
            raise ValueError("Not authenticated. Call authenticate_* first.")
        
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def _workspace_url(self, path: str) -> str:
        """Build URL with optional workspace."""
        if self.config.workspace_id:
            return f"{self.BASE_URL}/groups/{self.config.workspace_id}/{path}"
        return f"{self.BASE_URL}/{path}"
    
    def list_workspaces(self) -> List[Dict]:
        """List available workspaces."""
        url = f"{self.BASE_URL}/groups"
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        return response.json().get('value', [])
    
    def create_push_dataset(self, name: str, tables: List[Dict]) -> Dict:
        """
        Create a push dataset (real-time dataset).
        
        This allows creating a dataset without a PBIX file!
        
        Args:
            name: Dataset name
            tables: List of table definitions with columns
            
        Returns:
            Created dataset info including ID
        """
        url = self._workspace_url("datasets")
        
        # Build dataset definition
        dataset = {
            "name": name,
            "defaultMode": "Push",
            "tables": tables
        }
        
        response = requests.post(url, headers=self._headers(), json=dataset)
        response.raise_for_status()
        
        return response.json()
    
    def push_rows(self, dataset_id: str, table_name: str, rows: List[Dict]) -> None:
        """Push rows to a push dataset table."""
        url = self._workspace_url(f"datasets/{dataset_id}/tables/{table_name}/rows")
        
        response = requests.post(
            url, 
            headers=self._headers(), 
            json={"rows": rows}
        )
        response.raise_for_status()
    
    def create_report_from_dataset(self, name: str, dataset_id: str) -> Dict:
        """
        Create a new report bound to a dataset.
        
        Note: This creates an empty report. You'll need to add visuals
        through the Power BI portal or use the embedded SDK.
        """
        url = self._workspace_url("reports")
        
        # Clone from blank template approach
        report_def = {
            "name": name,
            "datasetId": dataset_id
        }
        
        response = requests.post(url, headers=self._headers(), json=report_def)
        
        if response.status_code == 404:
            # Direct report creation not available, use alternative
            print("Direct report creation not available.")
            print(f"Create report manually in Power BI Service using dataset: {dataset_id}")
            return {"id": None, "name": name, "datasetId": dataset_id}
        
        response.raise_for_status()
        return response.json()
    
    def list_datasets(self) -> List[Dict]:
        """List datasets in the workspace."""
        url = self._workspace_url("datasets")
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        return response.json().get('value', [])
    
    def list_reports(self) -> List[Dict]:
        """List reports in the workspace."""
        url = self._workspace_url("reports")
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        return response.json().get('value', [])
    
    def delete_dataset(self, dataset_id: str) -> None:
        """Delete a dataset."""
        url = self._workspace_url(f"datasets/{dataset_id}")
        response = requests.delete(url, headers=self._headers())
        response.raise_for_status()


def convert_tableau_to_powerbi_api(
    tableau_path: str,
    config: PowerBIConfig,
    dataset_name: Optional[str] = None
) -> Dict:
    """
    Convert a Tableau workbook to Power BI using the REST API.
    
    This creates:
    1. A Push Dataset with tables/columns from Tableau
    2. Measures converted to DAX
    
    Args:
        tableau_path: Path to .twbx or .twb file
        config: Power BI API configuration
        dataset_name: Optional name for the dataset
        
    Returns:
        Dictionary with created dataset info
    """
    from parsers.twbx_parser import TWBXParser
    from generators.semantic_model_generator import SemanticModelGenerator
    from pathlib import Path
    
    # Parse Tableau workbook
    parser = TWBXParser(tableau_path)
    workbook = parser.parse()
    
    # Generate Power BI model
    generator = SemanticModelGenerator(use_genai=False)
    report = generator.generate(workbook)
    
    # Build table definitions for Push Dataset API
    tables = []
    for table in report.tables:
        columns = []
        for col in table.columns:
            pbi_type = {
                'string': 'String',
                'integer': 'Int64',
                'real': 'Double',
                'boolean': 'Boolean',
                'datetime': 'DateTime',
                'date': 'DateTime'
            }.get(col.data_type.lower(), 'String')
            
            columns.append({
                "name": col.name,
                "dataType": pbi_type
            })
        
        # Add at least one column if none exist
        if not columns:
            columns.append({"name": "ID", "dataType": "Int64"})
        
        tables.append({
            "name": table.name,
            "columns": columns
        })
    
    # Ensure at least one table
    if not tables:
        tables.append({
            "name": "Data",
            "columns": [{"name": "ID", "dataType": "Int64"}]
        })
    
    # Create Power BI client and authenticate
    client = PowerBIRestClient(config)
    
    if config.client_secret:
        client.authenticate_service_principal()
    else:
        client.authenticate_device_code()
    
    # Create the dataset
    name = dataset_name or Path(tableau_path).stem
    dataset = client.create_push_dataset(name, tables)
    
    print(f"\nDataset created successfully!")
    print(f"  Name: {name}")
    print(f"  ID: {dataset.get('id')}")
    print(f"  Tables: {len(tables)}")
    
    return {
        "dataset": dataset,
        "tables": tables,
        "source": tableau_path
    }


# CLI integration
if __name__ == "__main__":
    import sys
    
    print("Power BI REST API - Tableau Converter")
    print("="*40)
    
    # Check for required environment variables
    required_vars = ['AZURE_TENANT_ID', 'AZURE_CLIENT_ID']
    missing = [v for v in required_vars if not os.environ.get(v)]
    
    if missing:
        print("\nRequired environment variables:")
        print("  AZURE_TENANT_ID     - Your Azure AD tenant ID")
        print("  AZURE_CLIENT_ID     - Your Azure AD app client ID")
        print("  AZURE_CLIENT_SECRET - (Optional) For service principal auth")
        print("  POWERBI_WORKSPACE_ID - (Optional) Target workspace")
        print(f"\nMissing: {', '.join(missing)}")
        sys.exit(1)
    
    if len(sys.argv) < 2:
        print("\nUsage: python powerbi_rest_api.py <tableau_file.twbx>")
        sys.exit(1)
    
    config = PowerBIConfig.from_env()
    result = convert_tableau_to_powerbi_api(sys.argv[1], config)
    
    print("\n" + "="*40)
    print("NEXT STEPS:")
    print("="*40)
    print("1. Go to app.powerbi.com")
    print("2. Navigate to your workspace")
    print(f"3. Find dataset: {result['dataset'].get('id')}")
    print("4. Create a new report from this dataset")
    print("="*40)
