"""
Extended function mappings for Tableau to DAX translation.

This module provides comprehensive mappings for:
- All Tableau functions to DAX equivalents
- Semantic differences between platforms
- Complex translation patterns
"""

from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum


class TranslationComplexity(Enum):
    """Complexity levels for translations."""
    DIRECT = "direct"           # 1:1 mapping
    SIMPLE = "simple"           # Minor syntax change
    MODERATE = "moderate"       # Requires restructuring
    COMPLEX = "complex"         # Needs pattern transformation
    MANUAL = "manual"           # Cannot be automated


@dataclass
class FunctionMapping:
    """Represents a function mapping from Tableau to DAX."""
    tableau_function: str
    dax_equivalent: str
    complexity: TranslationComplexity
    notes: str = ""
    transform_args: Optional[Callable] = None
    example_tableau: str = ""
    example_dax: str = ""


# =============================================================================
# AGGREGATION FUNCTIONS
# =============================================================================

AGGREGATION_MAPPINGS: Dict[str, FunctionMapping] = {
    # Basic aggregations
    "SUM": FunctionMapping(
        tableau_function="SUM",
        dax_equivalent="SUM",
        complexity=TranslationComplexity.DIRECT,
        example_tableau="SUM([Sales])",
        example_dax="SUM([Sales])"
    ),
    "AVG": FunctionMapping(
        tableau_function="AVG",
        dax_equivalent="AVERAGE",
        complexity=TranslationComplexity.SIMPLE,
        example_tableau="AVG([Price])",
        example_dax="AVERAGE([Price])"
    ),
    "MIN": FunctionMapping(
        tableau_function="MIN",
        dax_equivalent="MIN",
        complexity=TranslationComplexity.DIRECT
    ),
    "MAX": FunctionMapping(
        tableau_function="MAX",
        dax_equivalent="MAX",
        complexity=TranslationComplexity.DIRECT
    ),
    "COUNT": FunctionMapping(
        tableau_function="COUNT",
        dax_equivalent="COUNT",
        complexity=TranslationComplexity.DIRECT
    ),
    "COUNTD": FunctionMapping(
        tableau_function="COUNTD",
        dax_equivalent="DISTINCTCOUNT",
        complexity=TranslationComplexity.SIMPLE,
        example_tableau="COUNTD([Customer ID])",
        example_dax="DISTINCTCOUNT([Customer ID])"
    ),
    "MEDIAN": FunctionMapping(
        tableau_function="MEDIAN",
        dax_equivalent="MEDIAN",
        complexity=TranslationComplexity.DIRECT
    ),
    "STDEV": FunctionMapping(
        tableau_function="STDEV",
        dax_equivalent="STDEV.S",
        complexity=TranslationComplexity.SIMPLE,
        notes="Sample standard deviation"
    ),
    "STDEVP": FunctionMapping(
        tableau_function="STDEVP",
        dax_equivalent="STDEV.P",
        complexity=TranslationComplexity.SIMPLE,
        notes="Population standard deviation"
    ),
    "VAR": FunctionMapping(
        tableau_function="VAR",
        dax_equivalent="VAR.S",
        complexity=TranslationComplexity.SIMPLE,
        notes="Sample variance"
    ),
    "VARP": FunctionMapping(
        tableau_function="VARP",
        dax_equivalent="VAR.P",
        complexity=TranslationComplexity.SIMPLE,
        notes="Population variance"
    ),
    "CORR": FunctionMapping(
        tableau_function="CORR",
        dax_equivalent="/* CORR - use SUMMARIZE + custom calc */",
        complexity=TranslationComplexity.MANUAL,
        notes="No direct equivalent - requires custom calculation"
    ),
    "COVAR": FunctionMapping(
        tableau_function="COVAR",
        dax_equivalent="/* COVAR - use SUMMARIZE + custom calc */",
        complexity=TranslationComplexity.MANUAL,
        notes="No direct equivalent - requires custom calculation"
    ),
    "ATTR": FunctionMapping(
        tableau_function="ATTR",
        dax_equivalent="IF(DISTINCTCOUNT({0}) = 1, MAX({0}), BLANK())",
        complexity=TranslationComplexity.MODERATE,
        notes="Returns value if all values are same, else blank",
        example_tableau="ATTR([Region])",
        example_dax="IF(DISTINCTCOUNT([Region]) = 1, MAX([Region]), BLANK())"
    ),
    "COLLECT": FunctionMapping(
        tableau_function="COLLECT",
        dax_equivalent="CONCATENATEX",
        complexity=TranslationComplexity.MODERATE,
        notes="Collects values into a single geometry/string"
    ),
    "PERCENTILE": FunctionMapping(
        tableau_function="PERCENTILE",
        dax_equivalent="PERCENTILEX.INC",
        complexity=TranslationComplexity.SIMPLE,
        example_tableau="PERCENTILE([Sales], 0.9)",
        example_dax="PERCENTILEX.INC(Table, [Sales], 0.9)"
    ),
}

