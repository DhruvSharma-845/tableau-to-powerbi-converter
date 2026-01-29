"""
PBIR (Power BI Enhanced Report Format) generator.

Generates Power BI project files in the PBIR format, which stores
report metadata as properly formatted JSON files in a source
control-friendly structure.

PBIR Format Structure:
MyReport.pbip/
├── definition.pbir
├── definition/
│   ├── report.json
│   ├── pages/
│   │   └── page1/
│   │       ├── page.json
│   │       └── visuals/
│   │           └── visual1.json
│   └── bookmarks/
├── MyReport.SemanticModel/
│   └── definition/
│       ├── model.tmdl
│       ├── tables/
│       └── expressions.tmdl
└── .pbi/
    └── localSettings.json
"""

import os
import json
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from models.powerbi_models import (
    PowerBIReport, PowerBIPage, PowerBIVisual, PowerBIMeasure,
    PowerBITable, PowerBIDataSource, PowerBIRelationship
)


class PBIRGenerator:
    """
    Generates Power BI reports in PBIR format.
    """
    
    # PBIR schema version
    SCHEMA_VERSION = "1.0"
    
    # JSON schema references
    SCHEMAS = {
        "report": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.0.0/schema.json",
        "page": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.0.0/schema.json",
        "visual": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visual/1.0.0/schema.json",
        "definition": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition.json",
    }
    
    def __init__(self, output_dir: str):
        """
        Initialize the PBIR generator.
        
        Args:
            output_dir: Directory to write output files
        """
        self.output_dir = Path(output_dir)
        self.report_id = str(uuid.uuid4())
    
    def generate(self, report: PowerBIReport) -> Path:
        """
        Generate a complete PBIR project from a Power BI report model.
        
        Args:
            report: Power BI report model to generate
            
        Returns:
            Path to the generated .pbip directory
        """
        # Create project directory
        project_name = self._sanitize_name(report.name)
        project_dir = self.output_dir / f"{project_name}.pbip"
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Create directory structure
        report_dir = project_dir / f"{project_name}.Report"
        model_dir = project_dir / f"{project_name}.SemanticModel"
        pbi_dir = project_dir / ".pbi"
        
        report_dir.mkdir(exist_ok=True)
        model_dir.mkdir(exist_ok=True)
        pbi_dir.mkdir(exist_ok=True)
        
        # Generate report files
        self._generate_report_definition(report_dir, report)
        self._generate_pages(report_dir, report)
        
        # Generate semantic model files
        self._generate_semantic_model(model_dir, report)
        
        # Generate project metadata
        self._generate_project_metadata(project_dir, project_name)
        self._generate_local_settings(pbi_dir)
        
        return project_dir
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize name for file system use."""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name.strip()
    
    def _generate_report_definition(self, report_dir: Path, report: PowerBIReport) -> None:
        """Generate the main report definition files."""
        definition_dir = report_dir / "definition"
        definition_dir.mkdir(exist_ok=True)
        
        # Generate definition.pbir (the pointer file)
        pbir_content = {
            "version": "1.0",
            "datasetReference": {
                "byPath": {
                    "path": f"../{self._sanitize_name(report.name)}.SemanticModel"
                }
            }
        }
        
        with open(report_dir / "definition.pbir", 'w') as f:
            json.dump(pbir_content, f, indent=2)
        
        # Generate report.json
        report_json = {
            "$schema": self.SCHEMAS["report"],
            "id": report.id,
            "name": report.name,
            "themeCollection": {
                "baseTheme": {
                    "name": "CY24SU02",
                    "version": "5.0.0",
                    "type": "default"
                }
            },
            "layoutOptimization": "horizontal",
            "pages": [
                {
                    "name": page.name,
                    "displayName": page.display_name or page.name
                }
                for page in report.pages
            ],
            "config": {
                "version": "5.59",
                "settings": {
                    "isPersistentUserStateDisabled": False,
                    "hideVisualContainerHeader": False,
                    "useDefaultAggregateDisplayName": True
                }
            },
            "resourcePackages": []
        }
        
        with open(definition_dir / "report.json", 'w') as f:
            json.dump(report_json, f, indent=2)
    
    def _generate_pages(self, report_dir: Path, report: PowerBIReport) -> None:
        """Generate page definition files."""
        pages_dir = report_dir / "definition" / "pages"
        pages_dir.mkdir(exist_ok=True)
        
        for page in report.pages:
            page_dir = pages_dir / page.name
            page_dir.mkdir(exist_ok=True)
            
            # Generate page.json
            page_json = {
                "$schema": self.SCHEMAS["page"],
                "name": page.name,
                "displayName": page.display_name or page.name,
                "displayOption": "FitToPage",
                "width": page.width,
                "height": page.height,
                "config": {
                    "layouts": []
                }
            }
            
            if page.background_color:
                page_json["background"] = {
                    "color": page.background_color
                }
            
            with open(page_dir / "page.json", 'w') as f:
                json.dump(page_json, f, indent=2)
            
            # Generate visual files
            visuals_dir = page_dir / "visuals"
            visuals_dir.mkdir(exist_ok=True)
            
            for visual in page.visuals:
                self._generate_visual(visuals_dir, visual)
    
    def _generate_visual(self, visuals_dir: Path, visual: PowerBIVisual) -> None:
        """Generate a visual definition file."""
        visual_dir = visuals_dir / visual.id
        visual_dir.mkdir(exist_ok=True)
        
        visual_json = {
            "$schema": self.SCHEMAS["visual"],
            "name": visual.id,
            "visualType": visual.visual_type.value,
            "position": {
                "x": visual.x,
                "y": visual.y,
                "z": visual.z,
                "width": visual.width,
                "height": visual.height
            },
            "visual": self._build_visual_config(visual),
            "visualContainerObjects": {}
        }
        
        if visual.title:
            visual_json["visualContainerObjects"]["title"] = [{
                "properties": {
                    "text": {"expr": {"Literal": {"Value": f"'{visual.title}'"}}},
                    "show": {"expr": {"Literal": {"Value": "true"}}}
                }
            }]
        
        if visual.filters:
            visual_json["filters"] = visual.filters
        
        with open(visual_dir / "visual.json", 'w') as f:
            json.dump(visual_json, f, indent=2)
    
    def _build_visual_config(self, visual: PowerBIVisual) -> Dict[str, Any]:
        """Build the visual configuration object."""
        from translators.visual_mapper import VisualMapper
        
        config = {
            "visualType": visual.visual_type.value,
        }
        
        # Build data roles (projections)
        projections = {}
        
        # Get data role names for this visual type
        role_map = VisualMapper.VISUAL_DATA_ROLES.get(visual.visual_type, {
            "category": "Category",
            "values": "Values",
            "legend": "Legend"
        })
        
        if visual.category_fields:
            role_name = role_map.get("category", "Category")
            projections[role_name] = [
                {
                    "queryRef": f"{f.table}.{f.column}",
                    "active": True
                }
                for f in visual.category_fields
            ]
        
        if visual.value_fields:
            role_name = role_map.get("values", "Values")
            projections[role_name] = [
                {
                    "queryRef": f"{f.table}.{f.column}",
                    "active": True
                }
                for f in visual.value_fields
            ]
            
            # Special case for visuals with multiple value roles (like scatter)
            if "extra_values" in role_map and len(visual.value_fields) > 1:
                role_name = role_map["extra_values"]
                # Move the first value to the extra role if it's supposed to be there
                # This is a bit simplistic, but helps for Scatter X/Y
                pass
        
        if visual.legend_field:
            role_name = role_map.get("legend", "Legend")
            projections[role_name] = [{
                "queryRef": f"{visual.legend_field.table}.{visual.legend_field.column}",
                "active": True
            }]
            
        if visual.tooltip_fields:
            projections["Tooltips"] = [
                {
                    "queryRef": f"{f.table}.{f.column}",
                    "active": True
                }
                for f in visual.tooltip_fields
            ]
        
        if projections:
            config["projections"] = projections
            
            # Build prototype query
            config["prototypeQuery"] = self._build_prototype_query(visual)
        
        return config
    
    def _build_prototype_query(self, visual: PowerBIVisual) -> Dict[str, Any]:
        """Build the prototype query for a visual."""
        # Collect all fields
        selects = []
        
        # Dimensions (no aggregation)
        for f in visual.category_fields:
            if f.aggregation:
                # If it has aggregation, treat as measure
                agg = f.aggregation
                selects.append({
                    "Aggregation": {
                        "Expression": {
                            "Column": {
                                "Expression": {"SourceRef": {"Source": "d"}},
                                "Property": f.column
                            }
                        },
                        "Function": self._get_agg_function_id(agg)
                    },
                    "Name": f"{f.table}.{f.column}"
                })
            else:
                selects.append({
                    "Column": {
                        "Expression": {"SourceRef": {"Source": "d"}},
                        "Property": f.column
                    },
                    "Name": f"{f.table}.{f.column}"
                })
        
        # Measures
        for f in visual.value_fields:
            agg = f.aggregation or "Sum"
            selects.append({
                "Aggregation": {
                    "Expression": {
                        "Column": {
                            "Expression": {"SourceRef": {"Source": "d"}},
                            "Property": f.column
                        }
                    },
                    "Function": self._get_agg_function_id(agg)
                },
                "Name": f"{agg}({f.table}.{f.column})"
            })
        
        if visual.legend_field:
            f = visual.legend_field
            selects.append({
                "Column": {
                    "Expression": {"SourceRef": {"Source": "d"}},
                    "Property": f.column
                },
                "Name": f"{f.table}.{f.column}"
            })
            
        for f in visual.tooltip_fields:
            if f.aggregation:
                agg = f.aggregation
                selects.append({
                    "Aggregation": {
                        "Expression": {
                            "Column": {
                                "Expression": {"SourceRef": {"Source": "d"}},
                                "Property": f.column
                            }
                        },
                        "Function": self._get_agg_function_id(agg)
                    },
                    "Name": f"{f.table}.{f.column}"
                })
            else:
                selects.append({
                    "Column": {
                        "Expression": {"SourceRef": {"Source": "d"}},
                        "Property": f.column
                    },
                    "Name": f"{f.table}.{f.column}"
                })
        
        return {
            "Version": 2,
            "From": [{"Name": "d", "Entity": "Data", "Type": 0}],
            "Select": selects
        }
    
    def _get_agg_function_id(self, agg: str) -> int:
        """Get the aggregation function ID for Power BI."""
        agg_map = {
            "sum": 0,
            "average": 1,
            "min": 3,
            "max": 4,
            "count": 5,
            "distinctcount": 6,
            "median": 7,
            "variance": 8,
            "stddev": 9,
            "first": 0, # First/Last often use 0/1 in some contexts, but let's stick to Sum/Avg fallback
        }
        return agg_map.get(agg.lower(), 0)
    
    def _generate_semantic_model(self, model_dir: Path, report: PowerBIReport) -> None:
        """Generate the semantic model files."""
        definition_dir = model_dir / "definition"
        definition_dir.mkdir(exist_ok=True)
        
        # Generate model.tmdl (main model definition)
        model_tmdl = self._build_model_tmdl(report)
        with open(definition_dir / "model.tmdl", 'w') as f:
            f.write(model_tmdl)
        
        # Generate tables directory
        tables_dir = definition_dir / "tables"
        tables_dir.mkdir(exist_ok=True)
        
        for table in report.tables:
            table_tmdl = self._build_table_tmdl(table)
            with open(tables_dir / f"{self._sanitize_name(table.name)}.tmdl", 'w') as f:
                f.write(table_tmdl)
        
        # Generate expressions.tmdl (M queries)
        expressions_tmdl = self._build_expressions_tmdl(report)
        with open(definition_dir / "expressions.tmdl", 'w') as f:
            f.write(expressions_tmdl)
        
        # Generate definition.pbism
        pbism_content = {
            "version": "1.0",
            "settings": {}
        }
        with open(model_dir / "definition.pbism", 'w') as f:
            json.dump(pbism_content, f, indent=2)
    
    def _build_model_tmdl(self, report: PowerBIReport) -> str:
        """Build the model.tmdl content."""
        lines = [
            "model Model",
            f"    culture: en-US",
            f"    defaultPowerBIDataSourceVersion: powerBI_V3",
            "",
        ]
        
        # Add relationships
        for rel in report.relationships:
            lines.extend([
                f"relationship {rel.name}",
                f"    fromColumn: '{rel.from_table}'[{rel.from_column}]",
                f"    toColumn: '{rel.to_table}'[{rel.to_column}]",
                f"    crossFilteringBehavior: {rel.cross_filtering_behavior}",
                "",
            ])
        
        return "\n".join(lines)
    
    def _build_table_tmdl(self, table: PowerBITable) -> str:
        """Build TMDL content for a table."""
        lines = [
            f"table '{table.name}'",
            f"    lineageTag: {str(uuid.uuid4())}",
            "",
        ]
        
        # Add columns
        for col in table.columns:
            lines.extend([
                f"    column {col.name}",
                f"        dataType: {col.data_type.value}",
                f"        lineageTag: {str(uuid.uuid4())}",
                "",
            ])
        
        # Add measures
        for measure in table.measures:
            expr_lines = measure.expression.split('\n')
            if len(expr_lines) == 1:
                lines.extend([
                    f"    measure '{measure.name}' = {measure.expression}",
                    f"        lineageTag: {str(uuid.uuid4())}",
                ])
            else:
                lines.append(f"    measure '{measure.name}' =")
                for expr_line in expr_lines:
                    lines.append(f"        {expr_line}")
                lines.append(f"        lineageTag: {str(uuid.uuid4())}")
            
            if measure.description:
                lines.append(f"        description: {measure.description}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _build_expressions_tmdl(self, report: PowerBIReport) -> str:
        """Build the expressions.tmdl content (M queries)."""
        lines = ["expression Expressions"]
        
        for ds in report.data_sources:
            # Generate M query for data source
            m_query = self._generate_m_query(ds)
            lines.extend([
                "",
                f"    expression '{ds.name}' =",
                "        ```",
                f"        {m_query}",
                "        ```",
            ])
        
        if not report.data_sources:
            # Add a placeholder query
            lines.extend([
                "",
                "    expression 'Data' =",
                "        ```",
                "        let",
                "            Source = #table(",
                '                type table [Column1 = text],',
                '                {}',
                "            )",
                "        in",
                "            Source",
                "        ```",
            ])
        
        return "\n".join(lines)
    
    def _generate_m_query(self, ds: PowerBIDataSource) -> str:
        """Generate M query for a data source with templated connection strings."""
        if ds.connection_type == "SQL Server":
            server = ds.server or "localhost"
            database = ds.database or "Database"
            return f"""let
    Source = Sql.Database("{server}", "{database}"),
    Data = Source{{[Schema="dbo",Item="{ds.name}"]}}[Data]
