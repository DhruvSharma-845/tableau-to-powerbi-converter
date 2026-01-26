"""
Unit tests for Tableau formula parser.
"""

import pytest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.formula_parser import TableauFormulaParser, TokenType, ASTNode


class TestTokenizer:
    """Tests for formula tokenization."""
    
    def test_simple_number(self):
        parser = TableauFormulaParser("42")
        tokens = parser.tokenize()
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == 42.0
    
    def test_decimal_number(self):
        parser = TableauFormulaParser("3.14159")
        tokens = parser.tokenize()
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == 3.14159
    
    def test_string_literal(self):
        parser = TableauFormulaParser('"Hello World"')
        tokens = parser.tokenize()
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "Hello World"
    
    def test_field_reference(self):
        parser = TableauFormulaParser("[Sales Amount]")
        tokens = parser.tokenize()
        assert tokens[0].type == TokenType.FIELD
        assert tokens[0].value == "Sales Amount"
    
    def test_operators(self):
        parser = TableauFormulaParser("+ - * / = < > <= >= <>")
        tokens = parser.tokenize()
        expected = [
            TokenType.PLUS, TokenType.MINUS, TokenType.MULTIPLY, TokenType.DIVIDE,
            TokenType.EQUALS, TokenType.LESS_THAN, TokenType.GREATER_THAN,
            TokenType.LESS_EQUAL, TokenType.GREATER_EQUAL, TokenType.NOT_EQUALS
        ]
        for i, exp_type in enumerate(expected):
            assert tokens[i].type == exp_type
    
    def test_keywords(self):
        parser = TableauFormulaParser("IF THEN ELSE ELSEIF END AND OR NOT")
        tokens = parser.tokenize()
        expected = [
            TokenType.IF, TokenType.THEN, TokenType.ELSE, TokenType.ELSEIF,
            TokenType.END, TokenType.AND, TokenType.OR, TokenType.NOT
        ]
        for i, exp_type in enumerate(expected):
            assert tokens[i].type == exp_type
    
    def test_lod_keywords(self):
        parser = TableauFormulaParser("FIXED INCLUDE EXCLUDE")
        tokens = parser.tokenize()
        assert tokens[0].type == TokenType.FIXED
        assert tokens[1].type == TokenType.INCLUDE
        assert tokens[2].type == TokenType.EXCLUDE
    
    def test_function(self):
        parser = TableauFormulaParser("SUM([Sales])")
        tokens = parser.tokenize()
        assert tokens[0].type == TokenType.FUNCTION
        assert tokens[0].value == "SUM"
        assert tokens[1].type == TokenType.LPAREN
        assert tokens[2].type == TokenType.FIELD
        assert tokens[3].type == TokenType.RPAREN
    
    def test_boolean_literals(self):
        parser = TableauFormulaParser("TRUE FALSE")
        tokens = parser.tokenize()
        assert tokens[0].type == TokenType.BOOLEAN
        assert tokens[0].value == True
        assert tokens[1].type == TokenType.BOOLEAN
        assert tokens[1].value == False