# =============================================================================
# STRING FUNCTIONS
# =============================================================================

STRING_MAPPINGS: Dict[str, FunctionMapping] = {
    "ASCII": FunctionMapping(
        tableau_function="ASCII",
        dax_equivalent="UNICODE",
        complexity=TranslationComplexity.SIMPLE,
        notes="Returns Unicode value of first character"
    ),
    "CHAR": FunctionMapping(
        tableau_function="CHAR",
        dax_equivalent="UNICHAR",
        complexity=TranslationComplexity.SIMPLE
    ),
    "CONTAINS": FunctionMapping(
        tableau_function="CONTAINS",
        dax_equivalent="CONTAINSSTRING",
        complexity=TranslationComplexity.SIMPLE,
        example_tableau='CONTAINS([Name], "John")',
        example_dax='CONTAINSSTRING([Name], "John")'
    ),
    "ENDSWITH": FunctionMapping(
        tableau_function="ENDSWITH",
        dax_equivalent="ENDSWITH",
        complexity=TranslationComplexity.DIRECT
    ),
    "STARTSWITH": FunctionMapping(
        tableau_function="STARTSWITH",
        dax_equivalent="STARTSWITH",  # Available in newer DAX
        complexity=TranslationComplexity.DIRECT
    ),
    "FIND": FunctionMapping(
        tableau_function="FIND",
        dax_equivalent="SEARCH",
        complexity=TranslationComplexity.SIMPLE,
        notes="SEARCH is case-insensitive, use FIND for case-sensitive",
        example_tableau='FIND("a", [Text])',
        example_dax='SEARCH("a", [Text])'
    ),
    "FINDNTH": FunctionMapping(
        tableau_function="FINDNTH",
        dax_equivalent="/* FINDNTH - requires custom pattern */",
        complexity=TranslationComplexity.COMPLEX,
        notes="No direct equivalent - requires iterative approach"
    ),
    "LEFT": FunctionMapping(
        tableau_function="LEFT",
        dax_equivalent="LEFT",
        complexity=TranslationComplexity.DIRECT
    ),
    "RIGHT": FunctionMapping(
        tableau_function="RIGHT",
        dax_equivalent="RIGHT",
        complexity=TranslationComplexity.DIRECT
    ),
    "MID": FunctionMapping(
        tableau_function="MID",
        dax_equivalent="MID",
        complexity=TranslationComplexity.DIRECT
    ),
    "LEN": FunctionMapping(
        tableau_function="LEN",
        dax_equivalent="LEN",
        complexity=TranslationComplexity.DIRECT
    ),
    "LENGTH": FunctionMapping(
        tableau_function="LENGTH",
        dax_equivalent="LEN",
        complexity=TranslationComplexity.SIMPLE
    ),
    "LOWER": FunctionMapping(
        tableau_function="LOWER",
        dax_equivalent="LOWER",
        complexity=TranslationComplexity.DIRECT
    ),
    "UPPER": FunctionMapping(
        tableau_function="UPPER",
        dax_equivalent="UPPER",
        complexity=TranslationComplexity.DIRECT
    ),
    "PROPER": FunctionMapping(
        tableau_function="PROPER",
        dax_equivalent="/* PROPER - no direct equivalent */",
        complexity=TranslationComplexity.COMPLEX,
        notes="Use custom M query or calculated column"
    ),
    "TRIM": FunctionMapping(
        tableau_function="TRIM",
        dax_equivalent="TRIM",
        complexity=TranslationComplexity.DIRECT
    ),
    "LTRIM": FunctionMapping(
        tableau_function="LTRIM",
        dax_equivalent="TRIM",
        complexity=TranslationComplexity.SIMPLE,
        notes="DAX TRIM handles both sides"
    ),
    "RTRIM": FunctionMapping(
        tableau_function="RTRIM",
        dax_equivalent="TRIM",
        complexity=TranslationComplexity.SIMPLE,
        notes="DAX TRIM handles both sides"
    ),
    "REPLACE": FunctionMapping(
        tableau_function="REPLACE",
        dax_equivalent="SUBSTITUTE",
        complexity=TranslationComplexity.SIMPLE,
        notes="Different argument order - SUBSTITUTE(text, old, new)",
        example_tableau='REPLACE([Name], "old", "new")',
        example_dax='SUBSTITUTE([Name], "old", "new")'
    ),
    "SPACE": FunctionMapping(
        tableau_function="SPACE",
        dax_equivalent='REPT(" ", {0})',
        complexity=TranslationComplexity.SIMPLE,
        example_tableau="SPACE(5)",
        example_dax='REPT(" ", 5)'
    ),
    "SPLIT": FunctionMapping(
        tableau_function="SPLIT",
        dax_equivalent="/* SPLIT - use Power Query */",
        complexity=TranslationComplexity.MANUAL,
        notes="No DAX equivalent - use Power Query M"
    ),
    "STR": FunctionMapping(
        tableau_function="STR",
        dax_equivalent='FORMAT({0}, "General Number")',
        complexity=TranslationComplexity.SIMPLE
    ),
    "REGEXP_MATCH": FunctionMapping(
        tableau_function="REGEXP_MATCH",
        dax_equivalent="/* REGEXP - no DAX support */",
        complexity=TranslationComplexity.MANUAL,
        notes="DAX does not support regex - use Power Query"
    ),
    "REGEXP_REPLACE": FunctionMapping(
        tableau_function="REGEXP_REPLACE",
        dax_equivalent="/* REGEXP - no DAX support */",
        complexity=TranslationComplexity.MANUAL,
        notes="DAX does not support regex - use Power Query"
    ),
    "REGEXP_EXTRACT": FunctionMapping(
        tableau_function="REGEXP_EXTRACT",
        dax_equivalent="/* REGEXP - no DAX support */",
        complexity=TranslationComplexity.MANUAL,
        notes="DAX does not support regex - use Power Query"
    ),
}

