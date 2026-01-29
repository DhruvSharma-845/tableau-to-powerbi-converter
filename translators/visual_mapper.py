"""
Visual mapper for converting Tableau worksheets to Power BI visuals.

Maps Tableau mark types and visualization configurations to equivalent
Power BI visual types and configurations.
"""

from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from models.tableau_models import (
    TableauWorksheet, TableauMark, MarkType, FieldMapping, AggregationType,
    TableauDashboard, TableauWorkbook
)
from models.powerbi_models import (
    PowerBIVisual, PowerBIVisualType, VisualDataField, PowerBIPage
)
from translators.custom_visuals import custom_visual_registry, get_recommended_visual


class MappingConfidence(Enum):
    """Confidence levels for visual mapping."""
    EXACT = "exact"           # Direct equivalent exists
    GOOD = "good"             # Good match with minor differences
    PARTIAL = "partial"       # Partial match, some features lost
    CUSTOM = "custom"         # Requires custom/marketplace visual
    UNSUPPORTED = "unsupported"  # No equivalent


@dataclass
class VisualMappingResult:
    """Result of mapping a Tableau visual to Power BI."""
    powerbi_visual: PowerBIVisual
    confidence: MappingConfidence
    notes: List[str] = field(default_factory=list)
    requires_custom_visual: bool = False
    custom_visual_id: Optional[str] = None
    unmapped_features: List[str] = field(default_factory=list)


