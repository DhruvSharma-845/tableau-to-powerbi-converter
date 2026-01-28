"""
JSON Export Generator.

Exports the converted Tableau workbook as JSON files that can be
used to manually create Power BI reports or imported via Power Query.

This is the most reliable approach when PBIX generation has issues.
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from models.powerbi_models import PowerBIReport


class JSONExporter:
    """
    Exports Power BI report definitions as JSON files.
    
    Generates:
    - measures.json: All DAX measures ready to copy into Power BI
    - model.json: Data model definition (tables, columns, relationships)
    - visuals.json: Visual configurations for each page
    - summary.md: Human-readable summary of the conversion
    """
    
    def export(self, report: PowerBIReport, output_dir: str) -> Dict[str, str]:
        """
        Export report as JSON files.
        
        Args:
            report: PowerBIReport to export
            output_dir: Directory to write files
            
        Returns:
            Dictionary of file paths created
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        files = {}
        
        # Export measures
        measures_file = output_dir / "measures.json"
        measures = self._export_measures(report)
        with open(measures_file, 'w', encoding='utf-8') as f:
            json.dump(measures, f, indent=2, ensure_ascii=False)
        files['measures'] = str(measures_file)
        
        # Export data model
        model_file = output_dir / "model.json"
        model = self._export_model(report)
        with open(model_file, 'w', encoding='utf-8') as f:
            json.dump(model, f, indent=2, ensure_ascii=False)
        files['model'] = str(model_file)
        
        # Export visuals
        visuals_file = output_dir / "visuals.json"
        visuals = self._export_visuals(report)
        with open(visuals_file, 'w', encoding='utf-8') as f:
            json.dump(visuals, f, indent=2, ensure_ascii=False)
        files['visuals'] = str(visuals_file)
        
        # Export DAX measures as text (easy copy-paste)
        dax_file = output_dir / "dax_measures.txt"
        dax_text = self._export_dax_text(report)
        with open(dax_file, 'w', encoding='utf-8') as f:
            f.write(dax_text)
        files['dax'] = str(dax_file)
        
        # Export summary
        summary_file = output_dir / "conversion_summary.md"
        summary = self._export_summary(report, files)
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        files['summary'] = str(summary_file)
        
        return files
    
    def _export_measures(self, report: PowerBIReport) -> Dict[str, Any]:
        """Export all measures."""
        measures = []
        
        for table in report.tables:
            for measure in table.measures:
                measures.append({
                    "name": measure.name,
                    "table": table.name,
                    "expression": measure.expression,
                    "description": measure.description,
                    "displayFolder": measure.display_folder,
                    "formatString": measure.format_string,
                    "sourceTableauField": measure.source_tableau_field,
                    "sourceFormula": measure.source_formula,
                    "translationNotes": measure.translation_notes,
                    "requiresReview": measure.requires_review,
                    "confidence": measure.translation_confidence
                })
        
        return {
            "exportDate": datetime.utcnow().isoformat(),
            "totalMeasures": len(measures),
            "measures": measures
        }
    
    def _export_model(self, report: PowerBIReport) -> Dict[str, Any]:
        """Export data model."""
        tables = []
        
        for table in report.tables:
            columns = [{
                "name": col.name,
                "dataType": col.data_type.value if hasattr(col.data_type, 'value') else str(col.data_type),
                "sourceColumn": col.source_column,
                "isHidden": col.is_hidden,
                "formatString": col.format_string
            } for col in table.columns]
            
            tables.append({
                "name": table.name,
                "columns": columns,
                "measureCount": len(table.measures),
                "isHidden": table.is_hidden
            })
        
        relationships = [{
            "fromTable": rel.from_table,
            "fromColumn": rel.from_column,
            "toTable": rel.to_table,
            "toColumn": rel.to_column,
            "cardinality": rel.cardinality,
            "isActive": rel.is_active
        } for rel in report.relationships]
        
        return {
            "name": report.name,
            "tables": tables,
            "relationships": relationships,
            "totalTables": len(tables),
            "totalColumns": sum(len(t['columns']) for t in tables),
            "totalRelationships": len(relationships)
        }
    
    def _export_visuals(self, report: PowerBIReport) -> Dict[str, Any]:
        """Export visual configurations."""
        pages = []
        
        for page in report.pages:
            visuals = []
            for visual in page.visuals:
                vis_type = visual.visual_type
                if hasattr(vis_type, 'value'):
                    vis_type = vis_type.value
                
                visuals.append({
                    "name": visual.name,
                    "title": visual.title,
                    "visualType": vis_type,
                    "position": {
                        "x": visual.x,
                        "y": visual.y,
                        "width": visual.width,
                        "height": visual.height
                    },
                    "categoryFields": [
                        {"table": f.table, "column": f.column}
                        for f in visual.category_fields
                    ],
                    "valueFields": [
                        {"table": f.table, "column": f.column, "aggregation": f.aggregation}
                        for f in visual.value_fields
                    ],
                    "sourceTableauWorksheet": visual.source_tableau_worksheet,
                    "translationNotes": visual.translation_notes
                })
            
            pages.append({
                "name": page.name,
                "displayName": page.display_name,
                "width": page.width,
                "height": page.height,
                "visuals": visuals,
                "sourceTableauDashboard": page.source_tableau_dashboard
            })
        
        return {
            "reportName": report.name,
            "totalPages": len(pages),
            "totalVisuals": sum(len(p['visuals']) for p in pages),
            "pages": pages
        }
    
    def _export_dax_text(self, report: PowerBIReport) -> str:
        """Export DAX measures as plain text for easy copy-paste."""
        lines = [
            "=" * 60,
            "DAX MEASURES - Ready to copy into Power BI",
            "=" * 60,
            f"Generated: {datetime.utcnow().isoformat()}",
            f"Source: {report.source_tableau_workbook}",
            "",
            "Instructions:",
            "1. Open your Power BI report",
            "2. Go to Modeling > New Measure",
            "3. Copy and paste each measure below",
            "",
            "=" * 60,
            ""
        ]
        
        for table in report.tables:
            if table.measures:
                lines.append(f"-- Table: {table.name}")
                lines.append("-" * 40)
                
                for measure in table.measures:
                    lines.append(f"\n-- {measure.name}")
                    if measure.source_tableau_field:
                        lines.append(f"-- Source Tableau field: {measure.source_tableau_field}")
                    if measure.source_formula:
                        lines.append(f"-- Source formula: {measure.source_formula[:100]}...")
                    if measure.translation_notes:
                        for note in measure.translation_notes:
                            lines.append(f"-- Note: {note}")
                    
                    lines.append(f"{measure.name} = ")
                    # Indent multi-line expressions
                    expr_lines = (measure.expression or "0").split('\n')
                    for expr_line in expr_lines:
                        lines.append(f"    {expr_line}")
                    lines.append("")
                
                lines.append("")
        
        return '\n'.join(lines)
    
    def _export_summary(self, report: PowerBIReport, files: Dict[str, str]) -> str:
        """Export conversion summary."""
        lines = [
            f"# Tableau to Power BI Conversion Summary",
            "",
            f"**Report Name:** {report.name}",
            f"**Conversion Date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
            f"**Source:** {report.source_tableau_workbook}",
            "",
            "## Files Generated",
            "",
        ]
        
        for name, path in files.items():
            lines.append(f"- **{name}**: `{path}`")
        
        lines.extend([
            "",
            "## Data Model Summary",
            "",
            f"| Component | Count |",
            f"|-----------|-------|",
            f"| Tables | {len(report.tables)} |",
            f"| Columns | {sum(len(t.columns) for t in report.tables)} |",
            f"| Measures | {sum(len(t.measures) for t in report.tables)} |",
            f"| Relationships | {len(report.relationships)} |",
            f"| Pages | {len(report.pages)} |",
            f"| Visuals | {sum(len(p.visuals) for p in report.pages)} |",
            "",
            "## How to Use These Files",
            "",
            "### Option 1: Manual Creation in Power BI Desktop",
            "",
            "1. Open Power BI Desktop",
            "2. Connect to your data source",
            "3. Open `dax_measures.txt` and copy each measure into Power BI",
            "4. Create visuals based on `visuals.json`",
            "",
            "### Option 2: Use the PBIP Format",
            "",
            "The `.pbip` folder can be opened with Power BI Desktop (November 2023+)",
            "with Developer Mode enabled.",
            "",
            "### Option 3: Import Model via Tabular Editor",
            "",
            "1. Download Tabular Editor (free)",
            "2. Import `model.json` to create the semantic model",
            "3. Connect to Power BI Service",
            "",
            "## Measures Reference",
            "",
        ])
        
        for table in report.tables:
            if table.measures:
                lines.append(f"### {table.name}")
                lines.append("")
                for measure in table.measures:
                    confidence = measure.translation_confidence
                    status = "✅" if confidence >= 0.8 else "⚠️" if confidence >= 0.5 else "❌"
                    lines.append(f"- {status} **{measure.name}**")
                    if measure.requires_review:
                        lines.append(f"  - *Requires review*")
                lines.append("")
        
        return '\n'.join(lines)


def export_to_json(report: PowerBIReport, output_dir: str) -> Dict[str, str]:
    """Export a PowerBIReport as JSON files."""
    return JSONExporter().export(report, output_dir)
