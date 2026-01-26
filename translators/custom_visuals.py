"""
Custom Visual Support for Power BI.

This module provides mappings for Tableau visuals that require
custom visuals from the Power BI marketplace (AppSource).
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from models.tableau_models import MarkType


class VisualCategory(Enum):
    """Categories of custom visuals."""
    CHARTING = "Charting"
    KPI = "KPI & Metrics"
    MAPS = "Maps"
    ADVANCED = "Advanced Analytics"
    INFOGRAPHIC = "Infographic"
    TIME = "Time-based"
    TABLES = "Tables & Matrices"
    FILTERS = "Filters & Slicers"


@dataclass
class CustomVisual:
    """Represents a Power BI custom visual from AppSource."""
    id: str
    name: str
    publisher: str
    category: VisualCategory
    appsource_url: str
    description: str = ""
    
    # Mapping info
    tableau_equivalents: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    
    # Installation
    is_certified: bool = False
    is_free: bool = True
    
    # Data requirements
    min_category_fields: int = 0
    min_value_fields: int = 0
    supports_drill_down: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "publisher": self.publisher,
            "category": self.category.value,
            "appsource_url": self.appsource_url,
            "description": self.description,
            "tableau_equivalents": self.tableau_equivalents,
            "capabilities": self.capabilities,
            "is_certified": self.is_certified,
            "is_free": self.is_free,
        }


# =============================================================================
# CUSTOM VISUAL REGISTRY
# =============================================================================

CUSTOM_VISUALS: Dict[str, CustomVisual] = {
    # Gantt Charts
    "gantt_maq": CustomVisual(
        id="GanttChartbyMAQ",
        name="Gantt Chart by MAQ Software",
        publisher="MAQ Software",
        category=VisualCategory.TIME,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/wa104380765",
        description="Full-featured Gantt chart with dependencies, milestones, and resource allocation",
        tableau_equivalents=["Gantt Bar", "Gantt Chart"],
        capabilities=["task_dependencies", "milestones", "resources", "progress_tracking"],
        is_certified=True,
        is_free=True,
        min_category_fields=1,
        min_value_fields=2,
    ),
    "gantt_xvz": CustomVisual(
        id="GanttChartbyxViz",
        name="Gantt Chart by xViz",
        publisher="xViz",
        category=VisualCategory.TIME,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/xviz.ganttchartbyxviz",
        description="Advanced Gantt with conditional formatting and hierarchy support",
        tableau_equivalents=["Gantt Bar", "Gantt Chart"],
        capabilities=["conditional_formatting", "hierarchy", "tooltips"],
        is_certified=True,
        is_free=False,
    ),
    
    # Bullet Charts
    "bullet_okviz": CustomVisual(
        id="BulletChartbyOKViz",
        name="Bullet Chart by OKViz",
        publisher="OKViz",
        category=VisualCategory.KPI,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/wa104380755",
        description="Bullet chart for comparing actual vs target values",
        tableau_equivalents=["Bullet Graph"],
        capabilities=["target_comparison", "qualitative_ranges", "orientation"],
        is_certified=True,
        is_free=True,
        min_value_fields=1,
    ),
    
    # Waterfall Charts (Enhanced)
    "waterfall_xvz": CustomVisual(
        id="WaterfallChartbyxViz",
        name="Waterfall Chart by xViz",
        publisher="xViz",
        category=VisualCategory.CHARTING,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/xviz.waterfallchartbyxviz",
        description="Enhanced waterfall with breakdown and variance analysis",
        tableau_equivalents=["Waterfall Chart"],
        capabilities=["variance_analysis", "breakdown", "subtotals"],
        is_certified=True,
    ),
    
    # Sankey Diagrams
    "sankey": CustomVisual(
        id="SankeyChart",
        name="Sankey Chart",
        publisher="Microsoft",
        category=VisualCategory.ADVANCED,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/wa104380777",
        description="Flow diagram showing magnitude of flow between nodes",
        tableau_equivalents=["Sankey Diagram"],
        capabilities=["flow_visualization", "node_sizing", "path_highlighting"],
        is_certified=True,
        is_free=True,
        min_category_fields=2,
        min_value_fields=1,
    ),
    
    # Chord Diagrams
    "chord": CustomVisual(
        id="ChordChart",
        name="Chord Chart",
        publisher="Microsoft",
        category=VisualCategory.ADVANCED,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/wa104380761",
        description="Circular diagram showing relationships between entities",
        tableau_equivalents=["Chord Diagram"],
        capabilities=["relationship_visualization", "arc_sizing"],
        is_certified=True,
        is_free=True,
    ),
    
    # Radar/Spider Charts
    "radar": CustomVisual(
        id="RadarChart",
        name="Radar Chart",
        publisher="Microsoft",
        category=VisualCategory.CHARTING,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/wa104380771",
        description="Multi-dimensional data visualization on radial axes",
        tableau_equivalents=["Radar Chart", "Spider Chart", "Polygon Chart"],
        capabilities=["multi_axis", "area_fill", "multiple_series"],
        is_certified=True,
        is_free=True,
        min_category_fields=1,
        min_value_fields=3,
    ),
    
    # Sunburst Charts
    "sunburst": CustomVisual(
        id="Sunburst",
        name="Sunburst Chart",
        publisher="Microsoft",
        category=VisualCategory.CHARTING,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/wa104380767",
        description="Hierarchical data visualization with concentric rings",
        tableau_equivalents=["Sunburst", "Hierarchical Pie"],
        capabilities=["hierarchy", "drill_down", "proportional_sizing"],
        is_certified=True,
        is_free=True,
        supports_drill_down=True,
    ),
    
    # Word Cloud
    "wordcloud": CustomVisual(
        id="WordCloud",
        name="Word Cloud",
        publisher="Microsoft",
        category=VisualCategory.INFOGRAPHIC,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/wa104380752",
        description="Text visualization with word size based on frequency/value",
        tableau_equivalents=["Word Cloud", "Tag Cloud"],
        capabilities=["text_sizing", "color_coding", "rotation"],
        is_certified=True,
        is_free=True,
        min_category_fields=1,
    ),
    
    # Box and Whisker
    "boxwhisker": CustomVisual(
        id="BoxandWhiskerChart",
        name="Box and Whisker Chart",
        publisher="Microsoft",
        category=VisualCategory.ADVANCED,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/wa104380831",
        description="Statistical distribution visualization",
        tableau_equivalents=["Box Plot", "Box and Whisker"],
        capabilities=["quartiles", "outliers", "distribution"],
        is_certified=True,
        is_free=True,
        min_value_fields=1,
    ),
    
    # Histogram
    "histogram": CustomVisual(
        id="Histogram",
        name="Histogram Chart",
        publisher="Microsoft",
        category=VisualCategory.ADVANCED,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/wa104380776",
        description="Frequency distribution visualization",
        tableau_equivalents=["Histogram"],
        capabilities=["binning", "distribution", "frequency"],
        is_certified=True,
        is_free=True,
        min_value_fields=1,
    ),
    
    # Tornado Chart
    "tornado": CustomVisual(
        id="TornadoChart",
        name="Tornado Chart",
        publisher="Microsoft",
        category=VisualCategory.CHARTING,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/wa104380768",
        description="Side-by-side bar chart for comparison",
        tableau_equivalents=["Butterfly Chart", "Tornado Chart"],
        capabilities=["comparison", "diverging_bars"],
        is_certified=True,
        is_free=True,
        min_category_fields=1,
        min_value_fields=2,
    ),
    
    # Dot Plot
    "dotplot": CustomVisual(
        id="DotPlotbyMAQ",
        name="Dot Plot by MAQ Software",
        publisher="MAQ Software",
        category=VisualCategory.CHARTING,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/wa104381101",
        description="Lollipop/Dot plot chart",
        tableau_equivalents=["Lollipop Chart", "Dot Plot"],
        capabilities=["dots", "lines", "comparison"],
        is_certified=True,
        is_free=True,
    ),
    
    # Timeline
    "timeline": CustomVisual(
        id="TimelineSlicer",
        name="Timeline Slicer",
        publisher="Microsoft",
        category=VisualCategory.FILTERS,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/wa104380786",
        description="Interactive timeline for date filtering",
        tableau_equivalents=["Timeline Filter"],
        capabilities=["date_range", "brushing", "animation"],
        is_certified=True,
        is_free=True,
    ),
    
    # Play Axis (Animation)
    "playaxis": CustomVisual(
        id="PlayAxis",
        name="Play Axis",
        publisher="Microsoft",
        category=VisualCategory.TIME,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/wa104380981",
        description="Animate visualizations over time",
        tableau_equivalents=["Pages Shelf", "Animation"],
        capabilities=["animation", "playback", "time_series"],
        is_certified=True,
        is_free=True,
    ),
    
    # Calendar
    "calendar": CustomVisual(
        id="CalendarVisual",
        name="Calendar Visual",
        publisher="Various",
        category=VisualCategory.TIME,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/wa104381146",
        description="Calendar heatmap visualization",
        tableau_equivalents=["Calendar", "Calendar Heatmap"],
        capabilities=["heatmap", "date_selection", "monthly_view"],
        is_free=True,
    ),
    
    # Advanced Card
    "card_kpi": CustomVisual(
        id="AdvancedCardbyMAQ",
        name="Advanced Card by MAQ Software",
        publisher="MAQ Software",
        category=VisualCategory.KPI,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/wa104381499",
        description="Enhanced KPI card with formatting options",
        tableau_equivalents=["Big Number", "KPI Card"],
        capabilities=["conditional_formatting", "sparkline", "trends"],
        is_certified=True,
        is_free=True,
    ),
    
    # Sparklines
    "sparkline": CustomVisual(
        id="SparklinebyOKViz",
        name="Sparkline by OKViz",
        publisher="OKViz",
        category=VisualCategory.CHARTING,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/wa104380910",
        description="Inline trend visualizations",
        tableau_equivalents=["Sparklines", "Inline Charts"],
        capabilities=["inline_trends", "table_integration"],
        is_certified=True,
    ),
    
    # Pulse Chart (Timeline with events)
    "pulse": CustomVisual(
        id="PulseChart",
        name="Pulse Chart",
        publisher="Microsoft",
        category=VisualCategory.TIME,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/wa104381006",
        description="Animated line chart with event markers",
        tableau_equivalents=["Event Timeline", "Annotated Timeline"],
        capabilities=["events", "animation", "annotations"],
        is_certified=True,
        is_free=True,
    ),
    
    # Table Heatmap
    "tableheatmap": CustomVisual(
        id="TableHeatmapbyMAQ",
        name="Table Heatmap by MAQ Software",
        publisher="MAQ Software",
        category=VisualCategory.TABLES,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/wa104380818",
        description="Heatmap within table format",
        tableau_equivalents=["Highlight Table", "Heatmap"],
        capabilities=["color_gradient", "values", "categories"],
        is_certified=True,
        is_free=True,
    ),
    
    # Drill Down Donut
    "drilldown_donut": CustomVisual(
        id="DrillDownDonutChart",
        name="Drill Down Donut Chart",
        publisher="ZoomCharts",
        category=VisualCategory.CHARTING,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/wa104380858",
        description="Interactive donut with drill-down capability",
        tableau_equivalents=["Hierarchical Donut"],
        capabilities=["drill_down", "hierarchy", "interactivity"],
        is_free=False,
        supports_drill_down=True,
    ),
    
    # Globe Map
    "globe_map": CustomVisual(
        id="GlobeMap",
        name="Globe Map",
        publisher="Microsoft",
        category=VisualCategory.MAPS,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/wa104380799",
        description="3D globe visualization",
        tableau_equivalents=["Globe View"],
        capabilities=["3d", "rotation", "geocoding"],
        is_certified=True,
        is_free=True,
    ),
    
    # Flow Map
    "flow_map": CustomVisual(
        id="FlowMap",
        name="Flow Map",
        publisher="Various",
        category=VisualCategory.MAPS,
        appsource_url="https://appsource.microsoft.com/en-us/product/power-bi-visuals/wa104381061",
        description="Map showing movement/flow between locations",
        tableau_equivalents=["Flow Map", "Origin-Destination Map"],
        capabilities=["flows", "paths", "animation"],
    ),
}


# =============================================================================
# TABLEAU TO CUSTOM VISUAL MAPPING
# =============================================================================

TABLEAU_TO_CUSTOM_VISUAL: Dict[str, List[str]] = {
    # Tableau visualization -> List of recommended custom visual IDs
    "gantt": ["gantt_maq", "gantt_xvz"],
    "bullet_graph": ["bullet_okviz"],
    "sankey": ["sankey"],
    "chord": ["chord"],
    "radar": ["radar"],
    "spider": ["radar"],
    "sunburst": ["sunburst"],
    "word_cloud": ["wordcloud"],
    "box_plot": ["boxwhisker"],
    "histogram": ["histogram"],
    "butterfly": ["tornado"],
    "tornado": ["tornado"],
    "lollipop": ["dotplot"],
    "dot_plot": ["dotplot"],
    "timeline": ["timeline", "playaxis"],
    "calendar": ["calendar"],
    "sparklines": ["sparkline"],
    "heatmap_table": ["tableheatmap"],
    "globe": ["globe_map"],
    "flow_map": ["flow_map"],
    "pulse": ["pulse"],
}


class CustomVisualRegistry:
    """Registry for managing custom visual mappings."""
    
    def __init__(self):
        """Initialize the registry with default visuals."""
        self.visuals = CUSTOM_VISUALS.copy()
        self.tableau_mappings = TABLEAU_TO_CUSTOM_VISUAL.copy()
    
    def get_visual(self, visual_id: str) -> Optional[CustomVisual]:
        """Get a custom visual by ID."""
        return self.visuals.get(visual_id)
    
    def find_for_tableau(self, tableau_type: str) -> List[CustomVisual]:
        """Find custom visuals that can replace a Tableau visualization."""
        tableau_lower = tableau_type.lower().replace(" ", "_")
        visual_ids = self.tableau_mappings.get(tableau_lower, [])
        return [self.visuals[vid] for vid in visual_ids if vid in self.visuals]
    
    def find_for_mark_type(self, mark_type: MarkType) -> List[CustomVisual]:
        """Find custom visuals for a Tableau mark type."""
        mark_mappings = {
            MarkType.GANTT: ["gantt_maq", "gantt_xvz"],
            MarkType.POLYGON: ["flow_map"],
        }
        visual_ids = mark_mappings.get(mark_type, [])
        return [self.visuals[vid] for vid in visual_ids if vid in self.visuals]
    
    def get_certified_visuals(self) -> List[CustomVisual]:
        """Get all certified custom visuals."""
        return [v for v in self.visuals.values() if v.is_certified]
    
    def get_free_visuals(self) -> List[CustomVisual]:
        """Get all free custom visuals."""
        return [v for v in self.visuals.values() if v.is_free]
    
    def get_by_category(self, category: VisualCategory) -> List[CustomVisual]:
        """Get visuals by category."""
        return [v for v in self.visuals.values() if v.category == category]
    
    def register_visual(self, visual: CustomVisual) -> None:
        """Register a new custom visual."""
        self.visuals[visual.id] = visual
    
    def add_tableau_mapping(self, tableau_type: str, visual_ids: List[str]) -> None:
        """Add a Tableau to custom visual mapping."""
        self.tableau_mappings[tableau_type.lower()] = visual_ids
    
    def get_installation_report(self, needed_visuals: List[str]) -> Dict[str, Any]:
        """
        Generate a report of custom visuals that need to be installed.
        
        Args:
            needed_visuals: List of visual IDs that are needed
            
        Returns:
            Report with installation details
        """
        report = {
            "total": len(needed_visuals),
            "certified": 0,
            "free": 0,
            "paid": 0,
            "visuals": [],
        }
        
        for vid in needed_visuals:
            visual = self.visuals.get(vid)
            if visual:
                if visual.is_certified:
                    report["certified"] += 1
                if visual.is_free:
                    report["free"] += 1
                else:
                    report["paid"] += 1
                
                report["visuals"].append({
                    "id": visual.id,
                    "name": visual.name,
                    "publisher": visual.publisher,
                    "url": visual.appsource_url,
                    "is_certified": visual.is_certified,
                    "is_free": visual.is_free,
                })
        
        return report
    
    def export_all(self) -> List[Dict[str, Any]]:
        """Export all visuals as list of dictionaries."""
        return [v.to_dict() for v in self.visuals.values()]


# Global registry instance
custom_visual_registry = CustomVisualRegistry()


def get_recommended_visual(tableau_type: str) -> Optional[CustomVisual]:
    """
    Get the recommended custom visual for a Tableau visualization type.
    
    Args:
        tableau_type: Tableau visualization type name
        
    Returns:
        Best matching custom visual or None
    """
    visuals = custom_visual_registry.find_for_tableau(tableau_type)
    if visuals:
        # Prefer certified and free
        certified_free = [v for v in visuals if v.is_certified and v.is_free]
        if certified_free:
            return certified_free[0]
        certified = [v for v in visuals if v.is_certified]
        if certified:
            return certified[0]
        return visuals[0]
    return None