# =============================================================================
# DATE FUNCTIONS
# =============================================================================

DATE_MAPPINGS: Dict[str, FunctionMapping] = {
    "DATE": FunctionMapping(
        tableau_function="DATE",
        dax_equivalent="DATE",
        complexity=TranslationComplexity.DIRECT
    ),
    "DATETIME": FunctionMapping(
        tableau_function="DATETIME",
        dax_equivalent="DATE + TIME",
        complexity=TranslationComplexity.MODERATE,
        notes="Combine DATE and TIME functions"
    ),
    "DATEADD": FunctionMapping(
        tableau_function="DATEADD",
        dax_equivalent="DATEADD",
        complexity=TranslationComplexity.SIMPLE,
        notes="Different argument order in DAX",
        example_tableau="DATEADD('month', 3, [Date])",
        example_dax="DATEADD([Date], 3, MONTH)"
    ),
    "DATEDIFF": FunctionMapping(
        tableau_function="DATEDIFF",
        dax_equivalent="DATEDIFF",
        complexity=TranslationComplexity.SIMPLE,
        notes="Different argument order in DAX"
    ),
    "DATENAME": FunctionMapping(
        tableau_function="DATENAME",
        dax_equivalent="FORMAT",
        complexity=TranslationComplexity.MODERATE,
        example_tableau="DATENAME('month', [Date])",
        example_dax='FORMAT([Date], "MMMM")'
    ),
    "DATEPART": FunctionMapping(
        tableau_function="DATEPART",
        dax_equivalent="{part}([Date])",
        complexity=TranslationComplexity.MODERATE,
        notes="Use specific function: YEAR, MONTH, DAY, etc."
    ),
    "DATETRUNC": FunctionMapping(
        tableau_function="DATETRUNC",
        dax_equivalent="DATE(YEAR(...), MONTH(...), 1)",
        complexity=TranslationComplexity.COMPLEX,
        notes="Requires construction based on truncation level"
    ),
    "DAY": FunctionMapping(
        tableau_function="DAY",
        dax_equivalent="DAY",
        complexity=TranslationComplexity.DIRECT
    ),
    "MONTH": FunctionMapping(
        tableau_function="MONTH",
        dax_equivalent="MONTH",
        complexity=TranslationComplexity.DIRECT
    ),
    "YEAR": FunctionMapping(
        tableau_function="YEAR",
        dax_equivalent="YEAR",
        complexity=TranslationComplexity.DIRECT
    ),
    "QUARTER": FunctionMapping(
        tableau_function="QUARTER",
        dax_equivalent="QUARTER",
        complexity=TranslationComplexity.DIRECT
    ),
    "WEEK": FunctionMapping(
        tableau_function="WEEK",
        dax_equivalent="WEEKNUM",
        complexity=TranslationComplexity.SIMPLE
    ),
    "WEEKDAY": FunctionMapping(
        tableau_function="WEEKDAY",
        dax_equivalent="WEEKDAY",
        complexity=TranslationComplexity.DIRECT
    ),
    "ISDATE": FunctionMapping(
        tableau_function="ISDATE",
        dax_equivalent="ISERROR(DATEVALUE({0}))",
        complexity=TranslationComplexity.MODERATE,
        notes="Check if value can be converted to date"
    ),
    "MAKEDATE": FunctionMapping(
        tableau_function="MAKEDATE",
        dax_equivalent="DATE",
        complexity=TranslationComplexity.DIRECT,
        example_tableau="MAKEDATE(2024, 1, 15)",
        example_dax="DATE(2024, 1, 15)"
    ),
    "MAKEDATETIME": FunctionMapping(
        tableau_function="MAKEDATETIME",
        dax_equivalent="DATE(...) + TIME(...)",
        complexity=TranslationComplexity.MODERATE
    ),
    "MAKETIME": FunctionMapping(
        tableau_function="MAKETIME",
        dax_equivalent="TIME",
        complexity=TranslationComplexity.DIRECT
    ),
    "NOW": FunctionMapping(
        tableau_function="NOW",
        dax_equivalent="NOW",
        complexity=TranslationComplexity.DIRECT
    ),
    "TODAY": FunctionMapping(
        tableau_function="TODAY",
        dax_equivalent="TODAY",
        complexity=TranslationComplexity.DIRECT
    ),
}

