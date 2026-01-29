"""
Pre-flight validation for Tableau to Power BI conversion.

Validates the conversion before making API calls or generating files:
- DAX expression syntax validation
- Table and column reference checking
- Visual configuration validation
- Data type compatibility
"""

import re
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from models.powerbi_models import (
    PowerBIReport, PowerBITable, PowerBIMeasure, 
    PowerBIColumn, PowerBIPage, PowerBIVisual
)


class IssueSeverity(str, Enum):
    """Severity levels for validation issues."""
    ERROR = "error"           # Will cause failure
    WARNING = "warning"       # May cause issues
    INFO = "info"             # Informational


@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    severity: IssueSeverity
    category: str
    message: str
    component: str
    details: Optional[str] = None
    suggestion: Optional[str] = None
    
    def __str__(self) -> str:
        prefix = f"[{self.severity.value.upper()}]"
        return f"{prefix} {self.category}: {self.message}"


@dataclass
class ValidationResult:
    """Result of pre-flight validation."""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    errors: int = 0
    warnings: int = 0
    
    def add_issue(self, issue: ValidationIssue) -> None:
        """Add a validation issue."""
        self.issues.append(issue)
        if issue.severity == IssueSeverity.ERROR:
            self.errors += 1
            self.is_valid = False
        elif issue.severity == IssueSeverity.WARNING:
            self.warnings += 1
    
    def add_error(self, category: str, message: str, component: str, 
                  details: str = None, suggestion: str = None) -> None:
        """Add an error issue."""
        self.add_issue(ValidationIssue(
            severity=IssueSeverity.ERROR,
            category=category,
            message=message,
            component=component,
            details=details,
            suggestion=suggestion,
        ))
    
    def add_warning(self, category: str, message: str, component: str,
                    details: str = None, suggestion: str = None) -> None:
        """Add a warning issue."""
        self.add_issue(ValidationIssue(
            severity=IssueSeverity.WARNING,
            category=category,
            message=message,
            component=component,
            details=details,
            suggestion=suggestion,
        ))
    
    def add_info(self, category: str, message: str, component: str) -> None:
        """Add an informational issue."""
        self.add_issue(ValidationIssue(
            severity=IssueSeverity.INFO,
            category=category,
            message=message,
            component=component,
        ))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "issues": [
                {
                    "severity": i.severity.value,
                    "category": i.category,
                    "message": i.message,
                    "component": i.component,
                    "details": i.details,
                    "suggestion": i.suggestion,
                }
                for i in self.issues
            ]
        }
    
    def to_markdown(self) -> str:
        """Generate a markdown report."""
        lines = [
            "# Pre-flight Validation Report",
            "",
            f"**Status:** {'PASSED' if self.is_valid else 'FAILED'}",
            f"**Errors:** {self.errors}",
            f"**Warnings:** {self.warnings}",
            "",
        ]
        
        if self.issues:
            lines.append("## Issues")
            lines.append("")
            
            for issue in sorted(self.issues, key=lambda x: x.severity.value):
                severity_icon = {
                    IssueSeverity.ERROR: "X",
                    IssueSeverity.WARNING: "!",
                    IssueSeverity.INFO: "i",
                }[issue.severity]
                
                lines.append(f"### [{severity_icon}] {issue.category}")
                lines.append(f"**Component:** {issue.component}")
                lines.append(f"**Message:** {issue.message}")
                if issue.details:
                    lines.append(f"**Details:** {issue.details}")
                if issue.suggestion:
                    lines.append(f"**Suggestion:** {issue.suggestion}")
                lines.append("")
        
        return "\n".join(lines)


