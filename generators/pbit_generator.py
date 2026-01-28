"""
Power BI Template (PBIT) Generator.

PBIT files are similar to PBIX but don't contain data, making them
easier to generate and more reliable to open in Power BI Desktop.

This module generates a PBIT file that can be opened in Power BI Desktop,
where you can then connect to your data sources.
"""
import json
import zipfile
import uuid
import io
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from models.powerbi_models import PowerBIReport


class PBITGenerator:
    """
    Generates Power BI Template (PBIT) files.
    
    PBIT is essentially PBIX without data, making it more portable
    and easier to generate.
    """
    
    PAGE_WIDTH = 1280
    PAGE_HEIGHT = 720
    
    def __init__(self):
        self.report_id = str(uuid.uuid4())
    
    def generate(self, report: PowerBIReport, output_path: str) -> str:
        """Generate a PBIT file from a PowerBIReport."""
        output_path = Path(output_path)
        if not output_path.suffix.lower() == '.pbit':
            output_path = output_path.with_suffix('.pbit')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as pbit:
            # Content types
            pbit.writestr('[Content_Types].xml', self._content_types())
            
            # Version
            pbit.writestr('Version', '2.0.0.0')
            
            # Report layout
            layout = self._generate_layout(report)
            pbit.writestr('Report/Layout', json.dumps(layout, ensure_ascii=False))
            
            # Linguistic schema
            pbit.writestr('Report/LinguisticSchema', json.dumps({
                "Version": 1,
                "Language": "en-US"
            }))
            
            # Settings
            pbit.writestr('Settings', json.dumps({
                "Version": 3,
                "ReportSettings": {"persistentFilters": {"enabled": False}}
            }))
            
            # Metadata
            pbit.writestr('Metadata', json.dumps({
                "version": "1.0",
                "createdFrom": "Tableau-to-PowerBI-Converter",
                "createdDate": datetime.utcnow().isoformat()
            }))
            
            # Empty security bindings
            pbit.writestr('SecurityBindings', '')
            
            # Diagram layout
            pbit.writestr('DiagramLayout', json.dumps({
                "version": "1.0",
                "diagrams": []
            }))
            
            # Connections
            pbit.writestr('Connections', json.dumps({
                "Version": 1,
                "Connections": []
            }))
            
            # DataMashup - minimal Power Query package
            pbit.writestr('DataMashup', self._minimal_mashup(report))
            
            # Data model schema
            pbit.writestr('DataModelSchema', self._generate_model_schema(report))
        
        return str(output_path)
    
    def _content_types(self) -> str:
        return '''<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="application/json"/>
  <Override PartName="/Report/Layout" ContentType="application/json"/>
  <Override PartName="/Report/LinguisticSchema" ContentType="application/json"/>
  <Override PartName="/DataMashup" ContentType="application/vnd.ms-package.datamashup"/>
  <Override PartName="/DataModelSchema" ContentType="application/json"/>
  <Override PartName="/Metadata" ContentType="application/json"/>
  <Override PartName="/Settings" ContentType="application/json"/>
  <Override PartName="/Connections" ContentType="application/json"/>
  <Override PartName="/DiagramLayout" ContentType="application/json"/>
  <Override PartName="/Version" ContentType="text/plain"/>
</Types>'''
    
    def _minimal_mashup(self, report: PowerBIReport) -> bytes:
        """Create minimal DataMashup ZIP."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as z:
            # Config
            z.writestr('Config/Config.xml', '''<?xml version="1.0" encoding="utf-8"?>
<Config xmlns="http://schemas.datacontract.org/2004/07/Microsoft.Data.Mashup">
  <ConfigElement Name="CurrentCulture">en-US</ConfigElement>
</Config>''')
            
            # M section
            m_code = 'section Section1;\n\n'
            for table in report.tables:
                name = self._safe_name(table.name)
                m_code += f'''shared #"{name}" = let
    Source = #table(type table [Column1 = text], {{}})
in
    Source;

'''
            if not report.tables:
                m_code += '''shared Data = let
    Source = #table(type table [Column1 = text], {})
in
    Source;
'''
            z.writestr('Formulas/Section1.m', m_code.encode('utf-8'))
            
            # Content types
            z.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Override PartName="/Config/Config.xml" ContentType="text/xml"/>
  <Override PartName="/Formulas/Section1.m" ContentType="text/x-m"/>
</Types>''')
        
        return buffer.getvalue()
    
    def _safe_name(self, name: str) -> str:
        return ''.join(c if c.isalnum() or c in ' _-' else '_' for c in name).strip()
    
    def _generate_layout(self, report: PowerBIReport) -> dict:
        """Generate report layout."""
        sections = []
        
        for idx, page in enumerate(report.pages):
            visuals = []
            cols = min(3, max(1, len(page.visuals)))
            
            for v_idx, visual in enumerate(page.visuals):
                col = v_idx % cols
                row = v_idx // cols
                w = (self.PAGE_WIDTH - 60) // cols
                h = 200
                x = 20 + col * (w + 10)
                y = 20 + row * (h + 10)
                
                vis_type = getattr(visual.visual_type, 'value', 'card')
                title = visual.title or visual.name or f"Visual {v_idx + 1}"
                
                config = {
                    "name": uuid.uuid4().hex,
                    "layouts": [{"id": 0, "position": {
                        "x": x, "y": y, "z": v_idx * 1000,
                        "width": w, "height": h, "tabOrder": v_idx * 1000
                    }}],
                    "singleVisual": {
                        "visualType": self._validate_type(vis_type),
                        "drillFilterOtherVisuals": True,
                        "objects": {
                            "title": [{"properties": {
                                "text": {"expr": {"Literal": {"Value": f"'{title}'"}}},
                                "show": {"expr": {"Literal": {"Value": "true"}}}
                            }}]
                        }
                    }
                }
                
                visuals.append({
                    "x": x, "y": y, "z": v_idx * 1000,
                    "width": w, "height": h,
                    "config": json.dumps(config),
                    "filters": "[]",
                    "tabOrder": v_idx * 1000
                })
            
            sections.append({
                "id": idx,
                "name": uuid.uuid4().hex,
                "displayName": page.display_name or page.name or f"Page {idx + 1}",
                "displayOption": 1,
                "width": self.PAGE_WIDTH,
                "height": self.PAGE_HEIGHT,
                "visualContainers": visuals,
                "config": json.dumps({"visibility": 0})
            })
        
        if not sections:
            sections.append({
                "id": 0, "name": uuid.uuid4().hex,
                "displayName": "Page 1", "displayOption": 1,
                "width": self.PAGE_WIDTH, "height": self.PAGE_HEIGHT,
                "visualContainers": [],
                "config": json.dumps({"visibility": 0})
            })
        
        return {
            "id": self.report_id,
            "reportId": self.report_id,
            "sections": sections,
            "config": json.dumps({
                "version": "5.50",
                "themeCollection": {"baseTheme": {"name": "CY24SU06", "type": 2}},
                "activeSectionIndex": 0,
                "settings": {"isPersistentUserStateDisabled": True}
            }),
            "layoutOptimization": 0,
            "publicCustomVisuals": [],
            "resourcePackages": []
        }
    
    def _validate_type(self, t: str) -> str:
        valid = {'clusteredBarChart', 'clusteredColumnChart', 'lineChart', 
                 'pieChart', 'card', 'tableEx', 'slicer', 'map', 'scatterChart'}
        return t if t in valid else 'card'
    
    def _generate_model_schema(self, report: PowerBIReport) -> str:
        """Generate data model schema."""
        tables = []
        
        for table in report.tables:
            cols = [{
                "name": c.name,
                "dataType": self._map_type(c.data_type),
                "sourceColumn": c.source_column or c.name,
                "lineageTag": str(uuid.uuid4())
            } for c in table.columns]
            
            measures = [{
                "name": m.name,
                "expression": m.expression or "0",
                "lineageTag": str(uuid.uuid4()),
                **({"description": m.description} if m.description else {}),
                **({"displayFolder": m.display_folder} if m.display_folder else {})
            } for m in table.measures]
            
            tables.append({
                "name": table.name,
                "lineageTag": str(uuid.uuid4()),
                "columns": cols,
                "measures": measures,
                "partitions": [{
                    "name": table.name,
                    "mode": "import",
                    "source": {
                        "type": "m",
                        "expression": [
                            "let",
                            f"    Source = #\"{self._safe_name(table.name)}\"",
                            "in",
                            "    Source"
                        ]
                    }
                }]
            })
        
        return json.dumps({
            "name": report.name or "Model",
            "compatibilityLevel": 1567,
            "model": {
                "culture": "en-US",
                "defaultPowerBIDataSourceVersion": "powerBI_V3",
                "tables": tables,
                "relationships": [],
                "annotations": []
            }
        }, indent=2)
    
    def _map_type(self, t) -> str:
        if hasattr(t, 'value'):
            t = t.value
        return {'string': 'string', 'int64': 'int64', 'double': 'double',
                'datetime': 'dateTime'}.get(str(t).lower(), 'string')


def create_pbit(report: PowerBIReport, output_path: str) -> str:
    """Create a PBIT file from a PowerBIReport."""
    return PBITGenerator().generate(report, output_path)