class VisualMapper:
    """
    Maps Tableau visualizations to Power BI visuals.
    Enhanced with better chart type detection and comprehensive visual mappings.
    """
    
    # Mark type to visual type mapping
    MARK_TO_VISUAL: Dict[MarkType, Tuple[PowerBIVisualType, MappingConfidence]] = {
        MarkType.BAR: (PowerBIVisualType.CLUSTERED_BAR, MappingConfidence.EXACT),
        MarkType.LINE: (PowerBIVisualType.LINE_CHART, MappingConfidence.EXACT),
        MarkType.AREA: (PowerBIVisualType.AREA_CHART, MappingConfidence.EXACT),
        MarkType.CIRCLE: (PowerBIVisualType.SCATTER_CHART, MappingConfidence.GOOD),
        MarkType.SQUARE: (PowerBIVisualType.TREEMAP, MappingConfidence.PARTIAL),
        MarkType.SHAPE: (PowerBIVisualType.SCATTER_CHART, MappingConfidence.PARTIAL),
        MarkType.TEXT: (PowerBIVisualType.TABLE, MappingConfidence.GOOD),
        MarkType.MAP: (PowerBIVisualType.MAP, MappingConfidence.GOOD),
        MarkType.PIE: (PowerBIVisualType.PIE_CHART, MappingConfidence.EXACT),
        MarkType.GANTT: (PowerBIVisualType.CLUSTERED_BAR, MappingConfidence.CUSTOM),
        MarkType.POLYGON: (PowerBIVisualType.FILLED_MAP, MappingConfidence.PARTIAL),
        MarkType.AUTOMATIC: (PowerBIVisualType.CLUSTERED_COLUMN, MappingConfidence.GOOD),
    }
    
    # Extended visual detection based on worksheet name patterns
    VISUAL_NAME_PATTERNS: Dict[str, PowerBIVisualType] = {
        "waterfall": PowerBIVisualType.CLUSTERED_COLUMN,  # Waterfall pattern
        "funnel": PowerBIVisualType.CLUSTERED_BAR,  # Funnel pattern  
        "donut": PowerBIVisualType.DONUT_CHART,
        "treemap": PowerBIVisualType.TREEMAP,
        "scatter": PowerBIVisualType.SCATTER_CHART,
        "bubble": PowerBIVisualType.SCATTER_CHART,
        "heatmap": PowerBIVisualType.MATRIX,
        "kpi": PowerBIVisualType.KPI,
        "gauge": PowerBIVisualType.GAUGE,
        "card": PowerBIVisualType.CARD,
        "table": PowerBIVisualType.TABLE,
        "matrix": PowerBIVisualType.MATRIX,
    }
    
    # Data role mapping for different visual types
    # Defines which shelves map to which data roles in Power BI
    VISUAL_DATA_ROLES: Dict[PowerBIVisualType, Dict[str, str]] = {
        PowerBIVisualType.CLUSTERED_BAR: {
            "category": "Category",
            "values": "Values",
            "legend": "Series",
        },
        PowerBIVisualType.STACKED_BAR: {
            "category": "Category",
            "values": "Values",
            "legend": "Series",
        },
        PowerBIVisualType.CLUSTERED_COLUMN: {
            "category": "Category",
            "values": "Values",
            "legend": "Series",
        },
        PowerBIVisualType.STACKED_COLUMN: {
            "category": "Category",
            "values": "Values",
            "legend": "Series",
        },
        PowerBIVisualType.LINE_CHART: {
            "category": "Category",
            "values": "Y",
            "legend": "Series",
        },
        PowerBIVisualType.AREA_CHART: {
            "category": "Category",
            "values": "Y",
            "legend": "Series",
        },
        PowerBIVisualType.STACKED_AREA: {
            "category": "Category",
            "values": "Y",
            "legend": "Series",
        },
        PowerBIVisualType.PIE_CHART: {
            "category": "Legend",
            "values": "Values",
        },
        PowerBIVisualType.DONUT_CHART: {
            "category": "Legend",
            "values": "Values",
        },
        PowerBIVisualType.SCATTER_CHART: {
            "category": "Details",
            "values": "Y",
            "extra_values": "X",
            "legend": "Legend",
            "size": "Size",
        },
        PowerBIVisualType.MAP: {
            "category": "Location",
            "values": "Size",
            "legend": "Legend",
        },
        PowerBIVisualType.FILLED_MAP: {
            "category": "Location",
            "values": "Values",
            "legend": "Legend",
        },
        PowerBIVisualType.TABLE: {
            "category": "Values",
        },
        PowerBIVisualType.MATRIX: {
            "rows": "Rows",
            "columns": "Columns",
            "values": "Values",
        },
        PowerBIVisualType.TREEMAP: {
            "category": "Group",
            "values": "Values",
            "legend": "Details",
        },
    }
    
    # Custom visual recommendations (using custom_visuals module)
    CUSTOM_VISUALS: Dict[MarkType, Dict[str, str]] = {
        MarkType.GANTT: {
            "visual_id": "GanttChartbyMAQ",
            "name": "Gantt Chart by MAQ Software",
            "url": "https://appsource.microsoft.com/en-us/product/power-bi-visuals/wa104380765"
        },
    }
    
    def __init__(self, default_table_name: str = "Data", table_name_map: Dict[str, str] = None):
        """
        Initialize the visual mapper.
        
        Args:
            default_table_name: Default table name for field references
            table_name_map: Mapping from Tableau datasource names to Power BI table names
        """
        self.default_table = default_table_name
        self.table_name_map = table_name_map or {}
    
    def set_table_name(self, datasource_name: str, table_name: str) -> None:
        """Set the table name mapping for a datasource."""
        self.table_name_map[datasource_name] = table_name
    
    def get_table_name(self, datasource_name: str = None) -> str:
        """Get the Power BI table name for a datasource."""
        if datasource_name and datasource_name in self.table_name_map:
            return self.table_name_map[datasource_name]
        return self.default_table
    
    def map_worksheet(self, worksheet: TableauWorksheet, workbook: Optional[TableauWorkbook] = None) -> VisualMappingResult:
        """
        Map a Tableau worksheet to a Power BI visual.
        
        Args:
            worksheet: Tableau worksheet to map
            workbook: Optional workbook for field metadata lookup
            
        Returns:
            VisualMappingResult with mapped visual and metadata
        """
        notes = []
        unmapped = []
        
        # Determine visual type from mark type
        mark_type = worksheet.mark.mark_type
        visual_type, base_confidence = self.MARK_TO_VISUAL.get(
            mark_type, 
            (PowerBIVisualType.TABLE, MappingConfidence.PARTIAL)
        )
        
        # Refine visual type based on data configuration
        visual_type = self._refine_visual_type(worksheet, visual_type, notes)
        
        # Check for dual axis (not directly supported)
        if self._has_dual_axis(worksheet):
            visual_type = PowerBIVisualType.COMBO_CHART
            notes.append("Dual axis converted to combo chart - verify axis scaling")
        
        # Build the Power BI visual
        visual = PowerBIVisual(
            visual_type=visual_type,
            name=worksheet.name,
            title=worksheet.title or worksheet.name,
            source_tableau_worksheet=worksheet.name,
        )
        
        # Map data bindings
        visual = self._map_data_bindings(worksheet, visual, notes, unmapped, workbook)
        
        # Map filters
        visual = self._map_filters(worksheet, visual, notes)
        
        # Check for custom visual requirement
        requires_custom = False
        custom_visual_id = None
        
        if mark_type in self.CUSTOM_VISUALS:
            requires_custom = True
            custom_info = self.CUSTOM_VISUALS[mark_type]
            custom_visual_id = custom_info["visual_id"]
            notes.append(f"Consider using custom visual: {custom_info['name']}")
        
        # Determine final confidence
        confidence = base_confidence
        if unmapped:
            if confidence == MappingConfidence.EXACT:
                confidence = MappingConfidence.GOOD
            elif confidence == MappingConfidence.GOOD:
                confidence = MappingConfidence.PARTIAL
        
        return VisualMappingResult(
            powerbi_visual=visual,
            confidence=confidence,
            notes=notes,
            requires_custom_visual=requires_custom,
            custom_visual_id=custom_visual_id,
            unmapped_features=unmapped,
        )
    
    def _refine_visual_type(self, worksheet: TableauWorksheet, 
                            initial_type: PowerBIVisualType,
                            notes: List[str]) -> PowerBIVisualType:
        """
        Refine visual type based on data configuration and worksheet name patterns.
        Enhanced with better chart type detection.
        """
        rows = worksheet.rows
        cols = worksheet.columns
        has_color = worksheet.color_field is not None
        has_size = worksheet.size_field is not None
        ws_name_lower = (worksheet.name or "").lower()
        
        # First check worksheet name for visual type hints
        for pattern, visual_type in self.VISUAL_NAME_PATTERNS.items():
            if pattern in ws_name_lower:
                notes.append(f"Visual type inferred from worksheet name pattern: {pattern}")
                return visual_type
        
        # Check for KPI-like single value FIRST (before bar chart logic)
        if len(rows) == 0 and len(cols) == 1 and cols[0].aggregation != AggregationType.NONE:
            return PowerBIVisualType.CARD
        
        # Also check: single measure on rows, nothing on cols
        if len(cols) == 0 and len(rows) == 1 and rows[0].aggregation != AggregationType.NONE:
            return PowerBIVisualType.CARD
        
        # Detect bubble chart (scatter with size)
        if initial_type == PowerBIVisualType.SCATTER_CHART and has_size:
            notes.append("Size field detected - creating bubble chart")
            return PowerBIVisualType.SCATTER_CHART  # Scatter with size = bubble
        
        # Detect line chart with area (stacked area)
        if initial_type == PowerBIVisualType.AREA_CHART and has_color:
            notes.append("Color field with area - creating stacked area")
            return PowerBIVisualType.STACKED_AREA
        
        # Bar chart orientation
        if initial_type in [PowerBIVisualType.CLUSTERED_BAR, PowerBIVisualType.CLUSTERED_COLUMN]:
            # In Tableau, bars on rows means horizontal (bar), bars on columns means vertical (column)
            has_measure_on_cols = any(
                m.aggregation != AggregationType.NONE 
                for m in cols
            )
            
            # Check for stacked chart pattern
            if has_color:
                if has_measure_on_cols:
                    notes.append("Color field detected - using stacked column chart")
                    return PowerBIVisualType.STACKED_COLUMN
                else:
                    notes.append("Color field detected - using stacked bar chart")
                    return PowerBIVisualType.STACKED_BAR
            
            if has_measure_on_cols:
                return PowerBIVisualType.CLUSTERED_COLUMN
            else:
                return PowerBIVisualType.CLUSTERED_BAR
        
        # Check for matrix layout
        if len(rows) > 1 and len(cols) > 1:
            # Multiple dimensions on both axes suggests matrix
            has_dim_on_both = (
                any(m.aggregation == AggregationType.NONE for m in rows) and
                any(m.aggregation == AggregationType.NONE for m in cols)
            )
            if has_dim_on_both:
                notes.append("Matrix/pivot layout detected")
                return PowerBIVisualType.MATRIX
        
        # Check for combo chart pattern (line + bar)
        if initial_type == PowerBIVisualType.LINE_CHART:
            num_measures = sum(1 for m in rows + cols if m.aggregation != AggregationType.NONE)
            if num_measures > 1:
                notes.append("Multiple measures detected - consider combo chart")
        
        return initial_type
    
    def _has_dual_axis(self, worksheet: TableauWorksheet) -> bool:
        """Check if worksheet uses dual axis (multiple measure axes)."""
        # Count measures on columns
        measure_count = sum(
            1 for m in worksheet.columns 
            if m.aggregation != AggregationType.NONE
        )
        return measure_count > 1
    
    def _map_data_bindings(self, worksheet: TableauWorksheet, 
                           visual: PowerBIVisual,
                           notes: List[str],
                           unmapped: List[str],
                           workbook: Optional[TableauWorkbook] = None) -> PowerBIVisual:
        """Map Tableau data bindings to Power BI visual bindings."""
        
        # Get the appropriate table name
        table_name = self.get_table_name(worksheet.datasource_name)
        
        # Helper to check if a field is a measure
        def is_measure(m):
            if m.aggregation != AggregationType.NONE:
                return True
            if workbook and worksheet.datasource_name:
                ds = workbook.get_datasource(worksheet.datasource_name)
                if ds:
                    # Try looking up by clean name
                    field = ds.get_field(m.field) or ds.get_calculated_field(m.field)
                    if field and field.role == "measure":
                        return True
            return False

        # Separate dimensions and measures from rows and columns
        row_dims = [m for m in worksheet.rows if not is_measure(m)]
        row_meass = [m for m in worksheet.rows if is_measure(m)]
        col_dims = [m for m in worksheet.columns if not is_measure(m)]
        col_meass = [m for m in worksheet.columns if is_measure(m)]
        
        # Logic for mapping based on visual type
        if visual.visual_type in [PowerBIVisualType.CLUSTERED_BAR, PowerBIVisualType.STACKED_BAR]:
            # Bar chart: rows are usually categories, columns are values
            for m in row_dims + col_dims:
                visual.category_fields.append(self._create_data_field(m, table_name))
            for m in col_meass + row_meass:
                visual.value_fields.append(self._create_data_field(m, table_name))
                    
        elif visual.visual_type in [PowerBIVisualType.CLUSTERED_COLUMN, PowerBIVisualType.STACKED_COLUMN, 
                                  PowerBIVisualType.LINE_CHART, PowerBIVisualType.AREA_CHART, 
                                  PowerBIVisualType.STACKED_AREA]:
            # Column/Line/Area chart: columns are usually categories, rows are values
            for m in col_dims + row_dims:
                visual.category_fields.append(self._create_data_field(m, table_name))
            for m in row_meass + col_meass:
                visual.value_fields.append(self._create_data_field(m, table_name))

        elif visual.visual_type in [PowerBIVisualType.PIE_CHART, PowerBIVisualType.DONUT_CHART]:
            # Pie/Donut
            for m in row_dims + col_dims:
                visual.category_fields.append(self._create_data_field(m, table_name))
            for m in row_meass + col_meass:
                visual.value_fields.append(self._create_data_field(m, table_name))

        elif visual.visual_type == PowerBIVisualType.SCATTER_CHART:
            # Scatter: first measure to X, second to Y
            all_meass = col_meass + row_meass
            if len(all_meass) >= 1:
                visual.category_fields.append(self._create_data_field(all_meass[0], table_name))
            if len(all_meass) >= 2:
                visual.value_fields.append(self._create_data_field(all_meass[1], table_name))
            for m in row_dims + col_dims:
                visual.tooltip_fields.append(self._create_data_field(m, table_name))

        else:
            # Default: all dimensions to category, all measures to values
            for m in row_dims + col_dims:
                visual.category_fields.append(self._create_data_field(m, table_name))
            for m in row_meass + col_meass:
                visual.value_fields.append(self._create_data_field(m, table_name))
        
        # If still empty but we have fields, just put everything in Category as a last resort
        if not visual.category_fields and not visual.value_fields:
            for m in worksheet.rows + worksheet.columns:
                visual.category_fields.append(self._create_data_field(m, table_name))

        # Map color field to legend
        if worksheet.color_field:
            visual.legend_field = self._create_data_field(worksheet.color_field, table_name)
        
        # Map tooltip fields
        for mapping in worksheet.tooltip_fields:
            visual.tooltip_fields.append(self._create_data_field(mapping, table_name))
        
        return visual
    
    def _create_data_field(self, mapping: FieldMapping, table_name: str = None) -> VisualDataField:
        """Create a Power BI data field from a Tableau field mapping."""
        # Map aggregation
        agg_map = {
            AggregationType.SUM: "sum",
            AggregationType.AVG: "average",
            AggregationType.COUNT: "count",
            AggregationType.COUNTD: "distinctCount",
            AggregationType.MIN: "min",
            AggregationType.MAX: "max",
            AggregationType.MEDIAN: "median",
            AggregationType.ATTR: "first",  # ATTR becomes FIRST in DAX
            AggregationType.NONE: None,
        }
        
        # Clean field name (remove brackets if present)
        field_name = mapping.field
        if field_name.startswith('[') and field_name.endswith(']'):
            field_name = field_name[1:-1]
        
        return VisualDataField(
            table=table_name or self.default_table,
            column=field_name,
            aggregation=agg_map.get(mapping.aggregation),
        )
    
    def _map_filters(self, worksheet: TableauWorksheet, 
                     visual: PowerBIVisual,
                     notes: List[str]) -> PowerBIVisual:
        """Map Tableau filters to Power BI visual filters."""
        for filter_ in worksheet.filters:
            pbi_filter = {
                "target": {
                    "table": self.default_table,
                    "column": filter_.field,
                },
                "filterType": "categorical" if filter_.filter_type == "categorical" else "advanced",
            }
            
            if filter_.values:
                pbi_filter["operator"] = "In"
                pbi_filter["values"] = filter_.values
            
            if filter_.range_min is not None or filter_.range_max is not None:
                pbi_filter["filterType"] = "advanced"
                pbi_filter["operator"] = "Between"
                pbi_filter["lowValue"] = filter_.range_min
                pbi_filter["highValue"] = filter_.range_max
            
            visual.filters.append(pbi_filter)
        
        if worksheet.filters:
            notes.append(f"Mapped {len(worksheet.filters)} filters - verify filter behavior")
        
        return visual
    
    def map_dashboard_to_page(self, dashboard, worksheets: Dict[str, TableauWorksheet], workbook: Optional[TableauWorkbook] = None) -> PowerBIPage:
        """
        Map a Tableau dashboard to a Power BI page.
        
        Args:
            dashboard: Tableau dashboard
            worksheets: Dictionary of worksheet name to worksheet
            workbook: Optional workbook for context
            
        Returns:
            PowerBIPage with mapped visuals
        """
        # Sanitize page name (remove special characters)
        page_name = dashboard.name.replace(" ", "_")
        page_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in page_name)
        
        page = PowerBIPage(
            name=page_name,
            display_name=dashboard.title or dashboard.name,
            width=dashboard.width,
            height=dashboard.height,
            source_tableau_dashboard=dashboard.name,
        )
        
        # Track z-order for visuals
        z_order = 0
        
        # Map each dashboard object
        for obj in dashboard.objects:
            if obj.object_type == "worksheet" and obj.worksheet_name:
                worksheet = worksheets.get(obj.worksheet_name)
                if worksheet:
                    # Set table name from worksheet datasource
                    if worksheet.datasource_name:
                        table_name = self.get_table_name(worksheet.datasource_name)
                    else:
                        table_name = self.default_table
                    
                    result = self.map_worksheet(worksheet, workbook)
                    visual = result.powerbi_visual
                    
                    # Set position from dashboard layout
                    visual.x = obj.x
                    visual.y = obj.y
                    visual.width = max(obj.width, 100)  # Minimum width
                    visual.height = max(obj.height, 100)  # Minimum height
                    visual.z = z_order
                    z_order += 1000
                    
                    # Store mapping notes in visual config
                    if result.notes:
                        visual.translation_notes = result.notes
                    
                    page.visuals.append(visual)
            
            elif obj.object_type == "text":
                # Text objects become textbox visuals
                text_visual = PowerBIVisual(
                    visual_type=PowerBIVisualType.TEXT_BOX,
                    name=f"text_{obj.name or 'unnamed'}",
                    title=obj.name or "Text",
                    x=obj.x,
                    y=obj.y,
                    width=max(obj.width, 50),
                    height=max(obj.height, 30),
                    z=z_order,
                )
                z_order += 1000
                page.visuals.append(text_visual)
            
            elif obj.object_type == "image":
                # Image objects
                img_visual = PowerBIVisual(
                    visual_type=PowerBIVisualType.IMAGE,
                    name=f"image_{obj.name or 'unnamed'}",
                    title=obj.name or "Image",
                    x=obj.x,
                    y=obj.y,
                    width=max(obj.width, 50),
                    height=max(obj.height, 50),
                    z=z_order,
                )
                z_order += 1000
                page.visuals.append(img_visual)
            
            elif obj.object_type == "blank":
                # Skip blank objects (spacing elements)
                pass
            
            elif obj.object_type == "web":
                # Web page objects - not directly supported
                # Could be replaced with a shape or image placeholder
                pass
        
        return page
    
    def map_worksheet_standalone(self, worksheet: TableauWorksheet, 
                                  page_width: int = 1280, 
                                  page_height: int = 720) -> PowerBIPage:
        """
        Map a single worksheet to a standalone Power BI page.
        
        Args:
            worksheet: Tableau worksheet
            page_width: Page width
            page_height: Page height
            
        Returns:
            PowerBIPage with single visual
        """
        page_name = worksheet.name.replace(" ", "_")
        page_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in page_name)
        
        page = PowerBIPage(
            name=page_name,
            display_name=worksheet.title or worksheet.name,
            width=page_width,
            height=page_height,
            source_tableau_worksheet=worksheet.name,
        )
        
        result = self.map_worksheet(worksheet, None)
        visual = result.powerbi_visual
        
        # Center the visual on the page with padding
        padding = 20
        visual.x = padding
        visual.y = padding
        visual.width = page_width - (padding * 2)
        visual.height = page_height - (padding * 2)
        
        page.visuals.append(visual)
        
        return page
    
    def get_visual_type_for_mark(self, mark_type: MarkType) -> Tuple[str, str]:
        """
        Get the recommended Power BI visual type for a Tableau mark type.
        
        Returns:
            Tuple of (visual_type_name, notes)
        """
        mapping = self.MARK_TO_VISUAL.get(mark_type)
        if mapping:
            visual_type, confidence = mapping
            return (
                visual_type.value,
                f"Confidence: {confidence.value}"
            )
        return ("table", "No direct mapping - defaulting to table")
    
    @staticmethod
    def get_all_mappings() -> Dict[str, Dict[str, Any]]:
        """Get all visual type mappings for documentation."""
        mappings = {}
        for mark_type, (pbi_type, confidence) in VisualMapper.MARK_TO_VISUAL.items():
            custom_info = VisualMapper.CUSTOM_VISUALS.get(mark_type)
            mappings[mark_type.value] = {
                "powerbi_visual": pbi_type.value,
                "confidence": confidence.value,
                "custom_visual": custom_info["name"] if custom_info else None,
            }
        return mappings