class PreFlightValidator:
    """
    Pre-flight validator for Power BI conversion.
    
    Checks for common issues before making API calls or generating files.
    """
    
    # Reserved DAX keywords that cannot be used as identifiers
    DAX_RESERVED = {
        'TRUE', 'FALSE', 'NOT', 'AND', 'OR', 'IN', 'VAR', 'RETURN',
        'EVALUATE', 'ORDER', 'BY', 'ASC', 'DESC', 'DEFINE', 'MEASURE',
    }
    
    # Common DAX functions for validation
    DAX_FUNCTIONS = {
        'SUM', 'AVERAGE', 'COUNT', 'COUNTROWS', 'DISTINCTCOUNT', 'MIN', 'MAX',
        'CALCULATE', 'FILTER', 'ALL', 'ALLEXCEPT', 'VALUES', 'SUMMARIZE',
        'IF', 'SWITCH', 'ISBLANK', 'BLANK', 'FORMAT', 'RELATED', 'RELATEDTABLE',
        'DATE', 'YEAR', 'MONTH', 'DAY', 'TODAY', 'NOW', 'DATEDIFF', 'DATEADD',
        'DIVIDE', 'ROUND', 'ABS', 'INT', 'MOD', 'POWER', 'SQRT',
        'LEFT', 'RIGHT', 'MID', 'LEN', 'UPPER', 'LOWER', 'TRIM', 'SUBSTITUTE',
        'RANKX', 'TOPN', 'EARLIER', 'EARLIEST', 'SELECTEDVALUE',
        'WINDOW', 'OFFSET', 'INDEX',
    }
    
    # Invalid characters in Power BI identifiers
    INVALID_CHARS = set('<>:"/\\|?*[]')
    
    def __init__(self):
        self.result = ValidationResult(is_valid=True)
        self._table_names: Set[str] = set()
        self._column_refs: Dict[str, Set[str]] = {}  # table -> columns
    
    def validate(self, report: PowerBIReport) -> ValidationResult:
        """
        Perform full validation on a Power BI report.
        
        Args:
            report: Power BI report to validate
            
        Returns:
            ValidationResult with all issues found
        """
        self.result = ValidationResult(is_valid=True)
        self._table_names = set()
        self._column_refs = {}
        
        # Build reference maps
        self._build_reference_maps(report)
        
        # Validate tables
        self._validate_tables(report)
        
        # Validate measures
        self._validate_measures(report)
        
        # Validate pages and visuals
        self._validate_pages(report)
        
        # Validate relationships
        self._validate_relationships(report)
        
        return self.result
    
    def _build_reference_maps(self, report: PowerBIReport) -> None:
        """Build maps of table and column names for reference checking."""
        for table in report.tables:
            self._table_names.add(table.name)
            self._column_refs[table.name] = set()
            
            for col in table.columns:
                self._column_refs[table.name].add(col.name)
            
            for measure in table.measures:
                self._column_refs[table.name].add(measure.name)
    
    def _validate_tables(self, report: PowerBIReport) -> None:
        """Validate table definitions."""
        if not report.tables:
            self.result.add_warning(
                "Schema",
                "No tables defined in the data model",
                "Report",
                suggestion="Add at least one table with columns"
            )
            return
        
        table_names_seen = set()
        
        for table in report.tables:
            # Check for duplicate table names
            if table.name in table_names_seen:
                self.result.add_error(
                    "Schema",
                    f"Duplicate table name: {table.name}",
                    f"Table: {table.name}",
                    suggestion="Rename one of the tables"
                )
            table_names_seen.add(table.name)
            
            # Check for invalid characters in table name
            invalid = self.INVALID_CHARS.intersection(set(table.name))
            if invalid:
                self.result.add_error(
                    "Naming",
                    f"Invalid characters in table name: {invalid}",
                    f"Table: {table.name}",
                    suggestion="Remove or replace invalid characters"
                )
            
            # Check for empty table name
            if not table.name or table.name.isspace():
                self.result.add_error(
                    "Naming",
                    "Empty table name",
                    "Table",
                    suggestion="Provide a valid table name"
                )
            
            # Check for columns
            if not table.columns:
                self.result.add_warning(
                    "Schema",
                    f"Table has no columns",
                    f"Table: {table.name}",
                    suggestion="Add at least one column to the table"
                )
            
            # Validate columns
            self._validate_columns(table)
    
    def _validate_columns(self, table: PowerBITable) -> None:
        """Validate column definitions in a table."""
        column_names_seen = set()
        
        for col in table.columns:
            # Check for duplicate column names
            if col.name in column_names_seen:
                self.result.add_error(
                    "Schema",
                    f"Duplicate column name: {col.name}",
                    f"Table: {table.name}, Column: {col.name}",
                    suggestion="Rename one of the columns"
                )
            column_names_seen.add(col.name)
            
            # Check for invalid characters
            invalid = self.INVALID_CHARS.intersection(set(col.name))
            if invalid:
                self.result.add_warning(
                    "Naming",
                    f"Special characters in column name: {invalid}",
                    f"Table: {table.name}, Column: {col.name}",
                    suggestion="Consider removing special characters"
                )
            
            # Check for empty column name
            if not col.name or col.name.isspace():
                self.result.add_error(
                    "Naming",
                    "Empty column name",
                    f"Table: {table.name}",
                    suggestion="Provide a valid column name"
                )
    
    def _validate_measures(self, report: PowerBIReport) -> None:
        """Validate DAX measures."""
        all_measures = report.get_all_measures()
        
        for measure in all_measures:
            self._validate_dax_expression(measure)
    
    def _validate_dax_expression(self, measure: PowerBIMeasure) -> None:
        """Validate a DAX expression for syntax issues."""
        expr = measure.expression
        name = measure.name
        
        # Check for empty expression
        if not expr or expr.isspace():
            self.result.add_error(
                "DAX",
                "Empty measure expression",
                f"Measure: {name}",
                suggestion="Provide a valid DAX expression"
            )
            return
        
        # Check for comment-only expression (translation failure)
        if expr.strip().startswith('/*') and expr.strip().endswith('*/'):
            self.result.add_warning(
                "DAX",
                "Measure contains only a comment (likely translation failure)",
                f"Measure: {name}",
                details=expr[:100],
                suggestion="Review and fix the DAX expression"
            )
        
        # Check for unbalanced parentheses
        paren_count = expr.count('(') - expr.count(')')
        if paren_count != 0:
            self.result.add_error(
                "DAX",
                f"Unbalanced parentheses ({'+' if paren_count > 0 else ''}{paren_count})",
                f"Measure: {name}",
                details=expr[:100],
                suggestion="Check for missing or extra parentheses"
            )
        
        # Check for unbalanced brackets
        bracket_count = expr.count('[') - expr.count(']')
        if bracket_count != 0:
            self.result.add_error(
                "DAX",
                f"Unbalanced brackets ({'+' if bracket_count > 0 else ''}{bracket_count})",
                f"Measure: {name}",
                details=expr[:100],
                suggestion="Check for missing or extra brackets"
            )
        
        # Check for unbalanced quotes
        single_quotes = expr.count("'")
        if single_quotes % 2 != 0:
            self.result.add_warning(
                "DAX",
                "Unbalanced single quotes",
                f"Measure: {name}",
                details=expr[:100],
                suggestion="Check for missing or extra quotes"
            )
        
        double_quotes = expr.count('"')
        if double_quotes % 2 != 0:
            self.result.add_warning(
                "DAX",
                "Unbalanced double quotes",
                f"Measure: {name}",
                details=expr[:100],
                suggestion="Check for missing or extra quotes"
            )
        
        # Extract and validate column references
        self._validate_column_references(expr, name)
        
        # Check for unknown functions
        self._validate_dax_functions(expr, name)
    
    def _validate_column_references(self, expr: str, measure_name: str) -> None:
        """Validate column references in a DAX expression."""
        # Pattern for column references: 'Table'[Column] or [Column]
        # Match table references: 'TableName'[ColumnName]
        table_col_pattern = r"'([^']+)'\[([^\]]+)\]"
        matches = re.findall(table_col_pattern, expr)
        
        for table_name, col_name in matches:
            if table_name not in self._table_names:
                self.result.add_warning(
                    "Reference",
                    f"Reference to unknown table: {table_name}",
                    f"Measure: {measure_name}",
                    details=f"Column reference: '{table_name}'[{col_name}]",
                    suggestion="Verify the table name is correct"
                )
            elif col_name not in self._column_refs.get(table_name, set()):
                self.result.add_warning(
                    "Reference",
                    f"Reference to unknown column: {col_name} in table {table_name}",
                    f"Measure: {measure_name}",
                    suggestion="Verify the column name is correct"
                )
        
        # Match unqualified column references: [ColumnName]
        # Exclude those already matched with table prefix
        unqualified_pattern = r"(?<!')\[([^\]]+)\]"
        unqualified_matches = re.findall(unqualified_pattern, expr)
        
        for col_name in unqualified_matches:
            # Check if column exists in any table
            found = False
            for table_cols in self._column_refs.values():
                if col_name in table_cols:
                    found = True
                    break
            
            if not found and col_name not in self.DAX_RESERVED:
                # Could be a measure reference or truly unknown
                self.result.add_info(
                    "Reference",
                    f"Unqualified column reference: [{col_name}]",
                    f"Measure: {measure_name}",
                )
    
    def _validate_dax_functions(self, expr: str, measure_name: str) -> None:
        """Check for unknown DAX functions."""
        # Pattern for function calls: FunctionName(
        func_pattern = r'([A-Za-z_][A-Za-z0-9_]*)\s*\('
        matches = re.findall(func_pattern, expr)
        
        for func_name in matches:
            if func_name.upper() not in self.DAX_FUNCTIONS:
                # Check if it's a common variation or typo
                self.result.add_info(
                    "DAX",
                    f"Non-standard function: {func_name}",
                    f"Measure: {measure_name}",
                )
    
    def _validate_pages(self, report: PowerBIReport) -> None:
        """Validate page and visual definitions."""
        if not report.pages:
            self.result.add_info(
                "Report",
                "No pages defined in the report",
                "Report",
            )
            return
        
        page_names_seen = set()
        
        for page in report.pages:
            # Check for duplicate page names
            if page.name in page_names_seen:
                self.result.add_warning(
                    "Report",
                    f"Duplicate page name: {page.name}",
                    f"Page: {page.name}",
                    suggestion="Rename one of the pages"
                )
            page_names_seen.add(page.name)
            
            # Check page dimensions
            if page.width <= 0 or page.height <= 0:
                self.result.add_error(
                    "Layout",
                    f"Invalid page dimensions: {page.width}x{page.height}",
                    f"Page: {page.name}",
                    suggestion="Set valid positive dimensions"
                )
            
            # Validate visuals
            self._validate_visuals(page)
    
    def _validate_visuals(self, page: PowerBIPage) -> None:
        """Validate visuals on a page."""
        for visual in page.visuals:
            # Check for valid position
            if visual.width <= 0 or visual.height <= 0:
                self.result.add_warning(
                    "Layout",
                    f"Visual has invalid size: {visual.width}x{visual.height}",
                    f"Page: {page.name}, Visual: {visual.name}",
                    suggestion="Set valid positive dimensions"
                )
            
            # Check for visuals outside page bounds
            if visual.x < 0 or visual.y < 0:
                self.result.add_warning(
                    "Layout",
                    f"Visual position is negative: ({visual.x}, {visual.y})",
                    f"Page: {page.name}, Visual: {visual.name}",
                )
            
            if visual.x + visual.width > page.width:
                self.result.add_info(
                    "Layout",
                    "Visual extends beyond page width",
                    f"Page: {page.name}, Visual: {visual.name}",
                )
            
            if visual.y + visual.height > page.height:
                self.result.add_info(
                    "Layout",
                    "Visual extends beyond page height",
                    f"Page: {page.name}, Visual: {visual.name}",
                )
            
            # Check for data bindings
            if not visual.category_fields and not visual.value_fields:
                self.result.add_info(
                    "DataBinding",
                    "Visual has no data bindings",
                    f"Page: {page.name}, Visual: {visual.name}",
                )
    
    def _validate_relationships(self, report: PowerBIReport) -> None:
        """Validate relationship definitions."""
        for rel in report.relationships:
            # Check that referenced tables exist
            if rel.from_table not in self._table_names:
                self.result.add_error(
                    "Relationship",
                    f"Relationship references unknown table: {rel.from_table}",
                    f"Relationship: {rel.name}",
                    suggestion="Verify the table name is correct"
                )
            
            if rel.to_table not in self._table_names:
                self.result.add_error(
                    "Relationship",
                    f"Relationship references unknown table: {rel.to_table}",
                    f"Relationship: {rel.name}",
                    suggestion="Verify the table name is correct"
                )
            
            # Check that referenced columns exist
            if rel.from_table in self._column_refs:
                if rel.from_column not in self._column_refs[rel.from_table]:
                    self.result.add_warning(
                        "Relationship",
                        f"Relationship references unknown column: {rel.from_column}",
                        f"Relationship: {rel.name}",
                        suggestion="Verify the column name is correct"
                    )
            
            if rel.to_table in self._column_refs:
                if rel.to_column not in self._column_refs[rel.to_table]:
                    self.result.add_warning(
                        "Relationship",
                        f"Relationship references unknown column: {rel.to_column}",
                        f"Relationship: {rel.name}",
                        suggestion="Verify the column name is correct"
                    )


def validate_conversion(report: PowerBIReport) -> ValidationResult:
    """
    Convenience function to validate a Power BI report.
    
    Args:
        report: Power BI report to validate
        
    Returns:
        ValidationResult with all issues found
    """
    validator = PreFlightValidator()
    return validator.validate(report)