# =============================================================================
# MATH FUNCTIONS
# =============================================================================

MATH_MAPPINGS: Dict[str, FunctionMapping] = {
    "ABS": FunctionMapping(
        tableau_function="ABS",
        dax_equivalent="ABS",
        complexity=TranslationComplexity.DIRECT
    ),
    "ACOS": FunctionMapping(
        tableau_function="ACOS",
        dax_equivalent="ACOS",
        complexity=TranslationComplexity.DIRECT
    ),
    "ASIN": FunctionMapping(
        tableau_function="ASIN",
        dax_equivalent="ASIN",
        complexity=TranslationComplexity.DIRECT
    ),
    "ATAN": FunctionMapping(
        tableau_function="ATAN",
        dax_equivalent="ATAN",
        complexity=TranslationComplexity.DIRECT
    ),
    "ATAN2": FunctionMapping(
        tableau_function="ATAN2",
        dax_equivalent="ATAN(y/x)",
        complexity=TranslationComplexity.MODERATE,
        notes="DAX doesn't have ATAN2 - use ATAN(y/x) with quadrant logic"
    ),
    "COS": FunctionMapping(
        tableau_function="COS",
        dax_equivalent="COS",
        complexity=TranslationComplexity.DIRECT
    ),
    "COT": FunctionMapping(
        tableau_function="COT",
        dax_equivalent="COT",
        complexity=TranslationComplexity.DIRECT
    ),
    "SIN": FunctionMapping(
        tableau_function="SIN",
        dax_equivalent="SIN",
        complexity=TranslationComplexity.DIRECT
    ),
    "TAN": FunctionMapping(
        tableau_function="TAN",
        dax_equivalent="TAN",
        complexity=TranslationComplexity.DIRECT
    ),
    "CEILING": FunctionMapping(
        tableau_function="CEILING",
        dax_equivalent="CEILING",
        complexity=TranslationComplexity.DIRECT
    ),
    "FLOOR": FunctionMapping(
        tableau_function="FLOOR",
        dax_equivalent="FLOOR",
        complexity=TranslationComplexity.DIRECT
    ),
    "ROUND": FunctionMapping(
        tableau_function="ROUND",
        dax_equivalent="ROUND",
        complexity=TranslationComplexity.DIRECT
    ),
    "POWER": FunctionMapping(
        tableau_function="POWER",
        dax_equivalent="POWER",
        complexity=TranslationComplexity.DIRECT
    ),
    "SQRT": FunctionMapping(
        tableau_function="SQRT",
        dax_equivalent="SQRT",
        complexity=TranslationComplexity.DIRECT
    ),
    "SQUARE": FunctionMapping(
        tableau_function="SQUARE",
        dax_equivalent="POWER({0}, 2)",
        complexity=TranslationComplexity.SIMPLE
    ),
    "EXP": FunctionMapping(
        tableau_function="EXP",
        dax_equivalent="EXP",
        complexity=TranslationComplexity.DIRECT
    ),
    "LN": FunctionMapping(
        tableau_function="LN",
        dax_equivalent="LN",
        complexity=TranslationComplexity.DIRECT
    ),
    "LOG": FunctionMapping(
        tableau_function="LOG",
        dax_equivalent="LOG",
        complexity=TranslationComplexity.DIRECT
    ),
    "SIGN": FunctionMapping(
        tableau_function="SIGN",
        dax_equivalent="SIGN",
        complexity=TranslationComplexity.DIRECT
    ),
    "PI": FunctionMapping(
        tableau_function="PI",
        dax_equivalent="PI",
        complexity=TranslationComplexity.DIRECT
    ),
    "RADIANS": FunctionMapping(
        tableau_function="RADIANS",
        dax_equivalent="RADIANS",
        complexity=TranslationComplexity.DIRECT
    ),
    "DEGREES": FunctionMapping(
        tableau_function="DEGREES",
        dax_equivalent="DEGREES",
        complexity=TranslationComplexity.DIRECT
    ),
    "DIV": FunctionMapping(
        tableau_function="DIV",
        dax_equivalent="QUOTIENT",
        complexity=TranslationComplexity.SIMPLE,
        notes="Integer division"
    ),
    "HEXBINX": FunctionMapping(
        tableau_function="HEXBINX",
        dax_equivalent="/* HEXBINX - no equivalent */",
        complexity=TranslationComplexity.MANUAL,
        notes="Hexagonal binning not available in DAX"
    ),
    "HEXBINY": FunctionMapping(
        tableau_function="HEXBINY",
        dax_equivalent="/* HEXBINY - no equivalent */",
        complexity=TranslationComplexity.MANUAL,
        notes="Hexagonal binning not available in DAX"
    ),
}

