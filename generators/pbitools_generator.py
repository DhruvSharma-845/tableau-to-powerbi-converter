"""
pbi-tools compatible format generator.

Generates Power BI project files in the format expected by pbi-tools,
which can then compile them to PBIX.

pbi-tools PbixProj Format Structure:
MyReport/
├── Version.txt              (required - Power BI version string)
├── [Content_Types].xml      (required - content types)
├── Report/
│   └── Layout               (JSON - report layout)
├── DataMashup               (optional - M queries binary)
├── DiagramLayout            (optional)
└── Settings                 (optional)

For thin reports (report-only, no embedded data):
- Only Report/Layout is required
- Compiles to PBIX that connects to external data sources

For PBIT (templates with model):
- DataModel file is required
- Compiles to PBIT file
"""

import json
import uuid
import base64
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from models.powerbi_models import (
    PowerBIReport, PowerBIPage, PowerBIVisual, PowerBIMeasure,
    PowerBITable, PowerBIDataSource, PowerBIRelationship, PowerBIVisualType
)


class PbiToolsGenerator:
    """
    Generates Power BI reports in pbi-tools compatible format.
    """
    
    # Power BI Desktop version to use (required for compilation)
    PBI_VERSION = "2.133.866.0"
    
    def __init__(self, output_dir: str):
        """
        Initialize the generator.
        
        Args:
            output_dir: Directory to write output files
        """
        self.output_dir = Path(output_dir)
    
    def generate(self, report: PowerBIReport) -> Path:
        """
        Generate a pbi-tools compatible project folder.
        
        Args:
            report: Power BI report model to generate
            
        Returns:
            Path to the generated project directory
        """
        # Create project directory
        project_name = self._sanitize_name(report.name)
        project_dir = self.output_dir / f"{project_name}.pbixproj"
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate required files
        self._generate_version(project_dir)
        self._generate_content_types(project_dir)
        self._generate_report_layout(project_dir, report)
        self._generate_settings(project_dir)
        
        # Generate optional files if we have data
        if report.tables or report.data_sources:
            self._generate_connections(project_dir, report)
        
        return project_dir
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize name for file system use."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name.strip()
    
    def _generate_version(self, project_dir: Path) -> None:
        """Generate Version.txt file (required by pbi-tools)."""
        with open(project_dir / "Version.txt", 'w', encoding='utf-8') as f:
            f.write(self.PBI_VERSION)
    
    def _generate_content_types(self, project_dir: Path) -> None:
        """Generate [Content_Types].xml file."""
        content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="application/json"/>
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Override PartName="/Version.txt" ContentType="text/plain"/>
  <Override PartName="/Report/Layout" ContentType="application/json"/>
  <Override PartName="/Settings" ContentType="application/json"/>
  <Override PartName="/Connections" ContentType="application/json"/>
