"""
Formula translator for converting Tableau calculations to DAX.

This module provides both rule-based translation for simple formulas
and GenAI-powered translation for complex cases like LOD expressions
and table calculations.
"""

import re
import os
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from parsers.formula_parser import TableauFormulaParser, ASTNode
from models.tableau_models import TableauCalculatedField, CalculationType
from models.powerbi_models import PowerBIMeasure
from translators.extended_mappings import (
    get_all_mappings, get_mapping, get_direct_mappings,
    LOD_PATTERNS, TABLE_CALC_MAPPINGS, TranslationComplexity
)


class TranslationConfidence(Enum):
    """Confidence levels for formula translations."""
    HIGH = "high"       # Direct mapping, almost certainly correct
    MEDIUM = "medium"   # Good translation, may need verification
    LOW = "low"         # Best effort, likely needs manual review
    FAILED = "failed"   # Could not translate


@dataclass
class TranslationResult:
    """Result of a formula translation."""
    dax_expression: str
    confidence: TranslationConfidence
    notes: List[str]
    source_formula: str
    requires_review: bool = False
    alternative_expressions: List[str] = None
    
    def __post_init__(self):
        if self.alternative_expressions is None:
            self.alternative_expressions = []


class FormulaTranslator:
    """
    Translates Tableau formulas to DAX.
    
    Uses a combination of rule-based translation for simple cases
    and GenAI (OpenAI) for complex formulas.
    """
    
    # Direct function mappings (Tableau -> DAX)
    FUNCTION_MAP = {
        # Aggregations
        "SUM": "SUM",
        "AVG": "AVERAGE",
        "COUNT": "COUNT",
        "COUNTD": "DISTINCTCOUNT",
        "MIN": "MIN",
        "MAX": "MAX",
        "MEDIAN": "MEDIAN",
        
        # Math functions
        "ABS": "ABS",
        "CEILING": "CEILING",
        "FLOOR": "FLOOR",
        "ROUND": "ROUND",
        "POWER": "POWER",
        "SQRT": "SQRT",
        "EXP": "EXP",
        "LN": "LN",
        "LOG": "LOG",
        "SIGN": "SIGN",
        "PI": "PI",
        "SIN": "SIN",
        "COS": "COS",
        "TAN": "TAN",
        "ASIN": "ASIN",
        "ACOS": "ACOS",
        "ATAN": "ATAN",
        "RADIANS": "RADIANS",
        "DEGREES": "DEGREES",
        
        # String functions
        "LEN": "LEN",
        "LENGTH": "LEN",
        "LEFT": "LEFT",
        "RIGHT": "RIGHT",
        "MID": "MID",
        "UPPER": "UPPER",
        "LOWER": "LOWER",
        "TRIM": "TRIM",
        "REPLACE": "SUBSTITUTE",  # Note: different signature
        "SPACE": "REPT",  # SPACE(n) -> REPT(" ", n)
        "CONTAINS": "CONTAINSSTRING",
        "STARTSWITH": "STARTSWITH",  # Available in DAX
        "ENDSWITH": "ENDSWITH",  # Available in DAX
        
        # Date functions
        "TODAY": "TODAY",
        "NOW": "NOW",
        "YEAR": "YEAR",
        "MONTH": "MONTH",
        "DAY": "DAY",
        "WEEKDAY": "WEEKDAY",
        "QUARTER": "QUARTER",
        "WEEK": "WEEKNUM",
        "DATEADD": "DATEADD",
        "DATEDIFF": "DATEDIFF",
        
        # Logical functions
        "ISNULL": "ISBLANK",
        "IFNULL": "IF(ISBLANK",  # Requires special handling
        "ZN": "IF(ISBLANK",  # ZN(x) -> IF(ISBLANK(x), 0, x)
        
        # Type conversion
        "INT": "INT",
        "FLOAT": "VALUE",  # FLOAT -> VALUE in DAX
        "STR": "FORMAT",  # STR -> FORMAT (with format string)
    }
    
    # Operators mapping
    OPERATOR_MAP = {
        "+": "+",
        "-": "-",
        "*": "*",
        "/": "/",
        "^": "^",
        "%": "MOD",  # Modulo requires special handling
        "=": "=",
        "<>": "<>",
        "!=": "<>",
        "<": "<",
        ">": ">",
        "<=": "<=",
        ">=": ">=",
        "AND": "&&",
        "OR": "||",
        "NOT": "NOT",
    }
    
    def __init__(self, use_genai: bool = True, openai_api_key: Optional[str] = None):
        """
        Initialize the formula translator.
        
        Args:
            use_genai: Whether to use GenAI for complex translations
            openai_api_key: OpenAI API key (or from environment)
        """
        self.use_genai = use_genai
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self._openai_client = None
    
    @property
    def openai_client(self):
        """Lazy initialization of OpenAI client."""
        if self._openai_client is None and self.openai_api_key:
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=self.openai_api_key)
            except ImportError:
                pass
        return self._openai_client
    
    def translate(self, calc_field: TableauCalculatedField, table_name: Optional[str] = None) -> TranslationResult:
        """
        Translate a Tableau calculated field to DAX.
        
        Args:
            calc_field: Tableau calculated field to translate
            table_name: Optional table name for field references
            
        Returns:
            TranslationResult with DAX expression and metadata
        """
        formula = calc_field.formula
        
        # Determine translation strategy based on calculation type
        if calc_field.calculation_type in [CalculationType.SIMPLE, CalculationType.ROW_LEVEL]:
            return self._translate_simple(formula, table_name)
        
        elif calc_field.calculation_type == CalculationType.AGGREGATE:
            return self._translate_aggregate(formula, table_name)
        
        elif calc_field.is_lod:
            return self._translate_lod(formula, calc_field.calculation_type, calc_field.lod_dimensions, table_name)
        
        elif calc_field.is_table_calc:
            return self._translate_table_calc(formula, calc_field.table_calc_type, table_name)
        
        else:
            # Default: try simple translation, fall back to GenAI
            result = self._translate_simple(formula, table_name)
            if result.confidence == TranslationConfidence.FAILED and self.use_genai:
                return self._translate_with_genai(formula, calc_field)
            return result
    
    def _translate_simple(self, formula: str, table_name: Optional[str] = None) -> TranslationResult:
        """
        Translate simple formulas using rule-based approach.
        """
        notes = []
        
        try:
            # Parse the formula
            parser = TableauFormulaParser(formula)
            ast = parser.parse()
            
            # Translate AST to DAX
            dax_expr = self._ast_to_dax(ast, notes, table_name)
            
            # Determine confidence based on what we encountered
            confidence = TranslationConfidence.HIGH
            if notes:
                confidence = TranslationConfidence.MEDIUM
            
            return TranslationResult(
                dax_expression=dax_expr,
                confidence=confidence,
                notes=notes,
                source_formula=formula,
                requires_review=confidence != TranslationConfidence.HIGH,
            )
            
        except Exception as e:
            return TranslationResult(
                dax_expression=f"/* Translation failed: {str(e)} */",
                confidence=TranslationConfidence.FAILED,
                notes=[f"Translation error: {str(e)}"],
                source_formula=formula,
                requires_review=True,
            )
    
    def _ast_to_dax(self, node: ASTNode, notes: List[str], table_name: Optional[str] = None) -> str:
        """Convert an AST node to DAX expression."""
        if node.node_type == "number":
            return str(node.value)
        
        if node.node_type == "string":
            return f'"{node.value}"'
        
        if node.node_type == "boolean":
            return "TRUE()" if node.value else "FALSE()"
        
        if node.node_type == "null":
            return "BLANK()"
        
        if node.node_type == "field":
            # Convert field reference to DAX format
            # [Field Name] -> 'Table'[Field Name]
            field_name = node.value
            if table_name:
                return f"'{table_name}'[{field_name}]"
            return f"[{field_name}]"
        
        if node.node_type == "binary_op":
            left = self._ast_to_dax(node.children[0], notes, table_name)
            right = self._ast_to_dax(node.children[1], notes, table_name)
            op = self.OPERATOR_MAP.get(node.value, node.value)
            
            if node.value == "%":
                return f"MOD({left}, {right})"
            
            return f"({left} {op} {right})"
        
        if node.node_type == "unary_op":
            operand = self._ast_to_dax(node.children[0], notes, table_name)
            if node.value == "-":
                return f"-{operand}"
            if node.value == "NOT":
                return f"NOT({operand})"
            return operand
        
        if node.node_type == "comparison":
            left = self._ast_to_dax(node.children[0], notes, table_name)
            right = self._ast_to_dax(node.children[1], notes, table_name)
            op = self.OPERATOR_MAP.get(node.value, node.value)
            return f"{left} {op} {right}"
        
        if node.node_type == "function":
            return self._translate_function(node, notes, table_name)
        
        if node.node_type == "if":
            return self._translate_if(node, notes, table_name)
        
        if node.node_type == "case":
            return self._translate_case(node, notes, table_name)
        
        if node.node_type == "lod":
            # LOD expressions need special handling
            notes.append("LOD expression requires CALCULATE pattern")
            lod_type = node.value
            dims = node.metadata.get("dimensions", [])
            inner_expr = self._ast_to_dax(node.children[0], notes, table_name) if node.children else "0"
            return self._build_lod_dax(lod_type, dims, inner_expr, table_name or "Table")
        
        if node.node_type == "error":
            notes.append(f"Parse error: {node.value}")
            return f"/* Error: {node.value} */"
        
        return f"/* Unknown node type: {node.node_type} */"

    def _translate_function(self, node: ASTNode, notes: List[str], table_name: Optional[str] = None) -> str:
        """Translate a function call to DAX using extended mappings."""
        func_name = node.value.upper()
        args = [self._ast_to_dax(child, notes, table_name) for child in node.children]

        # First check extended mappings for comprehensive function support
        extended_mapping = get_mapping(func_name)
        if extended_mapping:
            if extended_mapping.complexity == TranslationComplexity.DIRECT:
                return f"{extended_mapping.dax_equivalent}({', '.join(args)})"
            elif extended_mapping.complexity == TranslationComplexity.SIMPLE:
                # Handle simple transformations
                dax_equiv = extended_mapping.dax_equivalent
                if "{0}" in dax_equiv:
                    return dax_equiv.format(*args) if args else dax_equiv
                return f"{dax_equiv}({', '.join(args)})"
            elif extended_mapping.complexity == TranslationComplexity.MANUAL:
                notes.append(extended_mapping.notes)
                return f"/* {func_name} - {extended_mapping.notes} */"
        
        # Direct mapping from local function map
        if func_name in self.FUNCTION_MAP:
            dax_func = self.FUNCTION_MAP[func_name]
            
            # Special cases requiring argument transformation
            if func_name == "ZN":
                if args:
                    return f"IF(ISBLANK({args[0]}), 0, {args[0]})"
                return "0"
            
            if func_name == "IFNULL":
                if len(args) >= 2:
                    return f"IF(ISBLANK({args[0]}), {args[1]}, {args[0]})"
                return args[0] if args else "BLANK()"
            
            if func_name == "SPACE":
                if args:
                    return f'REPT(" ", {args[0]})'
                return '""'
            
            if func_name == "FIND":
                # FIND(substring, string, start) -> SEARCH(substring, string, start)
                if len(args) >= 2:
                    search_args = ", ".join(args[:3] if len(args) >= 3 else args[:2])
                    return f"SEARCH({search_args})"
                return "0"
            
            if func_name == "STR":
                # STR(value) -> FORMAT(value, "General Number")
                if args:
                    return f'FORMAT({args[0]}, "General Number")'
                return '""'
            
            return f"{dax_func}({', '.join(args)})"
        
        # IIF function (inline if)
        if func_name == "IIF":
            if len(args) >= 3:
                return f"IF({args[0]}, {args[1]}, {args[2]})"
            elif len(args) == 2:
                return f"IF({args[0]}, {args[1]}, BLANK())"
            return "BLANK()"
        
        # ATTR function (returns value if all same, else *)
        if func_name == "ATTR":
            notes.append("ATTR function approximated - may behave differently")
            if args:
                return f"IF(DISTINCTCOUNT({args[0]}) = 1, MAX({args[0]}), BLANK())"
            return "BLANK()"
        
        # Date functions with special handling
        if func_name == "DATETRUNC":
            return self._translate_datetrunc(args, notes)
        
        if func_name == "DATENAME":
            return self._translate_datename(args, notes)
        
        if func_name == "DATEPART":
            return self._translate_datepart(args, notes)
        
        if func_name == "MAKEDATE":
            if len(args) >= 3:
                return f"DATE({args[0]}, {args[1]}, {args[2]})"
            return "BLANK()"
        
        # Table calculation functions
        if func_name in ("RUNNING_SUM", "RUNNING_AVG", "RUNNING_COUNT", 
                         "RUNNING_MIN", "RUNNING_MAX"):
            notes.append(f"{func_name} requires WINDOW function pattern - needs manual review")
            return self._translate_running_func(func_name, args, notes)
        
        if func_name in ("WINDOW_SUM", "WINDOW_AVG", "WINDOW_COUNT",
                         "WINDOW_MIN", "WINDOW_MAX"):
            notes.append(f"{func_name} requires WINDOW function pattern - needs manual review")
            return self._translate_window_func(func_name, args, notes)
        
        if func_name in ("INDEX", "FIRST", "LAST", "SIZE"):
            notes.append(f"{func_name} table calculation has no direct DAX equivalent")
            return f"/* {func_name}() - requires custom DAX pattern */"
        
        if func_name == "LOOKUP":
            notes.append("LOOKUP requires OFFSET function in DAX - needs manual review")
            return f"/* LOOKUP({', '.join(args)}) - use OFFSET pattern */"
        
        if func_name in ("RANK", "RANK_DENSE", "RANK_MODIFIED", 
                         "RANK_PERCENTILE", "RANK_UNIQUE"):
            return self._translate_rank(func_name, args, notes)
        
        # Unknown function
        notes.append(f"Unknown function: {func_name}")
        return f"{func_name}({', '.join(args)})"
    
    def _translate_if(self, node: ASTNode, notes: List[str], table_name: Optional[str] = None) -> str:
        """Translate IF-THEN-ELSE to DAX IF."""
        conditions_count = node.metadata.get("conditions_count", 1)
        has_else = node.metadata.get("has_else", False)
        
        conditions = node.children[:conditions_count]
        results = node.children[conditions_count:conditions_count * 2]
        else_result = node.children[-1] if has_else else None
        
        if conditions_count == 1:
            # Simple IF
            cond_dax = self._ast_to_dax(conditions[0], notes, table_name)
            then_dax = self._ast_to_dax(results[0], notes, table_name)
            else_dax = self._ast_to_dax(else_result, notes, table_name) if else_result else "BLANK()"
            return f"IF({cond_dax}, {then_dax}, {else_dax})"
        else:
            # Multiple conditions -> nested IF or SWITCH(TRUE(), ...)
            parts = []
            for i, (cond, result) in enumerate(zip(conditions, results)):
                cond_dax = self._ast_to_dax(cond, notes, table_name)
                result_dax = self._ast_to_dax(result, notes, table_name)
                parts.append(f"{cond_dax}, {result_dax}")
            
            else_dax = self._ast_to_dax(else_result, notes, table_name) if else_result else "BLANK()"
            
            return f"SWITCH(TRUE(), {', '.join(parts)}, {else_dax})"
    
    def _translate_case(self, node: ASTNode, notes: List[str], table_name: Optional[str] = None) -> str:
        """Translate CASE-WHEN to DAX SWITCH."""
        when_count = node.metadata.get("when_count", 0)
        has_else = node.metadata.get("has_else", False)
        
        case_expr = node.children[0]
        when_values = node.children[1:when_count + 1]
        then_results = node.children[when_count + 1:when_count * 2 + 1]
        else_result = node.children[-1] if has_else else None
        
        case_dax = self._ast_to_dax(case_expr, notes, table_name)
        
        pairs = []
        for when_val, then_result in zip(when_values, then_results):
            when_dax = self._ast_to_dax(when_val, notes, table_name)
            then_dax = self._ast_to_dax(then_result, notes, table_name)
            pairs.append(f"{when_dax}, {then_dax}")
        
        else_dax = self._ast_to_dax(else_result, notes, table_name) if else_result else "BLANK()"
        
        return f"SWITCH({case_dax}, {', '.join(pairs)}, {else_dax})"
    
    def _build_lod_dax(self, lod_type: str, dimensions: List[str], inner_expr: str, table_name: str = "'Table'") -> str:
        """Build DAX expression for LOD calculation using pattern templates."""
        # Use patterns from extended_mappings for consistency
        if lod_type == "FIXED":
            if dimensions:
                dim_list = ", ".join(f"{table_name}[{d}]" for d in dimensions)
                return f"CALCULATE({inner_expr}, ALLEXCEPT({table_name}, {dim_list}))"
            else:
                # FIXED with no dimensions = grand total
                return f"CALCULATE({inner_expr}, ALL({table_name}))"
        
        elif lod_type == "INCLUDE":
            # INCLUDE adds dimensions to current context
            if dimensions:
                dim_refs = ", ".join(f"{table_name}[{d}]" for d in dimensions)
                return f"AVERAGEX(SUMMARIZE({table_name}, {dim_refs}, \"_val\", {inner_expr}), [_val])"
            return inner_expr
        
        elif lod_type == "EXCLUDE":
            # EXCLUDE removes dimensions from current context
            if dimensions:
                dim_list = ", ".join(f"{table_name}[{d}]" for d in dimensions)
                return f"CALCULATE({inner_expr}, REMOVEFILTERS({dim_list}))"
            return inner_expr
        
        return inner_expr
    
    def _translate_aggregate(self, formula: str, table_name: Optional[str] = None) -> TranslationResult:
        """Translate aggregate formulas."""
        # Use simple translation as aggregates are straightforward
        return self._translate_simple(formula, table_name)
    
    def _translate_lod(self, formula: str, calc_type: CalculationType, 
                       dimensions: List[str], table_name: Optional[str] = None) -> TranslationResult:
        """Translate LOD expressions."""
        notes = ["LOD expression translated using CALCULATE pattern"]
        
        # Try rule-based first
        result = self._translate_simple(formula, table_name)
        
        if result.confidence == TranslationConfidence.FAILED and self.use_genai:
            return self._translate_with_genai(formula, None, "LOD")
        
        return result
    
    def _translate_table_calc(self, formula: str, 
                              calc_type: Optional[str], table_name: Optional[str] = None) -> TranslationResult:
        """Translate table calculations."""
        notes = [
            f"Table calculation ({calc_type or 'unknown'}) - requires careful review",
            "Table calc behavior depends on viz structure - verify result matches"
        ]
        
        # Table calcs often need GenAI assistance
        if self.use_genai and self.openai_client:
            return self._translate_with_genai(formula, None, "table_calc")
        
        # Attempt rule-based translation
        result = self._translate_simple(formula, table_name)
        result.notes.extend(notes)
        result.confidence = TranslationConfidence.LOW
        result.requires_review = True
        
        return result
    
    def _translate_running_func(self, func_name: str, args: List[str], 
                                notes: List[str]) -> str:
        """Translate RUNNING_* functions to DAX WINDOW pattern."""
        # RUNNING_SUM([Sales]) -> 
        # CALCULATE(
        #     SUM([Sales]),
        #     WINDOW(1, ABS, -1, REL, ALLSELECTED(Table), ORDERBY([Date]))
        # )
        
        agg_type = func_name.replace("RUNNING_", "")
        agg_map = {"SUM": "SUM", "AVG": "AVERAGE", "COUNT": "COUNT", 
                   "MIN": "MIN", "MAX": "MAX"}
        dax_agg = agg_map.get(agg_type, "SUM")
        
        expr = args[0] if args else "[Value]"
        
        notes.append("WINDOW function requires proper ORDERBY - add sort column")
        
        return f"""CALCULATE(
    {dax_agg}({expr}),
    WINDOW(1, ABS, 0, REL, ALLSELECTED('Table'), ORDERBY([_SortColumn]))
)"""
    
    def _translate_window_func(self, func_name: str, args: List[str], 
                               notes: List[str]) -> str:
        """Translate WINDOW_* functions to DAX WINDOW pattern."""
        # WINDOW_SUM(SUM([Sales]), -2, 0) ->
        # Calculate sum of current row and 2 previous rows
        
        agg_type = func_name.replace("WINDOW_", "")
        agg_map = {"SUM": "SUM", "AVG": "AVERAGE", "COUNT": "COUNT", 
                   "MIN": "MIN", "MAX": "MAX"}
        dax_agg = agg_map.get(agg_type, "SUM")
        
        expr = args[0] if args else "[Value]"
        start_offset = args[1] if len(args) > 1 else "-1"
        end_offset = args[2] if len(args) > 2 else "0"
        
        notes.append("WINDOW function requires proper ORDERBY - add sort column")
        
        return f"""CALCULATE(
    {dax_agg}({expr}),
    WINDOW({start_offset}, REL, {end_offset}, REL, ALLSELECTED('Table'), ORDERBY([_SortColumn]))
)"""
    
    def _translate_rank(self, func_name: str, args: List[str], 
                        notes: List[str]) -> str:
        """Translate RANK functions to DAX RANKX."""
        expr = args[0] if args else "[Value]"
        
        rank_func = "RANKX"
        order = "DESC"  # Default
        
        if func_name == "RANK_DENSE":
            rank_func = "RANKX"
            notes.append("RANK_DENSE uses RANKX with Dense parameter")
            return f"RANKX(ALL('Table'), {expr}, , {order}, Dense)"
        
        return f"RANKX(ALL('Table'), {expr}, , {order})"
    
    def _translate_datetrunc(self, args: List[str], notes: List[str]) -> str:
        """Translate DATETRUNC function."""
        if len(args) < 2:
            return "BLANK()"
        
        part = args[0].strip("'\"").upper()
        date_expr = args[1]
        
        trunc_map = {
            "YEAR": f"DATE(YEAR({date_expr}), 1, 1)",
            "QUARTER": f"DATE(YEAR({date_expr}), (QUARTER({date_expr})-1)*3+1, 1)",
            "MONTH": f"DATE(YEAR({date_expr}), MONTH({date_expr}), 1)",
            "WEEK": f"DATE(YEAR({date_expr}), MONTH({date_expr}), DAY({date_expr}) - WEEKDAY({date_expr}) + 1)",
            "DAY": f"DATE(YEAR({date_expr}), MONTH({date_expr}), DAY({date_expr}))",
        }
        
        return trunc_map.get(part, date_expr)
    
    def _translate_datename(self, args: List[str], notes: List[str]) -> str:
        """Translate DATENAME function."""
        if len(args) < 2:
            return '""'
        
        part = args[0].strip("'\"").upper()
        date_expr = args[1]
        
        name_map = {
            "YEAR": f'FORMAT({date_expr}, "YYYY")',
            "QUARTER": f'"Q" & QUARTER({date_expr})',
            "MONTH": f'FORMAT({date_expr}, "MMMM")',
            "WEEKDAY": f'FORMAT({date_expr}, "dddd")',
            "DAY": f'FORMAT({date_expr}, "DD")',
        }
        
        return name_map.get(part, f'FORMAT({date_expr}, "{part}")')
    
    def _translate_datepart(self, args: List[str], notes: List[str]) -> str:
        """Translate DATEPART function."""
        if len(args) < 2:
            return "0"
        
        part = args[0].strip("'\"").upper()
        date_expr = args[1]
        
        part_map = {
            "YEAR": f"YEAR({date_expr})",
            "QUARTER": f"QUARTER({date_expr})",
            "MONTH": f"MONTH({date_expr})",
            "WEEK": f"WEEKNUM({date_expr})",
            "WEEKDAY": f"WEEKDAY({date_expr})",
            "DAY": f"DAY({date_expr})",
            "HOUR": f"HOUR({date_expr})",
            "MINUTE": f"MINUTE({date_expr})",
            "SECOND": f"SECOND({date_expr})",
        }
        
        return part_map.get(part, f"0 /* Unknown date part: {part} */")
    
    def _translate_with_genai(self, formula: str, 
                              calc_field: Optional[TableauCalculatedField] = None,
                              context: str = "") -> TranslationResult:
        """
        Use GenAI (OpenAI) to translate complex formulas.
        """
        if not self.openai_client:
            return TranslationResult(
                dax_expression=f"/* GenAI translation unavailable for: {formula} */",
                confidence=TranslationConfidence.FAILED,
                notes=["GenAI not available - OpenAI API key not configured"],
                source_formula=formula,
                requires_review=True,
            )
        
        try:
            prompt = self._build_genai_prompt(formula, calc_field, context)
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert at translating Tableau calculations to Power BI DAX.
                        