# =============================================================================
# LOGICAL FUNCTIONS
# =============================================================================

LOGICAL_MAPPINGS: Dict[str, FunctionMapping] = {
    "IF": FunctionMapping(
        tableau_function="IF",
        dax_equivalent="IF",
        complexity=TranslationComplexity.SIMPLE,
        notes="IF-THEN-ELSE-END becomes IF(condition, true, false)"
    ),
    "IIF": FunctionMapping(
        tableau_function="IIF",
        dax_equivalent="IF",
        complexity=TranslationComplexity.DIRECT,
        example_tableau="IIF([Sales] > 100, 'High', 'Low')",
        example_dax="IF([Sales] > 100, \"High\", \"Low\")"
    ),
    "CASE": FunctionMapping(
        tableau_function="CASE",
        dax_equivalent="SWITCH",
        complexity=TranslationComplexity.SIMPLE,
        example_tableau="CASE [Region] WHEN 'East' THEN 1 WHEN 'West' THEN 2 END",
        example_dax="SWITCH([Region], \"East\", 1, \"West\", 2)"
    ),
    "IFNULL": FunctionMapping(
        tableau_function="IFNULL",
        dax_equivalent="IF(ISBLANK({0}), {1}, {0})",
        complexity=TranslationComplexity.SIMPLE,
        example_tableau="IFNULL([Sales], 0)",
        example_dax="IF(ISBLANK([Sales]), 0, [Sales])"
    ),
    "ZN": FunctionMapping(
        tableau_function="ZN",
        dax_equivalent="IF(ISBLANK({0}), 0, {0})",
        complexity=TranslationComplexity.SIMPLE,
        example_tableau="ZN([Sales])",
        example_dax="IF(ISBLANK([Sales]), 0, [Sales])"
    ),
    "ISNULL": FunctionMapping(
        tableau_function="ISNULL",
        dax_equivalent="ISBLANK",
        complexity=TranslationComplexity.SIMPLE
    ),
    "ISDATE": FunctionMapping(
        tableau_function="ISDATE",
        dax_equivalent="NOT(ISERROR(DATEVALUE({0})))",
        complexity=TranslationComplexity.MODERATE
    ),
    "ISNUMBER": FunctionMapping(
        tableau_function="ISNUMBER",
        dax_equivalent="ISNUMBER",
        complexity=TranslationComplexity.DIRECT
    ),
    "ISSTRING": FunctionMapping(
        tableau_function="ISSTRING",
        dax_equivalent="ISTEXT",
        complexity=TranslationComplexity.SIMPLE
    ),
    "NOT": FunctionMapping(
        tableau_function="NOT",
        dax_equivalent="NOT",
        complexity=TranslationComplexity.DIRECT
    ),
    "AND": FunctionMapping(
        tableau_function="AND",
        dax_equivalent="AND",
        complexity=TranslationComplexity.SIMPLE,
        notes="Can also use && operator"
    ),
    "OR": FunctionMapping(
        tableau_function="OR",
        dax_equivalent="OR",
        complexity=TranslationComplexity.SIMPLE,
        notes="Can also use || operator"
    ),
}

