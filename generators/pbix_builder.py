"""
PBIX Builder - Creates a valid PBIX file directly.

A PBIX file is essentially a ZIP archive with a specific structure.
This module creates a minimal valid PBIX that can be opened in Power BI Desktop.

Note: Power BI Service has strict validation requirements. This builder creates
"thin" reports (report-only, no embedded data) which are more likely to be accepted.
"""
import json
import zipfile
import base64
import uuid
from pathlib import Path
from datetime import datetime

from models.powerbi_models import PowerBIReport


class PBIXBuilder:
    """
    Builds a PBIX file directly as a ZIP archive.
    
    PBIX file structure for thin reports:
    - [Content_Types].xml
    - SecurityBindings
    - Settings
    - Version
    - Report/Layout
    - Report/LinguisticSchema  
    - DiagramLayout
    - Metadata
    - DataMashup (required for Power BI Service)
    """
    
    PBIX_VERSION = "2.0.0.0"
    PAGE_WIDTH = 1280
    PAGE_HEIGHT = 720
    
    def __init__(self):
        self.report_id = str(uuid.uuid4())
        
    def build(self, report: PowerBIReport, output_path: str, include_model: bool = False) -> str:
        """Build a PBIX file from a PowerBIReport model."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as pbix:
            # Core required files
            pbix.writestr('[Content_Types].xml', self._generate_content_types())
            pbix.writestr('Version', self.PBIX_VERSION)
            pbix.writestr('Settings', self._generate_settings())
            pbix.writestr('SecurityBindings', '')
            pbix.writestr('Metadata', self._generate_metadata(report))
            pbix.writestr('DiagramLayout', self._generate_diagram_layout())
            
            # Report layout with normalized coordinates
            layout = self._generate_layout(report)
            pbix.writestr('Report/Layout', json.dumps(layout, ensure_ascii=False))
            
            # Linguistic schema
            pbix.writestr('Report/LinguisticSchema', self._generate_linguistic_schema())
            
            # DataMashup - minimal but required for Power BI Service
            pbix.writestr('DataMashup', self._generate_data_mashup())
            
            # Connections
            pbix.writestr('Connections', self._generate_connections(report))
            
            # Only include model if requested and tables exist
            if include_model and report.tables:
                pbix.writestr('DataModelSchema', self._generate_data_model_schema(report))
        
        return str(output_path)
    
    def _generate_content_types(self) -> str:
        """Generate [Content_Types].xml for the PBIX."""
        return '''<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="application/json" />
  <Default Extension="xml" ContentType="application/xml" />
  <Override PartName="/DataMashup" ContentType="application/vnd.ms-package.datamashup" />
  <Override PartName="/Metadata" ContentType="application/json" />
  <Override PartName="/Settings" ContentType="application/json" />
  <Override PartName="/Version" ContentType="text/plain" />
  <Override PartName="/Report/Layout" ContentType="application/json" />
  <Override PartName="/Report/LinguisticSchema" ContentType="application/json" />
  <Override PartName="/DiagramLayout" ContentType="application/json" />
  <Override PartName="/Connections" ContentType="application/json" />
</Types>'''
    
    def _generate_settings(self) -> str:
        """Generate Settings file."""
        settings = {
            "Version": 3,
            "ReportSettings": {
                "persistentFilters": {"enabled": False}
            }
        }
        return json.dumps(settings, ensure_ascii=False)
    
    def _generate_metadata(self, report: PowerBIReport) -> str:
        """Generate Metadata file."""
        metadata = {
            "version": "1.0",
            "createdFrom": "PBIX Converter",
            "createdDate": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        }
        return json.dumps(metadata, ensure_ascii=False)
    
    def _generate_diagram_layout(self) -> str:
        """Generate DiagramLayout file."""
        diagram = {
            "version": "1.0",
            "diagrams": []
        }
        return json.dumps(diagram, ensure_ascii=False)
    
    def _generate_data_mashup(self) -> bytes:
        """
        Generate a minimal DataMashup.
        
        DataMashup is a ZIP file containing M queries. For thin reports,
        we create a minimal empty mashup.
        """
        import io
        
        mashup_buffer = io.BytesIO()
        with zipfile.ZipFile(mashup_buffer, 'w', zipfile.ZIP_DEFLATED) as mashup:
            # Config
            config = '''<Config xmlns="http://schemas.datacontract.org/2004/07/Microsoft.Data.Mashup">
  <ConfigElement Name="CurrentCulture">en-US</ConfigElement>
  <ConfigElement Name="FastCombine">true</ConfigElement>
</Config>'''
            mashup.writestr('Config/Config.xml', config)
            
            # Content types for mashup
            content_types = '''<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Override PartName="/Config/Config.xml" ContentType="text/xml" />
  <Override PartName="/Formulas/Section1.m" ContentType="text/x-m" />
  <Override PartName="/Formulas/Mashup.qry" ContentType="application/octet-stream" />
</Types>'''
            mashup.writestr('[Content_Types].xml', content_types)
            
            # Empty M section
            section_m = 'section Section1;\n'
            mashup.writestr('Formulas/Section1.m', section_m)
            
            # Empty binary mashup query
            mashup.writestr('Formulas/Mashup.qry', b'')
            
        return mashup_buffer.getvalue()
    
    def _normalize_coordinate(self, value: float, max_tableau: float = 100000, max_pbi: float = 1280) -> float:
        """Normalize Tableau coordinates to Power BI scale."""
        if value > max_pbi * 2:  # Likely Tableau coordinates
            return min(max_pbi - 50, max(0, (value / max_tableau) * max_pbi))
        return value
    
    def _generate_layout(self, report: PowerBIReport) -> dict:
        """Generate the Report/Layout JSON structure with normalized coordinates."""
        sections = []
        
        for idx, page in enumerate(report.pages):
            page_id = str(uuid.uuid4()).replace('-', '')
            page_name = page.name or f"Page{idx + 1}"
            
            # Build visual containers with normalized positions
            visual_containers = []
            
            # Calculate grid layout for visuals
            num_visuals = len(page.visuals)
            cols = min(3, num_visuals) if num_visuals > 0 else 1
            
            for v_idx, visual in enumerate(page.visuals):
                visual_id = str(uuid.uuid4()).replace('-', '')
                
                # Get raw coordinates
                raw_x = getattr(visual, 'x', 0)
                raw_y = getattr(visual, 'y', 0)
                raw_width = getattr(visual, 'width', 300)
                raw_height = getattr(visual, 'height', 200)
                
                # Normalize or use grid layout if coordinates are in Tableau scale
                if raw_x > self.PAGE_WIDTH or raw_y > self.PAGE_HEIGHT:
                    # Use grid layout instead
                    col = v_idx % cols
                    row = v_idx // cols
                    vis_width = (self.PAGE_WIDTH - 40) // cols - 10
                    vis_height = 200
                    vis_x = 20 + col * (vis_width + 10)
                    vis_y = 20 + row * (vis_height + 10)
                else:
                    vis_x = raw_x
                    vis_y = raw_y
                    vis_width = min(raw_width, self.PAGE_WIDTH - 20)
                    vis_height = min(raw_height, self.PAGE_HEIGHT - 20)
                
                vis_z = v_idx * 1000
                
                # Get visual type string
                vis_type = visual.visual_type
                if hasattr(vis_type, 'value'):
                    vis_type = vis_type.value
                
                # Map to valid Power BI visual type
                vis_type = self._validate_visual_type(vis_type)
                
                # Build visual configuration
                visual_config = {
                    "name": visual_id,
                    "layouts": [{
                        "id": 0,
                        "position": {
                            "x": vis_x,
                            "y": vis_y,
                            "z": vis_z,
                            "width": vis_width,
                            "height": vis_height,
                            "tabOrder": v_idx * 1000
                        }
                    }],
                    "singleVisual": {
                        "visualType": vis_type,
                        "drillFilterOtherVisuals": True,
                        "objects": {}
                    }
                }
                
                # Add title if present
                title = visual.title or visual.name or f"Visual {v_idx + 1}"
                if title:
                    visual_config["singleVisual"]["objects"]["title"] = [{
                        "properties": {
                            "text": {"expr": {"Literal": {"Value": f"'{title}'"}}},
                            "show": {"expr": {"Literal": {"Value": "true"}}}
                        }
                    }]
                
                visual_containers.append({
                    "x": vis_x,
                    "y": vis_y,
                    "z": vis_z,
                    "width": vis_width,
                    "height": vis_height,
                    "config": json.dumps(visual_config, ensure_ascii=False),
                    "filters": "[]",
                    "tabOrder": v_idx * 1000
                })
            
            section = {
                "id": idx,
                "name": page_id,
                "displayName": page_name,
                "displayOption": 1,  # Fit to page
                "width": self.PAGE_WIDTH,
                "height": self.PAGE_HEIGHT,
                "visualContainers": visual_containers,
                "config": json.dumps({"visibility": 0})
            }
            sections.append(section)
        
        # Create at least one blank page if none exist
        if not sections:
            sections.append({
                "id": 0,
                "name": str(uuid.uuid4()).replace('-', ''),
                "displayName": "Page 1",
                "displayOption": 1,
                "width": self.PAGE_WIDTH,
                "height": self.PAGE_HEIGHT,
                "visualContainers": [],
                "config": json.dumps({"visibility": 0})
            })
        
        report_config = {
            "version": "5.54",
            "themeCollection": {
                "baseTheme": {
                    "name": "CY24SU02",
                    "version": "5.54", 
                    "type": 2
                }
            },
            "activeSectionIndex": 0,
            "defaultDrillFilterOtherVisuals": True,
            "linguisticSchemaSyncVersion": 2,
            "settings": {
                "isPersistentUserStateDisabled": True,
                "useStylableVisualContainerHeader": True
            }
        }
        
        layout = {
            "id": self.report_id,
            "reportId": self.report_id,
            "sections": sections,
            "config": json.dumps(report_config, ensure_ascii=False),
            "layoutOptimization": 0,
            "publicCustomVisuals": [],
            "resourcePackages": []
        }
        
        return layout
    
    def _validate_visual_type(self, vis_type: str) -> str:
        """Ensure visual type is a valid Power BI visual type."""
        valid_types = {
            'barChart', 'clusteredBarChart', 'stackedBarChart',
            'columnChart', 'clusteredColumnChart', 'stackedColumnChart',
            'lineChart', 'areaChart', 'stackedAreaChart', 'comboChart',
            'pieChart', 'donutChart', 'treemap', 'map', 'filledMap',
            'scatterChart', 'tableEx', 'pivotTable', 'card', 'multiRowCard',
            'kpi', 'gauge', 'slicer', 'textbox', 'image', 'shape'
        }
        return vis_type if vis_type in valid_types else 'card'
    
    def _generate_linguistic_schema(self) -> str:
        """Generate linguistic schema for Q&A features."""
        schema = {
            "Version": 1,
            "Language": "en-US",
            "DynamicImprovement": "HighConfidence"
        }
        return json.dumps(schema, ensure_ascii=False)
    
    def _generate_connections(self, report: PowerBIReport) -> str:
        """Generate Connections file for data sources."""
        connections = {
            "Version": 1,
            "Connections": []
        }
        return json.dumps(connections, ensure_ascii=False)
    
    def _generate_data_model_schema(self, report: PowerBIReport) -> str:
        """Generate DataModelSchema (TOM model as JSON)."""
        if not report.tables:
            return "{}"
        
        tables = []
        for table in report.tables:
            columns = []
            for col in table.columns:
                columns.append({
                    "name": col.name,
                    "dataType": self._map_data_type(col.data_type),
                    "sourceColumn": col.name,
                    "isHidden": col.is_hidden
                })
            
            measures = []
            for measure in table.measures:
                measures.append({
                    "name": measure.name,
                    "expression": measure.expression or "0",
                    "isHidden": measure.is_hidden
                })
            
            table_def = {
                "name": table.name,
                "columns": columns,
                "measures": measures,
                "partitions": [{
                    "name": f"{table.name}-Partition",
                    "mode": "import",
                    "source": {
                        "type": "m",
                        "expression": [f'let Source = #table({{"Column1"}}, {{}}) in Source']
                    }
                }]
            }
            tables.append(table_def)
        
        schema = {
            "name": report.name or "SemanticModel",
            "compatibilityLevel": 1567,
            "model": {
                "culture": "en-US",
                "dataAccessOptions": {"legacyRedirects": True, "returnErrorValuesAsNull": True},
                "tables": tables,
                "relationships": [],
                "annotations": []
            }
        }
        
        return json.dumps(schema, ensure_ascii=False, indent=2)
    
    def _map_data_type(self, tableau_type: str) -> str:
        """Map Tableau data type to Power BI data type."""
        type_map = {
            'string': 'string',
            'integer': 'int64',
            'real': 'double',
            'boolean': 'boolean',
            'datetime': 'dateTime',
            'date': 'dateTime'
        }
        return type_map.get(tableau_type.lower(), 'string')


def create_pbix(report: PowerBIReport, output_path: str, include_model: bool = False) -> str:
    """
    Create a PBIX file from a PowerBIReport.
    
    Args:
        report: The Power BI report model
        output_path: Path for the output PBIX file
        include_model: Whether to include the data model (default False for thin reports)
        
    Returns:
        Path to the created PBIX file
    """
    builder = PBIXBuilder()
    return builder.build(report, output_path, include_model)
