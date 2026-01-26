"""
Integration tests for the full conversion pipeline.
"""

import pytest
import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestParserIntegration:
    """Integration tests for the parser."""
    
    def test_parser_import(self):
        """Test that parser can be imported."""
        from parsers.twbx_parser import TWBXParser
        assert TWBXParser is not None
    
    def test_formula_parser_import(self):
        """Test that formula parser can be imported."""
        from parsers.formula_parser import TableauFormulaParser
        assert TableauFormulaParser is not None


class TestTranslatorIntegration:
    """Integration tests for translators."""
    
    def test_formula_translator_import(self):
        """Test that formula translator can be imported."""
        from translators.formula_translator import FormulaTranslator
        assert FormulaTranslator is not None
    
    def test_visual_mapper_import(self):
        """Test that visual mapper can be imported."""
        from translators.visual_mapper import VisualMapper
        assert VisualMapper is not None
    
    def test_extended_mappings_import(self):
        """Test that extended mappings can be imported."""
        from translators.extended_mappings import get_all_mappings, get_direct_mappings
        
        all_mappings = get_all_mappings()
        direct = get_direct_mappings()
        
        assert len(all_mappings) > 50, "Should have many function mappings"
        assert len(direct) > 20, "Should have many direct mappings"
    
    def test_custom_visuals_import(self):
        """Test that custom visuals can be imported."""
        from translators.custom_visuals import custom_visual_registry, CUSTOM_VISUALS
        
        assert len(CUSTOM_VISUALS) > 10, "Should have many custom visuals"
        
        gantt = custom_visual_registry.find_for_tableau("gantt")
        assert len(gantt) > 0, "Should find Gantt replacements"
    
    def test_connection_templates_import(self):
        """Test that connection templates can be imported."""
        from translators.connection_templates import (
            connection_builder, ConnectionType, CONNECTION_TEMPLATES
        )
        
        assert len(CONNECTION_TEMPLATES) > 5, "Should have many connection templates"
        
        sql_template = connection_builder.get_template(ConnectionType.SQL_SERVER)
        assert sql_template is not None
        assert "server" in sql_template.required_params


class TestGeneratorIntegration:
    """Integration tests for generators."""
    
    def test_pbir_generator_import(self):
        """Test that PBIR generator can be imported."""
        from generators.pbir_generator import PBIRGenerator
        assert PBIRGenerator is not None
    
    def test_semantic_model_generator_import(self):
        """Test that semantic model generator can be imported."""
        from generators.semantic_model_generator import SemanticModelGenerator
        assert SemanticModelGenerator is not None


class TestModelsIntegration:
    """Integration tests for models."""
    
    def test_tableau_models_import(self):
        """Test that Tableau models can be imported."""
        from models.tableau_models import (
            TableauWorkbook, TableauDataSource, TableauCalculatedField
        )
        
        assert TableauWorkbook is not None
        assert TableauDataSource is not None
        assert TableauCalculatedField is not None
    
    def test_powerbi_models_import(self):
        """Test that Power BI models can be imported."""
        from models.powerbi_models import (
            PowerBIReport, PowerBIPage, PowerBIMeasure
        )
        
        assert PowerBIReport is not None
        assert PowerBIPage is not None
        assert PowerBIMeasure is not None
    
    def test_create_tableau_workbook(self):
        """Test creating a Tableau workbook model."""
        from models.tableau_models import (
            TableauWorkbook, TableauDataSource, TableauCalculatedField,
            TableauWorksheet, TableauMark, MarkType, CalculationType
        )
        
        calc = TableauCalculatedField(
            name="Total Sales",
            formula="SUM([Sales])",
            calculation_type=CalculationType.AGGREGATE
        )
        
        ds = TableauDataSource(
            name="Sample Data",
            calculated_fields=[calc]
        )
        
        ws = TableauWorksheet(
            name="Sales View",
            mark=TableauMark(mark_type=MarkType.BAR)
        )
        
        wb = TableauWorkbook(
            name="Test Workbook",
            datasources=[ds],
            worksheets=[ws]
        )
        
        assert wb.name == "Test Workbook"
        assert len(wb.datasources) == 1
        assert len(wb.worksheets) == 1
        assert wb.total_calculated_fields == 1
    
    def test_create_powerbi_report(self):
        """Test creating a Power BI report model."""
        from models.powerbi_models import (
            PowerBIReport, PowerBIPage, PowerBIVisual, PowerBIMeasure,
            PowerBIVisualType
        )
        
        measure = PowerBIMeasure(
            name="Total Sales",
            expression="SUM([Sales])"
        )
        
        visual = PowerBIVisual(
            visual_type=PowerBIVisualType.CLUSTERED_BAR,
            title="Sales by Category"
        )
        
        page = PowerBIPage(
            name="Page1",
            display_name="Sales Dashboard",
            visuals=[visual]
        )
        
        report = PowerBIReport(
            name="Test Report",
            pages=[page],
            measures=[measure]
        )
        
        assert report.name == "Test Report"
        assert len(report.pages) == 1
        assert len(report.get_all_measures()) == 1


