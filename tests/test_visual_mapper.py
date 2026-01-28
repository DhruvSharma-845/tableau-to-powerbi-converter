"""
Unit tests for visual mapping (Tableau to Power BI).
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from translators.visual_mapper import VisualMapper, MappingConfidence
from models.tableau_models import (
    TableauWorksheet, TableauMark, MarkType, FieldMapping, 
    TableauFilter, AggregationType, TableauDashboard, DashboardObject
)
from models.powerbi_models import PowerBIVisualType


class TestMarkTypeMapping:
    """Tests for mark type to visual type mapping."""
    
    @pytest.fixture
    def mapper(self):
        return VisualMapper()
    
    def test_bar_to_bar(self, mapper):
        visual_type, notes = mapper.get_visual_type_for_mark(MarkType.BAR)
        assert "bar" in visual_type.lower()
    
    def test_line_to_line(self, mapper):
        visual_type, notes = mapper.get_visual_type_for_mark(MarkType.LINE)
        assert "line" in visual_type.lower()
    
    def test_area_to_area(self, mapper):
        visual_type, notes = mapper.get_visual_type_for_mark(MarkType.AREA)
        assert "area" in visual_type.lower()
    
    def test_pie_to_pie(self, mapper):
        visual_type, notes = mapper.get_visual_type_for_mark(MarkType.PIE)
        assert "pie" in visual_type.lower()
    
    def test_map_to_map(self, mapper):
        visual_type, notes = mapper.get_visual_type_for_mark(MarkType.MAP)
        assert "map" in visual_type.lower()
    
    def test_text_to_table(self, mapper):
        visual_type, notes = mapper.get_visual_type_for_mark(MarkType.TEXT)
        assert "table" in visual_type.lower()
    
    def test_gantt_needs_custom(self, mapper):
        mapping = VisualMapper.MARK_TO_VISUAL.get(MarkType.GANTT)
        assert mapping is not None
        assert mapping[1] == MappingConfidence.CUSTOM


class TestWorksheetMapping:
    """Tests for worksheet to visual mapping."""
    
    @pytest.fixture
    def mapper(self):
        return VisualMapper()
    
    def test_simple_bar_chart(self, mapper):
        worksheet = TableauWorksheet(
            name="Sales by Category",
            mark=TableauMark(mark_type=MarkType.BAR),
            rows=[FieldMapping(field="Category", shelf="rows")],
            columns=[FieldMapping(field="Sales", shelf="cols", aggregation=AggregationType.SUM)]
        )
        
        result = mapper.map_worksheet(worksheet)
        
        assert result.powerbi_visual is not None
        assert result.confidence in [MappingConfidence.EXACT, MappingConfidence.GOOD]
    
    def test_line_chart(self, mapper):
        worksheet = TableauWorksheet(
            name="Sales Trend",
            mark=TableauMark(mark_type=MarkType.LINE),
            rows=[FieldMapping(field="Sales", shelf="rows", aggregation=AggregationType.SUM)],
            columns=[FieldMapping(field="Date", shelf="cols")]
        )
        
        result = mapper.map_worksheet(worksheet)
        
        assert result.powerbi_visual.visual_type == PowerBIVisualType.LINE_CHART
    
    def test_pie_chart(self, mapper):
        worksheet = TableauWorksheet(
            name="Category Distribution",
            mark=TableauMark(mark_type=MarkType.PIE),
            rows=[FieldMapping(field="Category", shelf="rows")],
            columns=[FieldMapping(field="Sales", shelf="cols", aggregation=AggregationType.SUM)]
        )
        
        result = mapper.map_worksheet(worksheet)
        
        assert result.powerbi_visual.visual_type == PowerBIVisualType.PIE_CHART
    
    def test_color_field_mapping(self, mapper):
        worksheet = TableauWorksheet(
            name="Colored Chart",
            mark=TableauMark(mark_type=MarkType.BAR),
            rows=[FieldMapping(field="Category", shelf="rows")],
            columns=[FieldMapping(field="Sales", shelf="cols", aggregation=AggregationType.SUM)],
            color_field=FieldMapping(field="Region", shelf="color")
        )
        
        result = mapper.map_worksheet(worksheet)
        
        assert result.powerbi_visual.legend_field is not None
        assert result.powerbi_visual.legend_field.column == "Region"
    
    def test_filter_mapping(self, mapper):
        worksheet = TableauWorksheet(
            name="Filtered Chart",
            mark=TableauMark(mark_type=MarkType.BAR),
            rows=[FieldMapping(field="Category", shelf="rows")],
            columns=[FieldMapping(field="Sales", shelf="cols", aggregation=AggregationType.SUM)],
            filters=[
                TableauFilter(field="Region", filter_type="categorical", values=["East", "West"])
            ]
        )
        
        result = mapper.map_worksheet(worksheet)
        
        assert len(result.powerbi_visual.filters) > 0
    
    def test_kpi_card_detection(self, mapper):
        # Single measure, no dimensions = Card visual
        worksheet = TableauWorksheet(
            name="Total Sales Summary",
            mark=TableauMark(mark_type=MarkType.AUTOMATIC),
            rows=[],
            columns=[FieldMapping(field="Sales", shelf="cols", aggregation=AggregationType.SUM)]
        )
        
        result = mapper.map_worksheet(worksheet)
        
        assert result.powerbi_visual.visual_type == PowerBIVisualType.CARD


class TestDashboardMapping:
    """Tests for dashboard to page mapping."""
    
    @pytest.fixture
    def mapper(self):
        return VisualMapper()
    
    def test_dashboard_to_page(self, mapper):
        worksheet = TableauWorksheet(
            name="Sales Chart",
            mark=TableauMark(mark_type=MarkType.BAR),
            rows=[FieldMapping(field="Category", shelf="rows")],
            columns=[FieldMapping(field="Sales", shelf="cols", aggregation=AggregationType.SUM)]
        )
        
        dashboard = TableauDashboard(
            name="Sales Dashboard",
            title="Sales Overview",
            width=1200,
            height=800,
            objects=[
                DashboardObject(
                    object_type="worksheet",
                    worksheet_name="Sales Chart",
                    x=10, y=10, width=500, height=400
                )
            ]
        )
        
        page = mapper.map_dashboard_to_page(dashboard, {"Sales Chart": worksheet})
        
        assert page.name == "Sales_Dashboard"
        assert page.display_name == "Sales Overview"
        assert page.width == 1200
        assert page.height == 800
        assert len(page.visuals) == 1
    
    def test_dashboard_multiple_worksheets(self, mapper):
        ws1 = TableauWorksheet(
            name="Chart 1",
            mark=TableauMark(mark_type=MarkType.BAR),
            rows=[FieldMapping(field="Category", shelf="rows")],
            columns=[]
        )
        ws2 = TableauWorksheet(
            name="Chart 2",
            mark=TableauMark(mark_type=MarkType.LINE),
            rows=[FieldMapping(field="Date", shelf="rows")],
            columns=[]
        )
        
        dashboard = TableauDashboard(
            name="Multi Dashboard",
            objects=[
                DashboardObject(object_type="worksheet", worksheet_name="Chart 1", x=0, y=0, width=400, height=300),
                DashboardObject(object_type="worksheet", worksheet_name="Chart 2", x=400, y=0, width=400, height=300),
            ]
        )
        
        page = mapper.map_dashboard_to_page(dashboard, {"Chart 1": ws1, "Chart 2": ws2})
        
        assert len(page.visuals) == 2
    
    def test_dashboard_text_object(self, mapper):
        dashboard = TableauDashboard(
            name="Dashboard with Text",
            objects=[
                DashboardObject(object_type="text", name="Title", x=0, y=0, width=200, height=50),
            ]
        )
        
        page = mapper.map_dashboard_to_page(dashboard, {})
        
        assert len(page.visuals) == 1
        assert page.visuals[0].visual_type == PowerBIVisualType.TEXT_BOX


class TestMappingConfidence:
    """Tests for mapping confidence levels."""
    
    def test_exact_mappings(self):
        exact_marks = [MarkType.BAR, MarkType.LINE, MarkType.PIE]
        
        for mark in exact_marks:
            mapping = VisualMapper.MARK_TO_VISUAL.get(mark)
            assert mapping is not None
            assert mapping[1] == MappingConfidence.EXACT
    
    def test_partial_mappings(self):
        partial_marks = [MarkType.SQUARE, MarkType.POLYGON]
        
        for mark in partial_marks:
            mapping = VisualMapper.MARK_TO_VISUAL.get(mark)
            assert mapping is not None
            assert mapping[1] in [MappingConfidence.PARTIAL, MappingConfidence.GOOD]


class TestAllMappings:
    """Tests for getting all mappings."""
    
    def test_get_all_mappings(self):
        mappings = VisualMapper.get_all_mappings()
        
        assert len(mappings) > 0
        assert "bar" in mappings
        assert "powerbi_visual" in mappings["bar"]
        assert "confidence" in mappings["bar"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