in
    Data"""
        
        elif ds.connection_type == "PostgreSQL":
            server = ds.server or "localhost"
            database = ds.database or "Database"
            return f"""let
    Source = PostgreSQL.Database("{server}", "{database}"),
    Data = Source{{[Schema="public",Item="{ds.name}"]}}[Data]
in
    Data"""
        
        elif ds.connection_type == "Excel":
            # For Excel, we use a placeholder path that the user can easily update
            path = ds.connection_string or "C:\\Path\\To\\Your\\File.xlsx"
            return f"""let
    Source = Excel.Workbook(File.Contents("{path}"), null, true),
    Data = Source{{[Item="{ds.name}",Kind="Sheet"]}}[Data]
in
    Data"""

        elif ds.connection_type == "CSV":
            path = ds.connection_string or "C:\\Path\\To\\Your\\File.csv"
            return f"""let
    Source = Csv.Document(File.Contents("{path}"),[Delimiter=",", Columns=null, Encoding=65001, QuoteStyle=QuoteStyle.None])
in
    Source"""
        
        elif ds.connection_type == "Snowflake":
            server = ds.server or "account.snowflakecomputing.com"
            warehouse = "YOUR_WAREHOUSE"
            return f"""let
    Source = Snowflake.Databases("{server}", "{warehouse}"),
    Data = Source{{[Name="{ds.database}"]}}[Data]