# =============================================================================
# TABLE CALCULATION FUNCTIONS
# =============================================================================

TABLE_CALC_MAPPINGS: Dict[str, FunctionMapping] = {
    "RUNNING_SUM": FunctionMapping(
        tableau_function="RUNNING_SUM",
        dax_equivalent="""CALCULATE(
    SUM({field}),
    WINDOW(1, ABS, 0, REL, ALLSELECTED(Table), ORDERBY([SortColumn]))
)""",
        complexity=TranslationComplexity.COMPLEX,
        notes="Requires proper ORDERBY column for correct ordering"
    ),
    "RUNNING_AVG": FunctionMapping(
        tableau_function="RUNNING_AVG",
        dax_equivalent="""CALCULATE(
    AVERAGE({field}),
    WINDOW(1, ABS, 0, REL, ALLSELECTED(Table), ORDERBY([SortColumn]))
)""",
        complexity=TranslationComplexity.COMPLEX
    ),
    "RUNNING_COUNT": FunctionMapping(
        tableau_function="RUNNING_COUNT",
        dax_equivalent="""CALCULATE(
    COUNT({field}),
    WINDOW(1, ABS, 0, REL, ALLSELECTED(Table), ORDERBY([SortColumn]))
)""",
        complexity=TranslationComplexity.COMPLEX
    ),
    "RUNNING_MIN": FunctionMapping(
        tableau_function="RUNNING_MIN",
        dax_equivalent="""CALCULATE(
    MIN({field}),
    WINDOW(1, ABS, 0, REL, ALLSELECTED(Table), ORDERBY([SortColumn]))
)""",
        complexity=TranslationComplexity.COMPLEX
    ),
    "RUNNING_MAX": FunctionMapping(
        tableau_function="RUNNING_MAX",
        dax_equivalent="""CALCULATE(
    MAX({field}),
    WINDOW(1, ABS, 0, REL, ALLSELECTED(Table), ORDERBY([SortColumn]))
)""",
        complexity=TranslationComplexity.COMPLEX
    ),
    "WINDOW_SUM": FunctionMapping(
        tableau_function="WINDOW_SUM",
        dax_equivalent="""CALCULATE(
    SUM({field}),
    WINDOW({start}, REL, {end}, REL, ALLSELECTED(Table), ORDERBY([SortColumn]))
)""",
        complexity=TranslationComplexity.COMPLEX,
        notes="Window boundaries may differ from Tableau behavior"
    ),
    "WINDOW_AVG": FunctionMapping(
        tableau_function="WINDOW_AVG",
        dax_equivalent="""CALCULATE(
    AVERAGE({field}),
    WINDOW({start}, REL, {end}, REL, ALLSELECTED(Table), ORDERBY([SortColumn]))
)""",
        complexity=TranslationComplexity.COMPLEX
    ),
    "INDEX": FunctionMapping(
        tableau_function="INDEX",
        dax_equivalent="INDEX(ALLSELECTED(Table), ORDERBY([SortColumn]))",
        complexity=TranslationComplexity.COMPLEX,
        notes="DAX INDEX function available in newer versions"
    ),
    "FIRST": FunctionMapping(
        tableau_function="FIRST",
        dax_equivalent="1 - INDEX(...)",
        complexity=TranslationComplexity.COMPLEX,
        notes="Offset from first row"
    ),
    "LAST": FunctionMapping(
        tableau_function="LAST",
        dax_equivalent="COUNTROWS(...) - INDEX(...)",
        complexity=TranslationComplexity.COMPLEX,
        notes="Offset from last row"
    ),
    "SIZE": FunctionMapping(
        tableau_function="SIZE",
        dax_equivalent="COUNTROWS(ALLSELECTED(Table))",
        complexity=TranslationComplexity.MODERATE,
        notes="Total number of rows in partition"
    ),
    "LOOKUP": FunctionMapping(
        tableau_function="LOOKUP",
        dax_equivalent="OFFSET({offset}, ALLSELECTED(Table), ORDERBY([SortColumn]))",
        complexity=TranslationComplexity.COMPLEX,
        notes="DAX OFFSET function for relative lookups"
    ),
    "PREVIOUS_VALUE": FunctionMapping(
        tableau_function="PREVIOUS_VALUE",
        dax_equivalent="/* Recursive - use iterator pattern */",
        complexity=TranslationComplexity.MANUAL,
        notes="Recursive calculations need different approach in DAX"
    ),
    "RANK": FunctionMapping(
        tableau_function="RANK",
        dax_equivalent="RANKX(ALL(Table), {measure})",
        complexity=TranslationComplexity.MODERATE,
        example_tableau="RANK(SUM([Sales]))",
        example_dax="RANKX(ALL(Table), [Total Sales])"
    ),
    "RANK_DENSE": FunctionMapping(
        tableau_function="RANK_DENSE",
        dax_equivalent="RANKX(ALL(Table), {measure}, , , Dense)",
        complexity=TranslationComplexity.MODERATE
    ),
    "RANK_MODIFIED": FunctionMapping(
        tableau_function="RANK_MODIFIED",
        dax_equivalent="/* Use custom rank pattern */",
        complexity=TranslationComplexity.COMPLEX,
        notes="Modified competition ranking needs custom logic"
    ),
    "RANK_PERCENTILE": FunctionMapping(
        tableau_function="RANK_PERCENTILE",
        dax_equivalent="DIVIDE(RANKX(...) - 1, COUNTROWS(...) - 1)",
        complexity=TranslationComplexity.COMPLEX
    ),
    "RANK_UNIQUE": FunctionMapping(
        tableau_function="RANK_UNIQUE",
        dax_equivalent="RANKX(ALL(Table), {measure}, , , Skip)",
        complexity=TranslationComplexity.MODERATE
    ),
    "TOTAL": FunctionMapping(
        tableau_function="TOTAL",
        dax_equivalent="CALCULATE({measure}, ALLSELECTED(Table))",
        complexity=TranslationComplexity.MODERATE,
        notes="Grand total across partition"
    ),
}