</Types>"""
        with open(project_dir / "[Content_Types].xml", 'w', encoding='utf-8') as f:
            f.write(content_types)
    
    def _generate_report_layout(self, project_dir: Path, report: PowerBIReport) -> None:
        """Generate Report/Layout file (the main report definition)."""
        report_dir = project_dir / "Report"
        report_dir.mkdir(exist_ok=True)
        
        # Build sections (pages)
        sections = []
        for i, page in enumerate(report.pages):
            section = {
                "id": i,
                "name": page.name,
                "displayName": page.display_name or page.name,
                "displayOption": 1,  # FitToPage
                "width": page.width,
                "height": page.height,
                "visualContainers": []
            }
            
            # Add visuals
            for visual in page.visuals:
                visual_container = self._build_visual_container(visual)
                section["visualContainers"].append(visual_container)
            
            sections.append(section)
        
        # Build config
        config = {
            "version": "5.50",
            "themeCollection": {
                "baseTheme": {
                    "name": "CY24SU06",
                    "version": "5.050",
                    "type": 2
                }
            },
            "activeSectionIndex": 0,
            "defaultDrillFilterOtherVisuals": True,
            "slowDataSourceSettings": {
                "isCrossHighlightingDisabled": True,
                "isSlicerSelectionsButtonEnabled": True,
                "isFilterSelectionsButtonEnabled": True,
                "isFieldWellButtonEnabled": True,
                "isApplyAllButtonEnabled": True
            },
            "linguisticSchemaSyncVersion": 2,
            "settings": {
                "useDefaultAggregateDisplayName": True
            }
        }
        
        # Build layout
        layout = {
            "id": 0,
            "reportId": report.id,
            "sections": sections,
            "config": json.dumps(config),
            "layoutOptimization": 0,
            "resourcePackages": [],
            "publicCustomVisuals": []
        }
        
        with open(report_dir / "Layout", 'w', encoding='utf-8') as f:
            json.dump(layout, f, indent=2)
    
    def _build_visual_container(self, visual: PowerBIVisual) -> Dict[str, Any]:
        """Build a visual container for the layout."""
        # Map our visual types to Power BI visual types
        visual_type_map = {
            PowerBIVisualType.CLUSTERED_BAR: "clusteredBarChart",
            PowerBIVisualType.CLUSTERED_COLUMN: "clusteredColumnChart",
            PowerBIVisualType.STACKED_BAR: "stackedBarChart",
            PowerBIVisualType.STACKED_COLUMN: "stackedColumnChart",
            PowerBIVisualType.LINE_CHART: "lineChart",
            PowerBIVisualType.AREA_CHART: "areaChart",
            PowerBIVisualType.PIE_CHART: "pieChart",
            PowerBIVisualType.DONUT_CHART: "donutChart",
            PowerBIVisualType.SCATTER_CHART: "scatterChart",
            PowerBIVisualType.MAP: "map",
            PowerBIVisualType.FILLED_MAP: "filledMap",
            PowerBIVisualType.TREEMAP: "treemap",
            PowerBIVisualType.TABLE: "tableEx",
            PowerBIVisualType.MATRIX: "pivotTable",
            PowerBIVisualType.CARD: "card",
            PowerBIVisualType.MULTI_ROW_CARD: "multiRowCard",
            PowerBIVisualType.KPI: "kpi",
            PowerBIVisualType.GAUGE: "gauge",
            PowerBIVisualType.SLICER: "slicer",
            PowerBIVisualType.TEXT_BOX: "textbox",
            PowerBIVisualType.IMAGE: "image",
            PowerBIVisualType.SHAPE: "shape",
            PowerBIVisualType.COMBO_CHART: "lineClusteredColumnComboChart",
        }
        
        pbi_visual_type = visual_type_map.get(visual.visual_type, "clusteredColumnChart")
        
        # Build visual config
        visual_config = {
            "name": visual.id,
            "layouts": [{
                "id": 0,
                "position": {
                    "x": visual.x,
                    "y": visual.y,
                    "z": visual.z,
                    "width": visual.width,
                    "height": visual.height,
                    "tabOrder": visual.z
                }
            }],
            "singleVisual": {
                "visualType": pbi_visual_type,
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
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                        "text": {"expr": {"Literal": {"Value": f"'{visual.title}'"}}}
                    }
                }]
            }
        
        container = {
            "x": visual.x,
            "y": visual.y,
            "z": visual.z,
            "width": visual.width,
            "height": visual.height,
            "config": json.dumps(visual_config),
            "filters": json.dumps(visual.filters) if visual.filters else "[]",
            "tabOrder": visual.z
        }
        
        return container
    
    def _build_projections(self, visual: PowerBIVisual) -> Dict[str, Any]:
        """Build projections (data bindings) for a visual."""
        projections = {}
        
        if visual.category_fields:
            projections["Category"] = [
                {"queryRef": f"{f.table}.{f.column}"}
                for f in visual.category_fields
            ]
        
        if visual.value_fields:
            agg_map = {
                "sum": "Sum",
                "average": "Avg",
                "count": "Count",
                "distinctcount": "CountD",
                "min": "Min",
                "max": "Max",
            }
            projections["Y"] = [
                {"queryRef": f"{agg_map.get(f.aggregation, 'Sum')}({f.table}.{f.column})"}
                for f in visual.value_fields
            ]
        
        if visual.legend_field:
            projections["Series"] = [
                {"queryRef": f"{visual.legend_field.table}.{visual.legend_field.column}"}
            ]
        
        return projections
    
    def _build_prototype_query(self, visual: PowerBIVisual) -> Dict[str, Any]:
        """Build the prototype query for a visual."""
        selects = []
        
        # Category fields
        for f in visual.category_fields:
            selects.append({
                "Column": {
                    "Expression": {"SourceRef": {"Source": "d"}},
                    "Property": f.column
                },
                "Name": f"{f.table}.{f.column}"
            })
        
        # Value fields with aggregation
        agg_function_map = {
            "sum": 0, "average": 1, "min": 3, "max": 4, 
            "count": 5, "distinctcount": 6
        }
        
        for f in visual.value_fields:
            agg = f.aggregation or "sum"
            selects.append({
                "Aggregation": {
                    "Expression": {
                        "Column": {
                            "Expression": {"SourceRef": {"Source": "d"}},
                            "Property": f.column
                        }
                    },
                    "Function": agg_function_map.get(agg.lower(), 0)
                },
                "Name": f"{agg}({f.table}.{f.column})"
            })
        
        # Legend field
        if visual.legend_field:
            selects.append({
                "Column": {
                    "Expression": {"SourceRef": {"Source": "d"}},
                    "Property": visual.legend_field.column
                },
                "Name": f"{visual.legend_field.table}.{visual.legend_field.column}"
            })
        
        return {
            "Version": 2,
            "From": [{"Name": "d", "Entity": "Data", "Type": 0}],
            "Select": selects
        }
    
    def _generate_settings(self, project_dir: Path) -> None:
        """Generate Settings file."""
        settings = {
            "Version": 3,
            "Settings": {
                "UseStale": True,
                "QnAEnabled": True
            }
        }
        with open(project_dir / "Settings", 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
    
    def _generate_connections(self, project_dir: Path, report: PowerBIReport) -> None:
        """Generate Connections file for data sources."""
        connections = {
            "Version": 1,
            "Connections": []
        }
        
        for ds in report.data_sources:
            conn = {
                "Name": ds.name,
                "ConnectionString": ds.connection_string or "",
                "ConnectionType": ds.connection_type or "Unknown"
            }
            connections["Connections"].append(conn)
        
        with open(project_dir / "Connections", 'w', encoding='utf-8') as f:
            json.dump(connections, f, indent=2)