Rules:
1. Provide ONLY the DAX expression, no explanation
2. Use proper DAX syntax and functions
3. For LOD expressions, use CALCULATE with ALLEXCEPT/REMOVEFILTERS
4. For table calculations, use WINDOW or iterator functions
5. If translation is impossible, return a comment explaining why

Common patterns:
- FIXED LOD -> CALCULATE(AGG(), ALLEXCEPT(Table, Dims))
- INCLUDE LOD -> AVERAGEX(SUMMARIZE(...), ...)
- EXCLUDE LOD -> CALCULATE(AGG(), REMOVEFILTERS(Dims))
- RUNNING_SUM -> CALCULATE(SUM(), WINDOW(1, ABS, 0, REL, ...))
- ZN() -> IF(ISBLANK(), 0, ...)"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=500,
            )
            
            dax_expr = response.choices[0].message.content.strip()
            
            # Clean up response (remove markdown code blocks if present)
            if dax_expr.startswith("```"):
                lines = dax_expr.split("\n")
                dax_expr = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            
            return TranslationResult(
                dax_expression=dax_expr,
                confidence=TranslationConfidence.MEDIUM,
                notes=[f"Translated using GenAI ({context or 'general'})"],
                source_formula=formula,
                requires_review=True,  # GenAI translations should always be reviewed
            )
            
        except Exception as e:
            return TranslationResult(
                dax_expression=f"/* GenAI translation failed: {str(e)} */",
                confidence=TranslationConfidence.FAILED,
                notes=[f"GenAI error: {str(e)}"],
                source_formula=formula,
                requires_review=True,
            )
    
    def _build_genai_prompt(self, formula: str, 
                            calc_field: Optional[TableauCalculatedField],
                            context: str) -> str:
        """Build prompt for GenAI translation."""
        prompt = f"Translate this Tableau calculation to DAX:\n\n{formula}"
        
        if calc_field:
            prompt += f"\n\nField name: {calc_field.display_name}"
            prompt += f"\nData type: {calc_field.datatype.value}"
            prompt += f"\nRole: {calc_field.role}"
            
            if calc_field.lod_dimensions:
                prompt += f"\nLOD dimensions: {', '.join(calc_field.lod_dimensions)}"
        
        if context:
            prompt += f"\n\nContext: This is a {context} calculation"
        
        return prompt
    
    def translate_batch(self, calc_fields: List[TableauCalculatedField]) -> List[Tuple[TableauCalculatedField, TranslationResult]]:
        """
        Translate multiple calculated fields.
        
        Args:
            calc_fields: List of calculated fields to translate
            
        Returns:
            List of tuples (original_field, translation_result)
        """
        results = []
        for field in calc_fields:
            result = self.translate(field)
            results.append((field, result))
        return results
    
    def to_measure(self, calc_field: TableauCalculatedField, 
                   translation: TranslationResult,
                   table_name: str = "Measures") -> PowerBIMeasure:
        """
        Convert a translated calculation to a Power BI measure.
        
        Args:
            calc_field: Original Tableau calculated field
            translation: Translation result
            table_name: Table to place the measure in
            
        Returns:
            PowerBIMeasure instance
        """
        return PowerBIMeasure(
            name=calc_field.display_name,
            expression=translation.dax_expression,
            description=f"Translated from Tableau: {calc_field.formula[:100]}...",
            source_tableau_field=calc_field.name,
            source_formula=calc_field.formula,
            translation_confidence=1.0 if translation.confidence == TranslationConfidence.HIGH 
                                   else 0.7 if translation.confidence == TranslationConfidence.MEDIUM 
                                   else 0.3,
            translation_notes=translation.notes,
            requires_review=translation.requires_review,
        )
