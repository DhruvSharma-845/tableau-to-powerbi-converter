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
import uuid
import requests
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from functools import wraps


def retry_on_rate_limit(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator to retry API calls on rate limit (429) errors."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:
                        if attempt < max_retries:
                            delay = base_delay * (2 ** attempt)
                            retry_after = e.response.headers.get('Retry-After', delay)
                            time.sleep(float(retry_after))
                            continue
                    last_error = e
                    raise
            raise last_error
        return wrapper
    return decorator


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
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate configuration and return any errors."""
        errors = []
        if not self.tenant_id:
            errors.append("AZURE_TENANT_ID is required")
        if not self.client_id:
            errors.append("AZURE_CLIENT_ID is required")
        return len(errors) == 0, errors


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
    
    def delete_report(self, report_id: str) -> None:
        """Delete a report."""
        url = self._workspace_url(f"reports/{report_id}")
        response = requests.delete(url, headers=self._headers())
        response.raise_for_status()
    
    @retry_on_rate_limit(max_retries=3)
    def update_dataset_tables(self, dataset_id: str, tables: List[Dict]) -> None:
        """Update table schema in a dataset."""
        for table in tables:
            url = self._workspace_url(f"datasets/{dataset_id}/tables/{table['name']}")
            response = requests.put(url, headers=self._headers(), json=table)
            response.raise_for_status()
    
    @retry_on_rate_limit(max_retries=3)
    def add_measures_to_dataset(self, dataset_id: str, measures: List[Dict]) -> Dict:
        """
        Add DAX measures to a dataset.
        
        Note: Push datasets have limited support for measures.
        For full measure support, consider using Import API or XMLA endpoint.
        """
        # Push datasets don't support adding measures directly
        # Return info about the measures that would be added
        return {
            "dataset_id": dataset_id,
            "measures_count": len(measures),
            "measures": measures,
            "note": "Measures must be added manually in Power BI Service or via XMLA endpoint"
        }
    
    def get_dataset(self, dataset_id: str) -> Dict:
        """Get dataset details."""
        url = self._workspace_url(f"datasets/{dataset_id}")
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        return response.json()
    
    def get_report(self, report_id: str) -> Dict:
        """Get report details."""
        url = self._workspace_url(f"reports/{report_id}")
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        return response.json()
    
    def clone_report(self, report_id: str, name: str, target_dataset_id: Optional[str] = None) -> Dict:
        """Clone an existing report."""
        url = self._workspace_url(f"reports/{report_id}/Clone")
        
        body = {"name": name}
        if target_dataset_id:
            body["targetModelId"] = target_dataset_id
        if self.config.workspace_id:
            body["targetWorkspaceId"] = self.config.workspace_id
        
        response = requests.post(url, headers=self._headers(), json=body)
        response.raise_for_status()
        return response.json()
    
    def rebind_report(self, report_id: str, dataset_id: str) -> None:
        """Rebind a report to a different dataset."""
        url = self._workspace_url(f"reports/{report_id}/Rebind")
        body = {"datasetId": dataset_id}
        response = requests.post(url, headers=self._headers(), json=body)
        response.raise_for_status()
    
    def get_report_pages(self, report_id: str) -> List[Dict]:
        """Get pages in a report."""
        url = self._workspace_url(f"reports/{report_id}/pages")
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        return response.json().get('value', [])
    
    def export_report(self, report_id: str, format: str = "PBIX") -> bytes:
        """
        Export a report to file format.
        
        Args:
            report_id: Report ID
            format: Export format (PBIX, PDF, PPTX, PNG)
        """
        url = self._workspace_url(f"reports/{report_id}/Export")
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        return response.content
    
    def get_workspace_url(self) -> str:
        """Get the Power BI Service URL for this workspace."""
        if self.config.workspace_id:
            return f"https://app.powerbi.com/groups/{self.config.workspace_id}"
        return "https://app.powerbi.com"
    
    def get_report_url(self, report_id: str) -> str:
        """Get the direct URL to a report."""
        base = self.get_workspace_url()
        return f"{base}/reports/{report_id}"
    
    def get_dataset_url(self, dataset_id: str) -> str:
        """Get the direct URL to a dataset."""
        base = self.get_workspace_url()
        return f"{base}/datasets/{dataset_id}"


class PowerBIReportBuilder:
    """
    Helper class to build report structures for Power BI API.
    
    Since the REST API has limited support for creating visuals directly,
    this class prepares the data structures that can be used with:
    1. Import API (for PBIX imports)
    2. Embedded SDK (for web-based report authoring)
    3. Manual creation in Power BI Service
    """
    
    # Visual type mappings for Power BI
    VISUAL_TYPES = {
        'bar': 'clusteredBarChart',
        'column': 'clusteredColumnChart',
        'line': 'lineChart',
        'area': 'areaChart',
        'pie': 'pieChart',
        'donut': 'donutChart',
        'scatter': 'scatterChart',
        'map': 'map',
        'table': 'tableEx',
        'matrix': 'pivotTable',
        'card': 'card',
        'kpi': 'kpi',
        'slicer': 'slicer',
        'treemap': 'treemap',
        'funnel': 'funnel',
        'gauge': 'gauge',
    }
    
    def __init__(self, report_name: str, dataset_id: str):
        self.report_name = report_name
        self.dataset_id = dataset_id
        self.pages: List[Dict] = []
        self.visuals: Dict[str, List[Dict]] = {}  # page_name -> visuals
    
    def add_page(self, name: str, display_name: str = None, 
                 width: int = 1280, height: int = 720) -> 'PowerBIReportBuilder':
        """Add a page to the report."""
        page = {
            "name": name,
            "displayName": display_name or name,
            "width": width,
            "height": height,
        }
        self.pages.append(page)
        self.visuals[name] = []
        return self
    
    def add_visual(self, page_name: str, visual_type: str, 
                   title: str, x: int, y: int, width: int, height: int,
                   category_fields: List[str] = None,
                   value_fields: List[str] = None,
                   legend_field: str = None) -> 'PowerBIReportBuilder':
        """Add a visual to a page."""
        if page_name not in self.visuals:
            self.add_page(page_name)
        
        # Map visual type
        pbi_type = self.VISUAL_TYPES.get(visual_type.lower(), 'card')
        
        visual = {
            "id": str(uuid.uuid4()),
            "visualType": pbi_type,
            "title": title,
            "position": {
                "x": x,
                "y": y,
                "width": width,
                "height": height,
            },
            "dataBindings": {
                "category": category_fields or [],
                "values": value_fields or [],
                "legend": legend_field,
            }
        }
        
        self.visuals[page_name].append(visual)
        return self
    
    def build(self) -> Dict:
        """Build the report definition."""
        return {
            "name": self.report_name,
            "datasetId": self.dataset_id,
            "pages": [
                {
                    **page,
                    "visuals": self.visuals.get(page["name"], [])
                }
                for page in self.pages
            ]
        }
    
    def to_instructions(self) -> str:
        """Generate human-readable instructions for creating this report."""
        lines = [
            f"# Power BI Report: {self.report_name}",
            f"Dataset ID: {self.dataset_id}",
            "",
            "## Pages and Visuals",
            ""
        ]
        
        for page in self.pages:
            page_name = page.get("displayName", page["name"])
            lines.append(f"### Page: {page_name}")
            lines.append(f"Size: {page['width']} x {page['height']}")
            lines.append("")
            
            visuals = self.visuals.get(page["name"], [])
            for i, visual in enumerate(visuals, 1):
                lines.append(f"#### Visual {i}: {visual['title']}")
                lines.append(f"- Type: {visual['visualType']}")
                pos = visual['position']
                lines.append(f"- Position: ({pos['x']}, {pos['y']})")
                lines.append(f"- Size: {pos['width']} x {pos['height']}")
                
                bindings = visual['dataBindings']
                if bindings.get('category'):
                    lines.append(f"- Category: {', '.join(bindings['category'])}")
                if bindings.get('values'):
                    lines.append(f"- Values: {', '.join(bindings['values'])}")
                if bindings.get('legend'):
                    lines.append(f"- Legend: {bindings['legend']}")
                lines.append("")
        
        return "\n".join(lines)


def convert_tableau_to_powerbi_api(
    tableau_path: str,
    config: PowerBIConfig,
    dataset_name: Optional[str] = None,
    create_report_structure: bool = True,
    verbose: bool = True,
    validate: bool = True,
    fail_on_validation_errors: bool = False
) -> Dict:
    """
    Convert a Tableau workbook to Power BI using the REST API.
    
    This creates:
    1. A Push Dataset with tables/columns from Tableau
    2. Measures converted to DAX (stored as metadata)
    3. Report structure definition with pages and visuals
    
    Args:
        tableau_path: Path to .twbx or .twb file
        config: Power BI API configuration
        dataset_name: Optional name for the dataset
        create_report_structure: Whether to create report structure definition
        verbose: Print progress messages
        validate: Whether to run pre-flight validation
        fail_on_validation_errors: If True, raise exception on validation errors
        
    Returns:
        Dictionary with created dataset info, report structure, and URLs
    """
    from parsers.twbx_parser import TWBXParser
    from generators.semantic_model_generator import SemanticModelGenerator
    from translators.visual_mapper import VisualMapper
    from pathlib import Path
    
    # Validate config
    is_valid, errors = config.validate()
    if not is_valid:
        raise ValueError(f"Invalid configuration: {', '.join(errors)}")
    
    # Parse Tableau workbook
    if verbose:
        print(f"Parsing Tableau workbook: {tableau_path}")
    
    parser = TWBXParser(tableau_path)
    workbook = parser.parse()
    
    if verbose:
        print(f"  Found {len(workbook.datasources)} data source(s)")
        print(f"  Found {len(workbook.worksheets)} worksheet(s)")
        print(f"  Found {len(workbook.dashboards)} dashboard(s)")
    
    # Generate Power BI model
    if verbose:
        print("Generating Power BI model...")
    
    generator = SemanticModelGenerator(use_genai=False)
    pbi_report = generator.generate(workbook)
    
    # Map visuals
    visual_mapper = VisualMapper()
    worksheets_dict = {ws.name: ws for ws in workbook.worksheets}
    
    # Add pages from dashboards
    for dashboard in workbook.dashboards:
        page = visual_mapper.map_dashboard_to_page(dashboard, worksheets_dict)
        pbi_report.pages.append(page)
    
    # If no dashboards, create pages from worksheets
    if not workbook.dashboards:
        for ws in workbook.worksheets:
            result = visual_mapper.map_worksheet(ws)
            from models.powerbi_models import PowerBIPage
            page = PowerBIPage(
                name=ws.name.replace(" ", "_"),
                display_name=ws.name,
                visuals=[result.powerbi_visual]
            )
            pbi_report.pages.append(page)
    
    # Run pre-flight validation
    validation_result = None
    if validate:
        if verbose:
            print("Running pre-flight validation...")
        
        from validators.pre_flight import validate_conversion
        validation_result = validate_conversion(pbi_report)
        
        if verbose:
            print(f"  Validation: {'PASSED' if validation_result.is_valid else 'FAILED'}")
            print(f"  Errors: {validation_result.errors}, Warnings: {validation_result.warnings}")
            
            # Show critical issues
            critical_issues = [i for i in validation_result.issues if i.severity.value == 'error']
            for issue in critical_issues[:3]:
                print(f"    - {issue.message}")
            if len(critical_issues) > 3:
                print(f"    ... and {len(critical_issues) - 3} more errors")
        
        if not validation_result.is_valid and fail_on_validation_errors:
            error_msgs = [i.message for i in validation_result.issues if i.severity.value == 'error']
            raise ValueError(f"Validation failed: {'; '.join(error_msgs[:3])}")
    
    # Build table definitions for Push Dataset API
    tables = []
    all_measures = []
    
    for table in pbi_report.tables:
        columns = []
        for col in table.columns:
            # Map data type to Push Dataset format
            data_type_str = col.data_type.value if hasattr(col.data_type, 'value') else str(col.data_type)
            pbi_type = {
                'string': 'String',
                'int64': 'Int64',
                'double': 'Double',
                'boolean': 'Boolean',
                'datetime': 'DateTime',
                'dateTime': 'DateTime',
            }.get(data_type_str.lower(), 'String')
            
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
        
        # Collect measures for reference
        for measure in table.measures:
            all_measures.append({
                "name": measure.name,
                "expression": measure.expression,
                "table": table.name,
                "description": measure.description,
                "displayFolder": measure.display_folder,
            })
    
    # Ensure at least one table
    if not tables:
        tables.append({
            "name": "Data",
            "columns": [{"name": "ID", "dataType": "Int64"}]
        })
    
    # Create Power BI client and authenticate
    if verbose:
        print("Authenticating with Power BI Service...")
    
    client = PowerBIRestClient(config)
    
    if config.client_secret:
        client.authenticate_service_principal()
    else:
        client.authenticate_device_code()
    
    # Create the dataset
    name = dataset_name or Path(tableau_path).stem
    
    if verbose:
        print(f"Creating dataset: {name}")
    
    dataset = client.create_push_dataset(name, tables)
    dataset_id = dataset.get('id')
    
    if verbose:
        print(f"  Dataset ID: {dataset_id}")
        print(f"  Tables: {len(tables)}")
    
    # Build report structure if requested
    report_builder = None
    report_instructions = None
    
    if create_report_structure:
        if verbose:
            print("Building report structure...")
        
        report_builder = PowerBIReportBuilder(name, dataset_id)
        
        for page in pbi_report.pages:
            report_builder.add_page(
                name=page.name,
                display_name=page.display_name or page.name,
                width=page.width,
                height=page.height
            )
            
            for visual in page.visuals:
                # Get field names for bindings
                category_fields = [f"{f.table}.{f.column}" for f in visual.category_fields] if visual.category_fields else []
                value_fields = [f"{f.table}.{f.column}" for f in visual.value_fields] if visual.value_fields else []
                legend_field = f"{visual.legend_field.table}.{visual.legend_field.column}" if visual.legend_field else None
                
                visual_type_str = visual.visual_type.value if hasattr(visual.visual_type, 'value') else str(visual.visual_type)
                
                report_builder.add_visual(
                    page_name=page.name,
                    visual_type=visual_type_str,
                    title=visual.title or visual.name or "Visual",
                    x=int(visual.x),
                    y=int(visual.y),
                    width=int(visual.width),
                    height=int(visual.height),
                    category_fields=category_fields,
                    value_fields=value_fields,
                    legend_field=legend_field
                )
        
        report_instructions = report_builder.to_instructions()
    
    # Get URLs
    dataset_url = client.get_dataset_url(dataset_id)
    workspace_url = client.get_workspace_url()
    
    if verbose:
        print(f"\nDataset created successfully!")
        print(f"  Name: {name}")
        print(f"  ID: {dataset_id}")
        print(f"  Tables: {len(tables)}")
        print(f"  Measures: {len(all_measures)}")
        print(f"  Pages: {len(pbi_report.pages)}")
        print(f"\n  Dataset URL: {dataset_url}")
        print(f"  Workspace URL: {workspace_url}")
    
    result = {
        "dataset": dataset,
        "dataset_id": dataset_id,
        "dataset_url": dataset_url,
        "workspace_url": workspace_url,
        "tables": tables,
        "measures": all_measures,
        "report_structure": report_builder.build() if report_builder else None,
        "report_instructions": report_instructions,
        "translation_stats": pbi_report.translation_stats,
        "validation": validation_result.to_dict() if validation_result else None,
        "source": tableau_path,
    }
    
    return result


def save_conversion_output(result: Dict, output_dir: str) -> Dict[str, str]:
    """
    Save conversion output files for reference.
    
    Args:
        result: Result from convert_tableau_to_powerbi_api
        output_dir: Directory to save files
        
    Returns:
        Dictionary of file paths
    """
    import os
    from pathlib import Path
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    files = {}
    
    # Save dataset schema
    dataset_file = output_path / "dataset_schema.json"
    with open(dataset_file, 'w') as f:
        json.dump({
            "dataset_id": result.get("dataset_id"),
            "tables": result.get("tables", []),
        }, f, indent=2)
    files["dataset_schema"] = str(dataset_file)
    
    # Save measures
    measures_file = output_path / "dax_measures.json"
    with open(measures_file, 'w') as f:
        json.dump(result.get("measures", []), f, indent=2)
    files["measures"] = str(measures_file)
    
    # Save DAX measures as text for easy copy-paste
    dax_file = output_path / "dax_measures.txt"
    with open(dax_file, 'w') as f:
        f.write("// DAX Measures for Power BI\n")
        f.write(f"// Source: {result.get('source', 'Unknown')}\n")
        f.write(f"// Dataset ID: {result.get('dataset_id', 'Unknown')}\n\n")
        
        for measure in result.get("measures", []):
            f.write(f"// Table: {measure.get('table', 'Unknown')}\n")
            if measure.get('displayFolder'):
                f.write(f"// Folder: {measure['displayFolder']}\n")
            f.write(f"{measure['name']} = \n")
            f.write(f"    {measure['expression']}\n\n")
    files["dax_text"] = str(dax_file)
    
    # Save report structure
    if result.get("report_structure"):
        report_file = output_path / "report_structure.json"
        with open(report_file, 'w') as f:
            json.dump(result["report_structure"], f, indent=2)
        files["report_structure"] = str(report_file)
    
    # Save instructions
    if result.get("report_instructions"):
        instructions_file = output_path / "report_instructions.md"
        with open(instructions_file, 'w') as f:
            f.write(result["report_instructions"])
        files["instructions"] = str(instructions_file)
    
    # Save validation report
    if result.get("validation"):
        validation = result["validation"]
        
        # JSON format
        validation_file = output_path / "validation_report.json"
        with open(validation_file, 'w') as f:
            json.dump(validation, f, indent=2)
        files["validation_json"] = str(validation_file)
        
        # Markdown format
        validation_md = output_path / "validation_report.md"
        with open(validation_md, 'w') as f:
            f.write("# Pre-flight Validation Report\n\n")
            f.write(f"**Status:** {'PASSED' if validation['is_valid'] else 'FAILED'}\n")
            f.write(f"**Errors:** {validation['errors']}\n")
            f.write(f"**Warnings:** {validation['warnings']}\n\n")
            
            if validation.get('issues'):
                f.write("## Issues\n\n")
                for issue in validation['issues']:
                    severity_icon = {'error': 'X', 'warning': '!', 'info': 'i'}
                    icon = severity_icon.get(issue['severity'], '?')
                    f.write(f"### [{icon}] {issue['category']}\n")
                    f.write(f"- **Severity:** {issue['severity']}\n")
                    f.write(f"- **Component:** {issue['component']}\n")
                    f.write(f"- **Message:** {issue['message']}\n")
                    if issue.get('details'):
                        f.write(f"- **Details:** {issue['details']}\n")
                    if issue.get('suggestion'):
                        f.write(f"- **Suggestion:** {issue['suggestion']}\n")
                    f.write("\n")
        files["validation_md"] = str(validation_md)
    
    # Save summary
    summary_file = output_path / "conversion_summary.md"
    with open(summary_file, 'w') as f:
        f.write(f"# Tableau to Power BI Conversion Summary\n\n")
        f.write(f"**Source:** {result.get('source', 'Unknown')}\n\n")
        f.write(f"**Dataset ID:** `{result.get('dataset_id', 'Unknown')}`\n\n")
        f.write(f"**Dataset URL:** [{result.get('dataset_url')}]({result.get('dataset_url')})\n\n")
        f.write(f"## Statistics\n\n")
        f.write(f"- Tables: {len(result.get('tables', []))}\n")
        f.write(f"- Measures: {len(result.get('measures', []))}\n")
        
        stats = result.get("translation_stats", {})
        if stats:
            f.write(f"- Success Rate: {stats.get('success_rate', 'N/A')}%\n")
            f.write(f"- High Confidence: {stats.get('high_confidence', 0)}\n")
            f.write(f"- Requires Review: {stats.get('requires_review', 0)}\n")
        
        f.write(f"\n## Next Steps\n\n")
        f.write(f"1. Open Power BI Service: {result.get('workspace_url')}\n")
        f.write(f"2. Find the dataset and create a new report\n")
        f.write(f"3. Add measures from `dax_measures.txt`\n")
        f.write(f"4. Create visuals as described in `report_instructions.md`\n")
    files["summary"] = str(summary_file)
    
    return files


# CLI integration
if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Power BI REST API - Tableau Converter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python powerbi_rest_api.py samples/sample_superstore.twbx
  python powerbi_rest_api.py sample.twbx -o output/ --name "My Report"
  
Required environment variables:
  AZURE_TENANT_ID      - Your Azure AD tenant ID
  AZURE_CLIENT_ID      - Your Azure AD app client ID
  AZURE_CLIENT_SECRET  - (Optional) For service principal auth
  POWERBI_WORKSPACE_ID - (Optional) Target workspace
        """
    )
    
    parser.add_argument("tableau_file", help="Path to Tableau workbook (.twbx or .twb)")
    parser.add_argument("-o", "--output", help="Output directory for reference files")
    parser.add_argument("-n", "--name", help="Dataset name (default: filename)")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress progress output")
    
    args = parser.parse_args()
    
    print("Power BI REST API - Tableau Converter")
    print("="*50)
    
    # Check for required environment variables
    required_vars = ['AZURE_TENANT_ID', 'AZURE_CLIENT_ID']
    missing = [v for v in required_vars if not os.environ.get(v)]
    
    if missing:
        print("\nRequired environment variables:")
        print("  AZURE_TENANT_ID      - Your Azure AD tenant ID")
        print("  AZURE_CLIENT_ID      - Your Azure AD app client ID")
        print("  AZURE_CLIENT_SECRET  - (Optional) For service principal auth")
        print("  POWERBI_WORKSPACE_ID - (Optional) Target workspace")
        print(f"\nMissing: {', '.join(missing)}")
        sys.exit(1)
    
    config = PowerBIConfig.from_env()
    
    try:
        result = convert_tableau_to_powerbi_api(
            args.tableau_file, 
            config,
            dataset_name=args.name,
            verbose=not args.quiet
        )
        
        # Save output files if requested
        if args.output:
            print(f"\nSaving reference files to: {args.output}")
            files = save_conversion_output(result, args.output)
            for name, path in files.items():
                print(f"  {name}: {path}")
        
        print("\n" + "="*50)
        print("CONVERSION COMPLETE!")
        print("="*50)
        print(f"\nDataset URL: {result['dataset_url']}")
        print(f"Workspace: {result['workspace_url']}")
        print("\nNEXT STEPS:")
        print("1. Open the dataset URL in your browser")
        print("2. Click 'Create a report' to build visualizations")
        print("3. Add the DAX measures from the output files")
        print("="*50)
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
