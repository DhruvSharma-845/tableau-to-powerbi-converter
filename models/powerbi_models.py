"""
Pydantic models for Power BI report components.
These models represent the structure needed for PBIR format output.
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class PowerBIDataType(str, Enum):
    """Power BI data types."""
    STRING = "string"
    INT64 = "int64"
    DOUBLE = "double"
    BOOLEAN = "boolean"
    DATETIME = "dateTime"
    DECIMAL = "decimal"


class PowerBIVisualType(str, Enum):
    """Power BI native visual types."""
    BAR_CHART = "barChart"
    CLUSTERED_BAR = "clusteredBarChart"
    STACKED_BAR = "stackedBarChart"
    COLUMN_CHART = "columnChart"
    CLUSTERED_COLUMN = "clusteredColumnChart"
    STACKED_COLUMN = "stackedColumnChart"
    LINE_CHART = "lineChart"
    AREA_CHART = "areaChart"
    STACKED_AREA = "stackedAreaChart"
    COMBO_CHART = "comboChart"
    PIE_CHART = "pieChart"
    DONUT_CHART = "donutChart"
    TREEMAP = "treemap"
    MAP = "map"
    FILLED_MAP = "filledMap"
    SCATTER_CHART = "scatterChart"
    TABLE = "tableEx"
    MATRIX = "pivotTable"
    CARD = "card"
    MULTI_ROW_CARD = "multiRowCard"
    KPI = "kpi"
    GAUGE = "gauge"
    SLICER = "slicer"
    TEXT_BOX = "textbox"
    IMAGE = "image"
    SHAPE = "shape"


class PowerBIColumn(BaseModel):
    """Represents a column in Power BI data model."""
    name: str
    source_column: Optional[str] = None
    data_type: PowerBIDataType = PowerBIDataType.STRING
    is_hidden: bool = False
    format_string: Optional[str] = None
    summarize_by: Optional[str] = None
    sort_by_column: Optional[str] = None
    
    def to_tmdl(self) -> str:
        """Generate TMDL representation."""
        lines = [f"    column {self.name}"]
        lines.append(f"        dataType: {self.data_type.value}")
        if self.source_column:
            lines.append(f"        sourceColumn: {self.source_column}")
        if self.is_hidden:
            lines.append("        isHidden")
        if self.format_string:
            lines.append(f"        formatString: {self.format_string}")
        return "\n".join(lines)


class PowerBIMeasure(BaseModel):
    """Represents a DAX measure in Power BI."""
    name: str
    expression: str
    description: Optional[str] = None
    format_string: Optional[str] = None
    display_folder: Optional[str] = None
    is_hidden: bool = False
    
    # Translation metadata
    source_tableau_field: Optional[str] = None
    source_formula: Optional[str] = None
    translation_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    translation_notes: List[str] = Field(default_factory=list)
    requires_review: bool = False
    
    def to_tmdl(self) -> str:
        """Generate TMDL representation."""
        lines = [f"    measure {self.name} = {self.expression}"]
        if self.description:
            lines.append(f"        description: {self.description}")
        if self.format_string:
            lines.append(f"        formatString: {self.format_string}")
        if self.display_folder:
            lines.append(f"        displayFolder: {self.display_folder}")
        if self.is_hidden:
            lines.append("        isHidden")
        return "\n".join(lines)


class PowerBITable(BaseModel):
    """Represents a table in Power BI data model."""
    name: str
    columns: List[PowerBIColumn] = Field(default_factory=list)
    measures: List[PowerBIMeasure] = Field(default_factory=list)
    is_hidden: bool = False
    
    # Source information
    source_type: str = Field(default="query", description="'query', 'calculated', 'date'")
    source_expression: Optional[str] = None
    
    def to_tmdl(self) -> str:
        """Generate TMDL representation."""
        lines = [f"table {self.name}"]
        if self.is_hidden:
            lines.append("    isHidden")
        
        for col in self.columns:
            lines.append(col.to_tmdl())
        
        for measure in self.measures:
            lines.append(measure.to_tmdl())
        
        return "\n".join(lines)


class PowerBIRelationship(BaseModel):
    """Represents a relationship in Power BI data model."""
    name: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    is_active: bool = True
    cross_filtering_behavior: str = Field(default="oneDirection", description="'oneDirection' or 'bothDirections'")
    cardinality: str = Field(default="manyToOne", description="'manyToOne', 'oneToMany', 'oneToOne', 'manyToMany'")


class PowerBIDataSource(BaseModel):
    """Represents a data source connection in Power BI."""
    name: str
    connection_type: str
    connection_string: Optional[str] = None
    
    # Specific connection details
    server: Optional[str] = None
    database: Optional[str] = None
    query: Optional[str] = None


class VisualDataField(BaseModel):
    """Represents a field binding in a Power BI visual."""
    table: str
    column: str
    aggregation: Optional[str] = None


class PowerBIVisual(BaseModel):
    """Represents a visual on a Power BI page."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    visual_type: PowerBIVisualType
    name: Optional[str] = None
    title: Optional[str] = None
    
    # Position and size
    x: float = 0
    y: float = 0
    width: float = 300
    height: float = 200
    z: int = 0
    
    # Data bindings
    category_fields: List[VisualDataField] = Field(default_factory=list)
    value_fields: List[VisualDataField] = Field(default_factory=list)
    legend_field: Optional[VisualDataField] = None
    tooltip_fields: List[VisualDataField] = Field(default_factory=list)
    
    # Filters
    filters: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Configuration
    config: Dict[str, Any] = Field(default_factory=dict)
    
    # Translation metadata
    source_tableau_worksheet: Optional[str] = None
    translation_notes: List[str] = Field(default_factory=list)
    
    def to_json(self) -> Dict[str, Any]:
        """Generate PBIR JSON representation."""
        visual_config = {
            "name": self.id,
            "visualType": self.visual_type.value,
            "position": {
                "x": self.x,
                "y": self.y,
                "width": self.width,
                "height": self.height,
                "z": self.z,
            },
            "visual": {
                "visualType": self.visual_type.value,
            }
        }
        
        if self.title:
            visual_config["title"] = self.title
        
        # Add data bindings
        data_bindings = {}
        
        if self.category_fields:
            data_bindings["category"] = [
                {"table": f.table, "column": f.column}
                for f in self.category_fields
            ]
        
        if self.value_fields:
            data_bindings["values"] = [
                {
                    "table": f.table,
                    "column": f.column,
                    "aggregation": f.aggregation or "sum"
                }
                for f in self.value_fields
            ]
        
        if self.legend_field:
            data_bindings["legend"] = {
                "table": self.legend_field.table,
                "column": self.legend_field.column
            }
        
        if data_bindings:
            visual_config["dataBindings"] = data_bindings
        
        if self.filters:
            visual_config["filters"] = self.filters
        
        if self.config:
            visual_config["config"] = self.config
        
        return visual_config


