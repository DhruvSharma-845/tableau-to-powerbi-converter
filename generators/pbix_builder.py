"""
PBIX Builder - Creates a valid PBIX file directly.

A PBIX file is essentially a ZIP archive with a specific structure.
This module creates a minimal valid PBIX that can be opened in Power BI Desktop.
"""
import json
import zipfile
import io
import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime

from models.powerbi_models import PowerBIReport


class PBIXBuilder:
    """
    Builds a PBIX file directly as a ZIP archive.
    
    PBIX file structure:
    - [Content_Types].xml
    - SecurityBindings
    - Settings
    - Version
    - Report/Layout
    - Report/LinguisticSchema
    - DataModelSchema (optional, for models with data)
    - DiagramLayout
    - Metadata
    """
    
    PBIX_VERSION = "2.0.0.0"
    
    def __init__(self):
        self.report_id = str(uuid.uuid4())
        
    def build(self, report: PowerBIReport, output_path: str) -> str:
        """Build a PBIX file from a PowerBIReport model."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as pbix:
            # Core files
            pbix.writestr('[Content_Types].xml', self._generate_content_types())
            pbix.writestr('Version', self.PBIX_VERSION)
            pbix.writestr('Settings', self._generate_settings())
            pbix.writestr('SecurityBindings', '')
            pbix.writestr('Metadata', self._generate_metadata(report))
            pbix.writestr('DiagramLayout', self._generate_diagram_layout())
            
            # Report layout
            layout = self._generate_layout(report)
            pbix.writestr('Report/Layout', json.dumps(layout, ensure_ascii=False))
            
            # Linguistic schema (required for Q&A features)
            pbix.writestr('Report/LinguisticSchema', self._generate_linguistic_schema())
            
            # Connections (if any data sources)
            if report.tables:
                pbix.writestr('Connections', self._generate_connections(report))
                pbix.writestr('DataModelSchema', self._generate_data_model_schema(report))
        
        return str(output_path)
    
    def _generate_content_types(self) -> str:
        """Generate [Content_Types].xml for the PBIX."""
        return '''<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="application/json" />
  <Default Extension="xml" ContentType="application/xml" />
</Types>'''
    
    def _generate_settings(self) -> str:
        """Generate Settings file."""
        settings = {
            "Version": 3,
            "Settings": []
        }
        return json.dumps(settings, ensure_ascii=False)
    
    def _generate_metadata(self, report: PowerBIReport) -> str:
        """Generate Metadata file."""
        metadata = {
            "version": "1.0",
            "createdFrom": "Tableau to Power BI Converter",
            "createdDate": datetime.utcnow().isoformat() + "Z"
        }
        return json.dumps(metadata, ensure_ascii=False)
    
    def _generate_diagram_layout(self) -> str:
        """Generate DiagramLayout file."""
        diagram = {
            "version": "1.0",
            "diagrams": []
        }
        return json.dumps(diagram, ensure_ascii=False)
    
    def _generate_layout(self, report: PowerBIReport) -> dict:
        """Generate the Report/Layout JSON structure."""
        # Build pages (sections)
        sections = []
        
        for idx, page in enumerate(report.pages):
            page_id = page.name or str(uuid.uuid4())
            
            # Build visual containers
            visual_containers = []
            for v_idx, visual in enumerate(page.visuals):
                visual_id = visual.id or str(uuid.uuid4())
                
                # Get position/size from visual attributes
                vis_x = getattr(visual, 'x', v_idx * 320)
                vis_y = getattr(visual, 'y', 0)
                vis_z = getattr(visual, 'z', v_idx * 1000)
                vis_width = getattr(visual, 'width', 300)
                vis_height = getattr(visual, 'height', 200)
                
                # Get visual type string
                vis_type = visual.visual_type
                if hasattr(vis_type, 'value'):
                    vis_type = vis_type.value
                
                # Create visual config
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
                        "projections": self._build_projections(visual),
                        "prototypeQuery": self._build_prototype_query(visual),
                        "drillFilterOtherVisuals": True
                    }
                }
                
                # Add title if present
                if visual.title:
                    visual_config["singleVisual"]["vcObjects"] = {
                        "title": [{
                            "properties": {
                                "text": {"expr": {"Literal": {"Value": f"'{visual.title}'"}}},
                                "show": {"expr": {"Literal": {"Value": "true"}}}
                            }
                        }]
                    }
                
                visual_containers.append({
                    "x": vis_x,
                    "y": vis_y,
                    "z": vis_z,
                    "width": vis_width,
                    "height": vis_height,
                    "config": json.dumps(visual_config),
                    "filters": json.dumps([]),
                    "tabOrder": v_idx * 1000
                })
            
            section = {
                "id": idx,
                "name": page_id,
                "displayName": page.name or f"Page {idx + 1}",
                "displayOption": 1,
                "width": 1280,
                "height": 720,
                "visualContainers": visual_containers
            }
            sections.append(section)
        
        # If no pages, create a blank page
        if not sections:
            sections.append({
                "id": 0,
                "name": str(uuid.uuid4()),
                "displayName": "Page 1",
                "displayOption": 1,
                "width": 1280,
                "height": 720,
                "visualContainers": []
            })
        
        layout = {
            "id": self.report_id,
            "reportId": self.report_id,
            "sections": sections,
            "config": json.dumps({
                "version": "5.54",
                "themeCollection": {"baseTheme": {"name": "CY24SU02", "version": "5.54", "type": 2}},
                "activeSectionIndex": 0,
                "defaultDrillFilterOtherVisuals": True,
                "linguisticSchemaSyncVersion": 2,
                "settings": {"isPersistentUserStateDisabled": True}
            }),
            "layoutOptimization": 0,
            "publicCustomVisuals": [],
            "resourcePackages": []
        }
        
        return layout
    
    def _build_projections(self, visual) -> dict:
        """Build projections (field mappings) for a visual."""
        projections = {}
        
        # Map category fields
        if hasattr(visual, 'category_fields') and visual.category_fields:
            projections["Category"] = []
            for field in visual.category_fields:
                name = field.name if hasattr(field, 'name') else str(field)
                projections["Category"].append({"queryRef": name})
        
        # Map value fields
        if hasattr(visual, 'value_fields') and visual.value_fields:
            projections["Values"] = []
            for field in visual.value_fields:
                name = field.name if hasattr(field, 'name') else str(field)
                projections["Values"].append({"queryRef": name})
        
        # Map legend field
        if hasattr(visual, 'legend_field') and visual.legend_field:
            name = visual.legend_field.name if hasattr(visual.legend_field, 'name') else str(visual.legend_field)
            projections["Legend"] = [{"queryRef": name}]
        
        return projections if projections else {"Values": []}
    
    def _build_prototype_query(self, visual) -> dict:
        """Build a prototype query for a visual."""
        # Minimal prototype query structure
        return {
            "Version": 2,
            "From": [{"Name": "t", "Entity": "Table", "Type": 0}],
            "Select": [],
            "OrderBy": []
        }
    
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


def create_pbix(report: PowerBIReport, output_path: str) -> str:
    """
    Create a PBIX file from a PowerBIReport.
    
    Args:
        report: The Power BI report model
        output_path: Path for the output PBIX file
        
    Returns:
        Path to the created PBIX file
    """
    builder = PBIXBuilder()
    return builder.build(report, output_path)