# =============================================================================
# LOD EXPRESSION PATTERNS
# =============================================================================

LOD_PATTERNS: Dict[str, Dict[str, str]] = {
    "FIXED": {
        "pattern": "CALCULATE({agg}, ALLEXCEPT(Table, {dims}))",
        "no_dims": "CALCULATE({agg}, ALL(Table))",
        "example_tableau": "{FIXED [Customer] : SUM([Sales])}",
        "example_dax": "CALCULATE(SUM([Sales]), ALLEXCEPT(Table, [Customer]))",
        "notes": "FIXED ignores viz filters, use ALLEXCEPT to maintain only specified dimensions"
    },
    "INCLUDE": {
        "pattern": "AVERAGEX(SUMMARIZE(Table, {dims}, \"_val\", {agg}), [_val])",
        "example_tableau": "{INCLUDE [Region] : AVG([Sales])}",
        "example_dax": "AVERAGEX(SUMMARIZE(Table, [Region], \"_val\", AVERAGE([Sales])), [_val])",
        "notes": "INCLUDE adds dimensions to current context"
    },
    "EXCLUDE": {
        "pattern": "CALCULATE({agg}, REMOVEFILTERS({dims}))",
        "example_tableau": "{EXCLUDE [Category] : SUM([Sales])}",
        "example_dax": "CALCULATE(SUM([Sales]), REMOVEFILTERS([Category]))",
        "notes": "EXCLUDE removes specified dimensions from context"
    },
}