in
    Data"""

        else:
            # Generic placeholder with comments for the user
            return f"""let
    // Converted from Tableau: {ds.connection_type}
    // Server: {ds.server or "N/A"}
    // Database: {ds.database or "N/A"}
    Source = #table(
        type table [Column1 = text],
        {{}}
    )
in
    Source"""
    
    def _generate_project_metadata(self, project_dir: Path, project_name: str) -> None:
        """Generate project-level metadata files."""
        # Create .pbip file
        pbip_content = {
            "version": "1.0",
            "artifacts": [
                {
                    "report": {
                        "path": f"{project_name}.Report"
                    }
                },
                {
                    "semanticModel": {
                        "path": f"{project_name}.SemanticModel"
                    }
                }
            ],
            "settings": {
                "enableAutoRecovery": True
            }
        }
        
        with open(project_dir / f"{project_name}.pbip", 'w') as f:
            json.dump(pbip_content, f, indent=2)
    
    def _generate_local_settings(self, pbi_dir: Path) -> None:
        """Generate local settings file."""
        settings = {
            "version": "1.0",
            "isAutoRecoveryEnabled": True
        }
        
        with open(pbi_dir / "localSettings.json", 'w') as f:
            json.dump(settings, f, indent=2)
    
    def generate_standalone_pbix_structure(self, report: PowerBIReport) -> Dict[str, Any]:
        """
        Generate the structure for a standalone PBIX file.
        
        Note: This returns the structure that would be inside a PBIX.
        Actually creating a working PBIX requires additional binary
        components that are beyond pure Python generation.
        
        Returns:
            Dictionary representing the PBIX internal structure
        """
        return {
            "[Content_Types].xml": self._generate_content_types(),
            "Report/Layout": json.dumps(self._generate_layout(report)),
            "DataMashup": "/* Binary - requires Power Query engine */",
            "DataModel": "/* Binary - requires Analysis Services */",
            "_rels/.rels": self._generate_rels(),
        }
    
    def _generate_content_types(self) -> str:
        """Generate [Content_Types].xml for PBIX."""
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="json" ContentType="application/json"/>
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Override PartName="/Report/Layout" ContentType="application/json"/>
    <Override PartName="/DataMashup" ContentType="application/x-powerbidatamashup"/>
    <Override PartName="/DataModel" ContentType="application/x-msanalysisservices-tabular"/>
</Types>"""
    
    def _generate_layout(self, report: PowerBIReport) -> Dict[str, Any]:
        """Generate the Layout JSON for PBIX."""
        return {
            "id": 0,
            "reportId": report.id,
            "sections": [
                {
                    "id": i,
                    "name": page.name,
                    "displayName": page.display_name or page.name,
                    "width": page.width,
                    "height": page.height,
                    "visualContainers": [
                        visual.to_json() for visual in page.visuals
                    ]
                }
                for i, page in enumerate(report.pages)
            ],
            "config": json.dumps({
                "version": "5.59",
                "themeCollection": {"baseTheme": {"name": "CY24SU02"}}
            }),
            "layoutOptimization": 0,
        }
    
    def _generate_rels(self) -> str:
        """Generate .rels file for PBIX."""
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.microsoft.com/packaging/2006/relationships/report" Target="/Report/Layout"/>
</Relationships>"""
