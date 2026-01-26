"""
Pydantic models for Tableau workbook components.
These models represent the parsed structure of a Tableau workbook.
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class DataType(str, Enum):
    """Tableau data types."""
    STRING = "string"
    INTEGER = "integer"
    REAL = "real"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    UNKNOWN = "unknown"


class AggregationType(str, Enum):
    """Tableau aggregation types."""
    SUM = "sum"
    AVG = "avg"
    COUNT = "count"
    COUNTD = "countd"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    ATTR = "attr"
    NONE = "none"


class MarkType(str, Enum):
    """Tableau mark types for visualization."""
    BAR = "bar"
    LINE = "line"
    AREA = "area"
    SQUARE = "square"
    CIRCLE = "circle"
    SHAPE = "shape"
    TEXT = "text"
    MAP = "map"
    PIE = "pie"
    GANTT = "gantt"
    POLYGON = "polygon"
    AUTOMATIC = "automatic"


class CalculationType(str, Enum):
    """Types of Tableau calculations."""
    SIMPLE = "simple"
    LOD_FIXED = "lod_fixed"
    LOD_INCLUDE = "lod_include"
    LOD_EXCLUDE = "lod_exclude"
    TABLE_CALC = "table_calc"
    AGGREGATE = "aggregate"
    ROW_LEVEL = "row_level"


class TableauConnection(BaseModel):
    """Represents a data source connection in Tableau."""
    class_name: str = Field(default="", description="Connection class (e.g., 'sqlserver', 'excel')")
    server: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    schema_name: Optional[str] = Field(default=None, alias="schema")
    username: Optional[str] = None
    filename: Optional[str] = None
    connection_type: str = Field(default="unknown", description="Type of connection")
    custom_sql: Optional[str] = None
    
    class Config:
        populate_by_name = True


class TableauColumn(BaseModel):
    """Represents a column/field in Tableau."""
    name: str
    caption: Optional[str] = None
    datatype: DataType = DataType.UNKNOWN
    role: str = Field(default="dimension", description="'dimension' or 'measure'")
    aggregation: AggregationType = AggregationType.NONE
    hidden: bool = False
    semantic_role: Optional[str] = None
    
    @property
    def display_name(self) -> str:
        """Return the display name (caption or name)."""
        return self.caption or self.name


class TableauCalculatedField(BaseModel):
    """Represents a calculated field in Tableau."""
    name: str
    caption: Optional[str] = None
    formula: str
    datatype: DataType = DataType.UNKNOWN
    calculation_type: CalculationType = CalculationType.SIMPLE
    role: str = Field(default="measure", description="'dimension' or 'measure'")
    
    # Parsed components for complex calculations
    lod_dimensions: List[str] = Field(default_factory=list)
    table_calc_type: Optional[str] = None
    table_calc_direction: Optional[str] = None
    referenced_fields: List[str] = Field(default_factory=list)
    
    @property
    def display_name(self) -> str:
        """Return the display name (caption or name)."""
        return self.caption or self.name
    
    @property
    def is_lod(self) -> bool:
        """Check if this is an LOD expression."""
        return self.calculation_type in [
            CalculationType.LOD_FIXED,
            CalculationType.LOD_INCLUDE,
            CalculationType.LOD_EXCLUDE,
        ]
    
    @property
    def is_table_calc(self) -> bool:
        """Check if this is a table calculation."""
        return self.calculation_type == CalculationType.TABLE_CALC


class TableauParameter(BaseModel):
    """Represents a parameter in Tableau."""
    name: str
    caption: Optional[str] = None
    datatype: DataType = DataType.STRING
    current_value: Optional[Any] = None
    allowable_values_type: str = Field(default="all", description="'all', 'list', or 'range'")
    allowable_values: List[Any] = Field(default_factory=list)
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    step_size: Optional[float] = None
    
    @property
    def display_name(self) -> str:
        """Return the display name (caption or name)."""
        return self.caption or self.name


class TableauFilter(BaseModel):
    """Represents a filter in Tableau."""
    field: str
    filter_type: str = Field(default="categorical", description="'categorical', 'quantitative', 'relative_date'")
    values: List[Any] = Field(default_factory=list)
    include_null: bool = True
    range_min: Optional[Any] = None
    range_max: Optional[Any] = None
    condition: Optional[str] = None


class FieldMapping(BaseModel):
    """Represents field placement on a shelf."""
    field: str
    shelf: str = Field(description="'rows', 'columns', 'color', 'size', 'label', 'detail', 'tooltip'")
    aggregation: AggregationType = AggregationType.NONE
    sort_order: Optional[str] = None


class TableauMark(BaseModel):
    """Represents mark configuration for a worksheet."""
    mark_type: MarkType = MarkType.AUTOMATIC
    color: Optional[str] = None
    size: Optional[float] = None
    shape: Optional[str] = None
    label_field: Optional[str] = None


class TableauWorksheet(BaseModel):
    """Represents a worksheet in Tableau."""
    name: str
    title: Optional[str] = None
    mark: TableauMark = Field(default_factory=TableauMark)
    rows: List[FieldMapping] = Field(default_factory=list)
    columns: List[FieldMapping] = Field(default_factory=list)
    filters: List[TableauFilter] = Field(default_factory=list)
    color_field: Optional[FieldMapping] = None
    size_field: Optional[FieldMapping] = None
    label_fields: List[FieldMapping] = Field(default_factory=list)
    detail_fields: List[FieldMapping] = Field(default_factory=list)
    tooltip_fields: List[FieldMapping] = Field(default_factory=list)
    
    # References to data source
    datasource_name: Optional[str] = None
    
    @property
    def all_fields(self) -> List[str]:
        """Get all fields used in this worksheet."""
        fields = []
        for mapping in self.rows + self.columns + self.label_fields + self.detail_fields:
            fields.append(mapping.field)
        if self.color_field:
            fields.append(self.color_field.field)
        if self.size_field:
            fields.append(self.size_field.field)
        return list(set(fields))


class DashboardObject(BaseModel):
    """Represents an object on a dashboard."""
    object_type: str = Field(description="'worksheet', 'text', 'image', 'web', 'blank'")
    name: Optional[str] = None
    worksheet_name: Optional[str] = None
    x: float = 0
    y: float = 0
    width: float = 100
    height: float = 100
    z_order: int = 0


class TableauDashboard(BaseModel):
    """Represents a dashboard in Tableau."""
    name: str
    title: Optional[str] = None
    width: int = 1000
    height: int = 800
    objects: List[DashboardObject] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    
    @property
    def worksheets(self) -> List[str]:
        """Get all worksheet names used in this dashboard."""
        return [
            obj.worksheet_name
            for obj in self.objects
            if obj.object_type == "worksheet" and obj.worksheet_name
        ]


class TableauDataSource(BaseModel):
    """Represents a data source in Tableau."""
    name: str
    caption: Optional[str] = None
    connection: Optional[TableauConnection] = None
    columns: List[TableauColumn] = Field(default_factory=list)
    calculated_fields: List[TableauCalculatedField] = Field(default_factory=list)
    parameters: List[TableauParameter] = Field(default_factory=list)
    
    # Relationships/joins
    tables: List[str] = Field(default_factory=list)
    joins: List[Dict[str, Any]] = Field(default_factory=list)
    
    @property
    def display_name(self) -> str:
        """Return the display name (caption or name)."""
        return self.caption or self.name
    
    def get_field(self, name: str) -> Optional[TableauColumn]:
        """Get a field by name."""
        for col in self.columns:
            if col.name == name or col.caption == name:
                return col
        return None
    
    def get_calculated_field(self, name: str) -> Optional[TableauCalculatedField]:
        """Get a calculated field by name."""
        for calc in self.calculated_fields:
            if calc.name == name or calc.caption == name:
                return calc
        return None


class TableauWorkbook(BaseModel):
    """Represents a complete Tableau workbook."""
    name: str
    version: Optional[str] = None
    datasources: List[TableauDataSource] = Field(default_factory=list)
    worksheets: List[TableauWorksheet] = Field(default_factory=list)
    dashboards: List[TableauDashboard] = Field(default_factory=list)
    parameters: List[TableauParameter] = Field(default_factory=list)
    
    # Metadata
    source_file: Optional[str] = None
    has_extract: bool = False
    extract_files: List[str] = Field(default_factory=list)
    
    def get_datasource(self, name: str) -> Optional[TableauDataSource]:
        """Get a data source by name."""
        for ds in self.datasources:
            if ds.name == name or ds.caption == name:
                return ds
        return None
    
    def get_worksheet(self, name: str) -> Optional[TableauWorksheet]:
        """Get a worksheet by name."""
        for ws in self.worksheets:
            if ws.name == name:
                return ws
        return None
    
    def get_all_calculated_fields(self) -> List[TableauCalculatedField]:
        """Get all calculated fields from all data sources."""
        fields = []
        for ds in self.datasources:
            fields.extend(ds.calculated_fields)
        return fields
    
    @property
    def total_fields(self) -> int:
        """Get total number of fields across all data sources."""
        return sum(
            len(ds.columns) + len(ds.calculated_fields)
            for ds in self.datasources
        )
    
    @property
    def total_calculated_fields(self) -> int:
        """Get total number of calculated fields."""
        return sum(len(ds.calculated_fields) for ds in self.datasources)