# =============================================================================
# TYPE CONVERSION FUNCTIONS
# =============================================================================

TYPE_MAPPINGS: Dict[str, FunctionMapping] = {
    "INT": FunctionMapping(
        tableau_function="INT",
        dax_equivalent="INT",
        complexity=TranslationComplexity.DIRECT
    ),
    "FLOAT": FunctionMapping(
        tableau_function="FLOAT",
        dax_equivalent="VALUE",
        complexity=TranslationComplexity.SIMPLE
    ),
    "STR": FunctionMapping(
        tableau_function="STR",
        dax_equivalent='FORMAT({0}, "General Number")',
        complexity=TranslationComplexity.SIMPLE
    ),
    "DATE": FunctionMapping(
        tableau_function="DATE",
        dax_equivalent="DATE",
        complexity=TranslationComplexity.DIRECT
    ),
    "DATETIME": FunctionMapping(
        tableau_function="DATETIME",
        dax_equivalent="/* Use DATE + TIME */",
        complexity=TranslationComplexity.MODERATE
    ),
    "BOOL": FunctionMapping(
        tableau_function="BOOL",
        dax_equivalent="/* Boolean conversion */",
        complexity=TranslationComplexity.SIMPLE,
        notes="Use comparison or IF statement"
    ),
}


def get_all_mappings() -> Dict[str, FunctionMapping]:
    """Get all function mappings combined."""
    all_mappings = {}
    all_mappings.update(AGGREGATION_MAPPINGS)
    all_mappings.update(STRING_MAPPINGS)
    all_mappings.update(DATE_MAPPINGS)
    all_mappings.update(MATH_MAPPINGS)
    all_mappings.update(LOGICAL_MAPPINGS)
    all_mappings.update(TABLE_CALC_MAPPINGS)
    all_mappings.update(TYPE_MAPPINGS)
    return all_mappings


def get_mapping(function_name: str) -> Optional[FunctionMapping]:
    """Get mapping for a specific function."""
    all_mappings = get_all_mappings()
    return all_mappings.get(function_name.upper())


def get_mappings_by_complexity(complexity: TranslationComplexity) -> List[FunctionMapping]:
    """Get all mappings with a specific complexity level."""
    return [
        m for m in get_all_mappings().values()
        if m.complexity == complexity
    ]


def get_direct_mappings() -> Dict[str, str]:
    """Get simple dict of direct 1:1 mappings."""
    return {
        name: mapping.dax_equivalent
        for name, mapping in get_all_mappings().items()
        if mapping.complexity == TranslationComplexity.DIRECT
    }