class TestValidationIntegration:
    """Integration tests for validation."""
    
    def test_validation_report_import(self):
        """Test that validation report can be imported."""
        from validation_report import ValidationReportGenerator, ValidationReport
        
        assert ValidationReportGenerator is not None
        assert ValidationReport is not None


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""
    
    def test_formula_translation_workflow(self):
        """Test the formula translation workflow."""
        from models.tableau_models import TableauCalculatedField, CalculationType
        from translators.formula_translator import FormulaTranslator
        
        translator = FormulaTranslator(use_genai=False)
        
        # Test simple aggregation
        calc = TableauCalculatedField(
            name="Total Sales",
            formula="SUM([Sales])",
            calculation_type=CalculationType.AGGREGATE
        )
        
        result = translator.translate(calc)
        measure = translator.to_measure(calc, result)
        
        assert "SUM" in result.dax_expression
        assert measure.name == "Total Sales"
    
    def test_visual_mapping_workflow(self):
        """Test the visual mapping workflow."""
        from models.tableau_models import (
            TableauWorksheet, TableauMark, MarkType, FieldMapping, AggregationType
        )
        from translators.visual_mapper import VisualMapper
        
        mapper = VisualMapper()
        
        worksheet = TableauWorksheet(
            name="Test Chart",
            mark=TableauMark(mark_type=MarkType.BAR),
            rows=[FieldMapping(field="Category", shelf="rows")],
            columns=[FieldMapping(field="Sales", shelf="cols", aggregation=AggregationType.SUM)]
        )
        
        result = mapper.map_worksheet(worksheet)
        
        assert result.powerbi_visual is not None
        assert result.powerbi_visual.source_tableau_worksheet == "Test Chart"
    
    def test_pbir_generation_workflow(self):
        """Test PBIR generation workflow."""
        from models.powerbi_models import PowerBIReport, PowerBIPage, PowerBIVisual, PowerBIVisualType
        from generators.pbir_generator import PBIRGenerator
        
        with tempfile.TemporaryDirectory() as tmpdir:
            report = PowerBIReport(
                name="Test Report",
                pages=[
                    PowerBIPage(
                        name="Page1",
                        display_name="Test Page",
                        visuals=[
                            PowerBIVisual(
                                visual_type=PowerBIVisualType.CLUSTERED_BAR,
                                title="Test Chart"
                            )
                        ]
                    )
                ]
            )
            
            generator = PBIRGenerator(tmpdir)
            output_path = generator.generate(report)
            
            assert output_path.exists()
            # Check that the report folder was created (name may have space or underscore)
            report_dirs = list(output_path.glob("*.Report"))
            assert len(report_dirs) == 1, f"Expected 1 report dir, found: {list(output_path.iterdir())}"


class TestExtendedMappings:
    """Tests for extended function mappings."""
    
    def test_lod_patterns(self):
        """Test LOD expression patterns."""
        from translators.extended_mappings import LOD_PATTERNS
        
        assert "FIXED" in LOD_PATTERNS
        assert "INCLUDE" in LOD_PATTERNS
        assert "EXCLUDE" in LOD_PATTERNS
        
        fixed = LOD_PATTERNS["FIXED"]
        assert "ALLEXCEPT" in fixed["pattern"]
    
    def test_table_calc_mappings(self):
        """Test table calculation mappings."""
        from translators.extended_mappings import TABLE_CALC_MAPPINGS
        
        assert "RUNNING_SUM" in TABLE_CALC_MAPPINGS
        assert "WINDOW_AVG" in TABLE_CALC_MAPPINGS
        assert "RANK" in TABLE_CALC_MAPPINGS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
