"""
Unit tests for formula translation (Tableau to DAX).
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from translators.formula_translator import FormulaTranslator, TranslationResult, TranslationConfidence
from models.tableau_models import TableauCalculatedField, CalculationType, DataType


class TestSimpleTranslations:
    """Tests for simple formula translations."""
    
    @pytest.fixture
    def translator(self):
        return FormulaTranslator(use_genai=False)
    
    def test_sum_aggregation(self, translator):
        calc = TableauCalculatedField(
            name="Total Sales",
            formula="SUM([Sales])",
            calculation_type=CalculationType.AGGREGATE
        )
        result = translator.translate(calc)
        assert "SUM" in result.dax_expression
        assert "[Sales]" in result.dax_expression
        assert result.confidence in [TranslationConfidence.HIGH, TranslationConfidence.MEDIUM]
    
    def test_avg_aggregation(self, translator):
        calc = TableauCalculatedField(
            name="Average Price",
            formula="AVG([Price])",
            calculation_type=CalculationType.AGGREGATE
        )
        result = translator.translate(calc)
        assert "AVERAGE" in result.dax_expression
        assert result.confidence in [TranslationConfidence.HIGH, TranslationConfidence.MEDIUM]
    
    def test_count_aggregation(self, translator):
        calc = TableauCalculatedField(
            name="Order Count",
            formula="COUNT([Order ID])",
            calculation_type=CalculationType.AGGREGATE
        )
        result = translator.translate(calc)
        assert "COUNT" in result.dax_expression
    
    def test_countd_aggregation(self, translator):
        calc = TableauCalculatedField(
            name="Unique Customers",
            formula="COUNTD([Customer ID])",
            calculation_type=CalculationType.AGGREGATE
        )
        result = translator.translate(calc)
        assert "DISTINCTCOUNT" in result.dax_expression
    
    def test_min_max(self, translator):
        calc_min = TableauCalculatedField(
            name="Min Sales",
            formula="MIN([Sales])",
            calculation_type=CalculationType.AGGREGATE
        )
        calc_max = TableauCalculatedField(
            name="Max Sales",
            formula="MAX([Sales])",
            calculation_type=CalculationType.AGGREGATE
        )
        
        result_min = translator.translate(calc_min)
        result_max = translator.translate(calc_max)
        
        assert "MIN" in result_min.dax_expression
        assert "MAX" in result_max.dax_expression


class TestMathFunctions:
    """Tests for math function translations."""
    
    @pytest.fixture
    def translator(self):
        return FormulaTranslator(use_genai=False)
    
    def test_abs(self, translator):
        calc = TableauCalculatedField(
            name="Abs Value",
            formula="ABS([Profit])",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "ABS" in result.dax_expression
    
    def test_round(self, translator):
        calc = TableauCalculatedField(
            name="Rounded",
            formula="ROUND([Price], 2)",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "ROUND" in result.dax_expression
    
    def test_power(self, translator):
        calc = TableauCalculatedField(
            name="Squared",
            formula="POWER([Value], 2)",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "POWER" in result.dax_expression
    
    def test_sqrt(self, translator):
        calc = TableauCalculatedField(
            name="Square Root",
            formula="SQRT([Area])",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "SQRT" in result.dax_expression


class TestStringFunctions:
    """Tests for string function translations."""
    
    @pytest.fixture
    def translator(self):
        return FormulaTranslator(use_genai=False)
    
    def test_left(self, translator):
        calc = TableauCalculatedField(
            name="First 3 Chars",
            formula="LEFT([Name], 3)",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "LEFT" in result.dax_expression
    
    def test_right(self, translator):
        calc = TableauCalculatedField(
            name="Last 3 Chars",
            formula="RIGHT([Name], 3)",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "RIGHT" in result.dax_expression
    
    def test_upper_lower(self, translator):
        calc_upper = TableauCalculatedField(
            name="Uppercase",
            formula="UPPER([Name])",
            calculation_type=CalculationType.SIMPLE
        )
        calc_lower = TableauCalculatedField(
            name="Lowercase",
            formula="LOWER([Name])",
            calculation_type=CalculationType.SIMPLE
        )
        
        result_upper = translator.translate(calc_upper)
        result_lower = translator.translate(calc_lower)
        
        assert "UPPER" in result_upper.dax_expression
        assert "LOWER" in result_lower.dax_expression
    
    def test_len(self, translator):
        calc = TableauCalculatedField(
            name="Name Length",
            formula="LEN([Name])",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "LEN" in result.dax_expression
    
    def test_trim(self, translator):
        calc = TableauCalculatedField(
            name="Trimmed",
            formula="TRIM([Text])",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "TRIM" in result.dax_expression


class TestLogicalExpressions:
    """Tests for logical expression translations."""
    
    @pytest.fixture
    def translator(self):
        return FormulaTranslator(use_genai=False)
    
    def test_simple_if(self, translator):
        calc = TableauCalculatedField(
            name="Sales Category",
            formula="IF [Sales] > 1000 THEN 'High' ELSE 'Low' END",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "IF" in result.dax_expression
    
    def test_iif(self, translator):
        calc = TableauCalculatedField(
            name="Quick Check",
            formula="IIF([Profit] > 0, 'Positive', 'Negative')",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "IF" in result.dax_expression
    
    def test_case(self, translator):
        calc = TableauCalculatedField(
            name="Region Code",
            formula="CASE [Region] WHEN 'East' THEN 1 WHEN 'West' THEN 2 ELSE 0 END",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "SWITCH" in result.dax_expression
    
    def test_isnull(self, translator):
        calc = TableauCalculatedField(
            name="Null Check",
            formula="ISNULL([Value])",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "ISBLANK" in result.dax_expression
    
    def test_zn(self, translator):
        calc = TableauCalculatedField(
            name="Zero Null",
            formula="ZN([Sales])",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "ISBLANK" in result.dax_expression
        assert "0" in result.dax_expression
    
    def test_ifnull(self, translator):
        calc = TableauCalculatedField(
            name="Default Value",
            formula="IFNULL([Sales], 0)",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "ISBLANK" in result.dax_expression


class TestDateFunctions:
    """Tests for date function translations."""
    
    @pytest.fixture
    def translator(self):
        return FormulaTranslator(use_genai=False)
    
    def test_year(self, translator):
        calc = TableauCalculatedField(
            name="Order Year",
            formula="YEAR([Order Date])",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "YEAR" in result.dax_expression
    
    def test_month(self, translator):
        calc = TableauCalculatedField(
            name="Order Month",
            formula="MONTH([Order Date])",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "MONTH" in result.dax_expression
    
    def test_day(self, translator):
        calc = TableauCalculatedField(
            name="Order Day",
            formula="DAY([Order Date])",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "DAY" in result.dax_expression
    
    def test_today(self, translator):
        calc = TableauCalculatedField(
            name="Current Date",
            formula="TODAY()",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "TODAY" in result.dax_expression
    
    def test_now(self, translator):
        calc = TableauCalculatedField(
            name="Current DateTime",
            formula="NOW()",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "NOW" in result.dax_expression


class TestLODExpressions:
    """Tests for LOD expression translations."""
    
    @pytest.fixture
    def translator(self):
        return FormulaTranslator(use_genai=False)
    
    def test_fixed_lod(self, translator):
        calc = TableauCalculatedField(
            name="Customer Total",
            formula="{FIXED [Customer ID] : SUM([Sales])}",
            calculation_type=CalculationType.LOD_FIXED,
            lod_dimensions=["Customer ID"]
        )
        result = translator.translate(calc)
        assert "CALCULATE" in result.dax_expression
        assert "ALLEXCEPT" in result.dax_expression or result.requires_review
    
    def test_exclude_lod(self, translator):
        calc = TableauCalculatedField(
            name="Total Without Category",
            formula="{EXCLUDE [Category] : SUM([Sales])}",
            calculation_type=CalculationType.LOD_EXCLUDE,
            lod_dimensions=["Category"]
        )
        result = translator.translate(calc)
        assert "CALCULATE" in result.dax_expression or result.requires_review
    
    def test_include_lod(self, translator):
        calc = TableauCalculatedField(
            name="Regional Average",
            formula="{INCLUDE [Region] : AVG([Sales])}",
            calculation_type=CalculationType.LOD_INCLUDE,
            lod_dimensions=["Region"]
        )
        result = translator.translate(calc)
        # Include LODs are complex
        assert result.dax_expression is not None


class TestTableCalculations:
    """Tests for table calculation translations."""
    
    @pytest.fixture
    def translator(self):
        return FormulaTranslator(use_genai=False)
    
    def test_running_sum(self, translator):
        calc = TableauCalculatedField(
            name="Cumulative Sales",
            formula="RUNNING_SUM(SUM([Sales]))",
            calculation_type=CalculationType.TABLE_CALC,
            table_calc_type="running_sum"
        )
        result = translator.translate(calc)
        # Table calcs are complex and need review
        assert result.requires_review or "WINDOW" in result.dax_expression or "CALCULATE" in result.dax_expression
    
    def test_running_avg(self, translator):
        calc = TableauCalculatedField(
            name="Running Average",
            formula="RUNNING_AVG(AVG([Price]))",
            calculation_type=CalculationType.TABLE_CALC,
            table_calc_type="running_avg"
        )
        result = translator.translate(calc)
        assert result.requires_review or len(result.notes) > 0


class TestBinaryOperations:
    """Tests for binary operation translations."""
    
    @pytest.fixture
    def translator(self):
        return FormulaTranslator(use_genai=False)
    
    def test_addition(self, translator):
        calc = TableauCalculatedField(
            name="Total",
            formula="[Sales] + [Profit]",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "+" in result.dax_expression
    
    def test_subtraction(self, translator):
        calc = TableauCalculatedField(
            name="Difference",
            formula="[Sales] - [Cost]",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "-" in result.dax_expression
    
    def test_multiplication(self, translator):
        calc = TableauCalculatedField(
            name="Revenue",
            formula="[Price] * [Quantity]",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "*" in result.dax_expression
    
    def test_division(self, translator):
        calc = TableauCalculatedField(
            name="Unit Price",
            formula="[Total] / [Quantity]",
            calculation_type=CalculationType.SIMPLE
        )
        result = translator.translate(calc)
        assert "/" in result.dax_expression


class TestTranslationConfidence:
    """Tests for translation confidence levels."""
    
    @pytest.fixture
    def translator(self):
        return FormulaTranslator(use_genai=False)
    
    def test_simple_formula_high_confidence(self, translator):
        calc = TableauCalculatedField(
            name="Simple Sum",
            formula="SUM([Sales])",
            calculation_type=CalculationType.AGGREGATE
        )
        result = translator.translate(calc)
        assert result.confidence in [TranslationConfidence.HIGH, TranslationConfidence.MEDIUM]
    
    def test_table_calc_needs_review(self, translator):
        calc = TableauCalculatedField(
            name="Running Total",
            formula="RUNNING_SUM(SUM([Sales]))",
            calculation_type=CalculationType.TABLE_CALC,
            table_calc_type="running_sum"
        )
        result = translator.translate(calc)
        assert result.requires_review == True


class TestMeasureGeneration:
    """Tests for Power BI measure generation."""
    
    @pytest.fixture
    def translator(self):
        return FormulaTranslator(use_genai=False)
    
    def test_to_measure(self, translator):
        calc = TableauCalculatedField(
            name="Total Sales",
            caption="Total Sales Amount",
            formula="SUM([Sales])",
            calculation_type=CalculationType.AGGREGATE
        )
        result = translator.translate(calc)
        measure = translator.to_measure(calc, result)
        
        assert measure.name == "Total Sales Amount"
        assert measure.expression is not None
        assert measure.source_tableau_field == "Total Sales"
        assert measure.source_formula == "SUM([Sales])"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