class TestParser:
    """Tests for formula parsing to AST."""
    
    def test_simple_number(self):
        parser = TableauFormulaParser("42")
        ast = parser.parse()
        assert ast.node_type == "number"
        assert ast.value == 42.0
    
    def test_simple_string(self):
        parser = TableauFormulaParser('"test"')
        ast = parser.parse()
        assert ast.node_type == "string"
        assert ast.value == "test"
    
    def test_field_reference(self):
        parser = TableauFormulaParser("[Sales]")
        ast = parser.parse()
        assert ast.node_type == "field"
        assert ast.value == "Sales"
    
    def test_binary_addition(self):
        parser = TableauFormulaParser("[A] + [B]")
        ast = parser.parse()
        assert ast.node_type == "binary_op"
        assert ast.value == "+"
        assert len(ast.children) == 2
        assert ast.children[0].node_type == "field"
        assert ast.children[1].node_type == "field"
    
    def test_binary_multiplication(self):
        parser = TableauFormulaParser("[Price] * [Quantity]")
        ast = parser.parse()
        assert ast.node_type == "binary_op"
        assert ast.value == "*"
    
    def test_operator_precedence(self):
        parser = TableauFormulaParser("[A] + [B] * [C]")
        ast = parser.parse()
        # Should be A + (B * C)
        assert ast.node_type == "binary_op"
        assert ast.value == "+"
        assert ast.children[1].node_type == "binary_op"
        assert ast.children[1].value == "*"
    
    def test_parentheses(self):
        parser = TableauFormulaParser("([A] + [B]) * [C]")
        ast = parser.parse()
        # Should be (A + B) * C
        assert ast.node_type == "binary_op"
        assert ast.value == "*"
        assert ast.children[0].node_type == "binary_op"
        assert ast.children[0].value == "+"
    
    def test_function_call(self):
        parser = TableauFormulaParser("SUM([Sales])")
        ast = parser.parse()
        assert ast.node_type == "function"
        assert ast.value == "SUM"
        assert len(ast.children) == 1
        assert ast.children[0].node_type == "field"
    
    def test_function_multiple_args(self):
        parser = TableauFormulaParser("LEFT([Name], 5)")
        ast = parser.parse()
        assert ast.node_type == "function"
        assert ast.value == "LEFT"
        assert len(ast.children) == 2
    
    def test_nested_functions(self):
        parser = TableauFormulaParser("UPPER(LEFT([Name], 5))")
        ast = parser.parse()
        assert ast.node_type == "function"
        assert ast.value == "UPPER"
        assert ast.children[0].node_type == "function"
        assert ast.children[0].value == "LEFT"
    
    def test_if_expression(self):
        parser = TableauFormulaParser("IF [Sales] > 100 THEN 'High' ELSE 'Low' END")
        ast = parser.parse()
        assert ast.node_type == "if"
        assert ast.metadata["conditions_count"] == 1
        assert ast.metadata["has_else"] == True
    
    def test_case_expression(self):
        parser = TableauFormulaParser("CASE [Region] WHEN 'East' THEN 1 WHEN 'West' THEN 2 ELSE 0 END")
        ast = parser.parse()
        assert ast.node_type == "case"
        assert ast.metadata["when_count"] == 2
        assert ast.metadata["has_else"] == True
    
    def test_lod_fixed(self):
        parser = TableauFormulaParser("{FIXED [Customer] : SUM([Sales])}")
        ast = parser.parse()
        assert ast.node_type == "lod"
        assert ast.value == "FIXED"
        assert "Customer" in ast.metadata["dimensions"]
    
    def test_lod_exclude(self):
        parser = TableauFormulaParser("{EXCLUDE [Category] : AVG([Price])}")
        ast = parser.parse()
        assert ast.node_type == "lod"
        assert ast.value == "EXCLUDE"
        assert "Category" in ast.metadata["dimensions"]
    
    def test_comparison(self):
        parser = TableauFormulaParser("[Sales] >= 1000")
        ast = parser.parse()
        assert ast.node_type == "comparison"
        assert ast.value == ">="
    
    def test_logical_and(self):
        parser = TableauFormulaParser("[A] > 0 AND [B] < 100")
        ast = parser.parse()
        assert ast.node_type == "binary_op"
        assert ast.value == "AND"
    
    def test_logical_or(self):
        parser = TableauFormulaParser("[A] = 1 OR [B] = 2")
        ast = parser.parse()
        assert ast.node_type == "binary_op"
        assert ast.value == "OR"
    
    def test_unary_minus(self):
        parser = TableauFormulaParser("-[Sales]")
        ast = parser.parse()
        assert ast.node_type == "unary_op"
        assert ast.value == "-"


class TestComplexityScoring:
    """Tests for formula complexity scoring."""
    
    def test_simple_formula_low_score(self):
        parser = TableauFormulaParser("SUM([Sales])")
        score = parser.get_complexity_score()
        assert score <= 20
    
    def test_lod_formula_higher_score(self):
        parser = TableauFormulaParser("{FIXED [Customer] : SUM([Sales])}")
        score = parser.get_complexity_score()
        assert score >= 30
    
    def test_table_calc_highest_score(self):
        parser = TableauFormulaParser("RUNNING_SUM(SUM([Sales]))")
        score = parser.get_complexity_score()
        assert score >= 40


class TestFieldExtraction:
    """Tests for extracting field references."""
    
    def test_single_field(self):
        parser = TableauFormulaParser("[Sales]")
        fields = parser.extract_fields()
        assert fields == ["Sales"]
    
    def test_multiple_fields(self):
        parser = TableauFormulaParser("[Sales] + [Profit]")
        fields = parser.extract_fields()
        assert set(fields) == {"Sales", "Profit"}
    
    def test_nested_fields(self):
        parser = TableauFormulaParser("IF [Region] = 'East' THEN [Sales] * 1.1 ELSE [Sales] END")
        fields = parser.extract_fields()
        assert set(fields) == {"Region", "Sales"}


class TestFunctionExtraction:
    """Tests for extracting function calls."""
    
    def test_single_function(self):
        parser = TableauFormulaParser("SUM([Sales])")
        funcs = parser.extract_functions()
        assert funcs == ["SUM"]
    
    def test_nested_functions(self):
        parser = TableauFormulaParser("ROUND(AVG([Price]), 2)")
        funcs = parser.extract_functions()
        assert set(funcs) == {"ROUND", "AVG"}
    
    def test_multiple_functions(self):
        parser = TableauFormulaParser("SUM([Sales]) / COUNT([Orders])")
        funcs = parser.extract_functions()
        assert set(funcs) == {"SUM", "COUNT"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