class PowerBIPage(BaseModel):
    """Represents a page in a Power BI report."""
    name: str
    display_name: Optional[str] = None
    width: int = 1280
    height: int = 720
    visuals: List[PowerBIVisual] = Field(default_factory=list)
    
    # Page settings
    background_color: Optional[str] = None
    wallpaper: Optional[str] = None
    
    # Translation metadata
    source_tableau_dashboard: Optional[str] = None
    source_tableau_worksheet: Optional[str] = None
    
    def to_json(self) -> Dict[str, Any]:
        """Generate PBIR JSON representation for page."""
        page_config = {
            "name": self.name,
            "displayName": self.display_name or self.name,
            "width": self.width,
            "height": self.height,
        }
        
        if self.background_color:
            page_config["backgroundColor"] = self.background_color
        
        return page_config


class PowerBIReport(BaseModel):
    """Represents a complete Power BI report."""
    name: str
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Report structure
    pages: List[PowerBIPage] = Field(default_factory=list)
    
    # Data model
    tables: List[PowerBITable] = Field(default_factory=list)
    relationships: List[PowerBIRelationship] = Field(default_factory=list)
    data_sources: List[PowerBIDataSource] = Field(default_factory=list)
    
    # Standalone measures (not in tables)
    measures: List[PowerBIMeasure] = Field(default_factory=list)
    
    # Report settings
    theme: Optional[str] = None
    
    # Translation metadata
    source_tableau_workbook: Optional[str] = None
    translation_stats: Dict[str, Any] = Field(default_factory=dict)
    
    def get_all_measures(self) -> List[PowerBIMeasure]:
        """Get all measures from all tables and standalone."""
        measures = list(self.measures)
        for table in self.tables:
            measures.extend(table.measures)
        return measures
    
    def add_measure_to_table(self, table_name: str, measure: PowerBIMeasure) -> bool:
        """Add a measure to a specific table."""
        for table in self.tables:
            if table.name == table_name:
                table.measures.append(measure)
                return True
        return False
