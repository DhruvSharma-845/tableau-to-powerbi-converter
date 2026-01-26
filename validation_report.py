"""
Validation Report Generator.

Generates comprehensive reports on the conversion process,
highlighting successful translations, issues, and items
requiring manual review.
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum

from models.tableau_models import TableauWorkbook, TableauCalculatedField
from models.powerbi_models import PowerBIReport, PowerBIMeasure
from translators.formula_translator import TranslationResult, TranslationConfidence
from translators.visual_mapper import VisualMappingResult, MappingConfidence


class SeverityLevel(Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""
    severity: SeverityLevel
    category: str
    component: str
    message: str
    suggestion: Optional[str] = None
    tableau_reference: Optional[str] = None
    powerbi_reference: Optional[str] = None


@dataclass
class ComponentSummary:
    """Summary statistics for a component type."""
    total: int = 0
    successful: int = 0
    warnings: int = 0
    errors: int = 0
    
    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 100.0
        return round(self.successful / self.total * 100, 1)


@dataclass
class ValidationReport:
    """Complete validation report for a conversion."""
    workbook_name: str
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Summaries
    overall_success_rate: float = 0.0
    formulas: ComponentSummary = field(default_factory=ComponentSummary)
    visuals: ComponentSummary = field(default_factory=ComponentSummary)
    data_sources: ComponentSummary = field(default_factory=ComponentSummary)
    parameters: ComponentSummary = field(default_factory=ComponentSummary)
    
    # Issues
    issues: List[ValidationIssue] = field(default_factory=list)
    
    # Detailed results
    formula_translations: List[Dict[str, Any]] = field(default_factory=list)
    visual_mappings: List[Dict[str, Any]] = field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "workbook_name": self.workbook_name,
            "generated_at": self.generated_at,
            "overall_success_rate": self.overall_success_rate,
            "summary": {
                "formulas": asdict(self.formulas),
                "visuals": asdict(self.visuals),
                "data_sources": asdict(self.data_sources),
                "parameters": asdict(self.parameters),
            },
            "issues": [
                {
                    "severity": issue.severity.value,
                    "category": issue.category,
                    "component": issue.component,
                    "message": issue.message,
                    "suggestion": issue.suggestion,
                    "tableau_reference": issue.tableau_reference,
                    "powerbi_reference": issue.powerbi_reference,
                }
                for issue in self.issues
            ],
            "formula_translations": self.formula_translations,
            "visual_mappings": self.visual_mappings,
            "recommendations": self.recommendations,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert report to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = [
            f"# Tableau to Power BI Conversion Report",
            f"",
            f"**Workbook:** {self.workbook_name}",
            f"**Generated:** {self.generated_at}",
            f"**Overall Success Rate:** {self.overall_success_rate}%",
            f"",
            "---",
            "",
            "## Summary",
            "",
            "| Component | Total | Successful | Warnings | Errors | Success Rate |",
            "|-----------|-------|------------|----------|--------|--------------|",
            f"| Formulas | {self.formulas.total} | {self.formulas.successful} | {self.formulas.warnings} | {self.formulas.errors} | {self.formulas.success_rate}% |",
            f"| Visuals | {self.visuals.total} | {self.visuals.successful} | {self.visuals.warnings} | {self.visuals.errors} | {self.visuals.success_rate}% |",
            f"| Data Sources | {self.data_sources.total} | {self.data_sources.successful} | {self.data_sources.warnings} | {self.data_sources.errors} | {self.data_sources.success_rate}% |",
            f"| Parameters | {self.parameters.total} | {self.parameters.successful} | {self.parameters.warnings} | {self.parameters.errors} | {self.parameters.success_rate}% |",
            "",
        ]
        
        # Issues section
        if self.issues:
            lines.extend([
                "---",
                "",
                "## Issues Requiring Attention",
                "",
            ])
            
            # Group by severity
            for severity in [SeverityLevel.CRITICAL, SeverityLevel.ERROR, 
                           SeverityLevel.WARNING, SeverityLevel.INFO]:
                severity_issues = [i for i in self.issues if i.severity == severity]
                if severity_issues:
                    icon = {"critical": "🔴", "error": "🟠", "warning": "🟡", "info": "🔵"}
                    lines.append(f"### {icon.get(severity.value, '')} {severity.value.upper()}")
                    lines.append("")
                    
                    for issue in severity_issues:
                        lines.append(f"- **{issue.category}** - {issue.component}")
                        lines.append(f"  - {issue.message}")
                        if issue.suggestion:
                            lines.append(f"  - *Suggestion:* {issue.suggestion}")
                        lines.append("")
        
        # Formula translations
        if self.formula_translations:
            lines.extend([
                "---",
                "",
                "## Formula Translations",
                "",
            ])
            
            # Group by confidence
            high_conf = [f for f in self.formula_translations if f.get("confidence") == "high"]
            med_conf = [f for f in self.formula_translations if f.get("confidence") == "medium"]
            low_conf = [f for f in self.formula_translations if f.get("confidence") == "low"]
            failed = [f for f in self.formula_translations if f.get("confidence") == "failed"]
            
            if failed:
                lines.append("### Failed Translations")
                lines.append("")
                for f in failed:
                    lines.append(f"#### {f['name']}")
                    lines.append(f"```")
                    lines.append(f"Tableau: {f['source_formula']}")
                    lines.append(f"```")
                    lines.append(f"*Error:* {', '.join(f.get('notes', []))}")
                    lines.append("")
            
            if low_conf:
                lines.append("### Low Confidence (Needs Review)")
                lines.append("")
                for f in low_conf:
                    lines.append(f"<details>")
                    lines.append(f"<summary>{f['name']}</summary>")
                    lines.append(f"")
                    lines.append(f"**Tableau:**")
                    lines.append(f"```")
                    lines.append(f"{f['source_formula']}")
                    lines.append(f"```")
                    lines.append(f"**DAX:**")
                    lines.append(f"```dax")
                    lines.append(f"{f['dax_expression']}")
                    lines.append(f"```")
                    if f.get('notes'):
                        lines.append(f"**Notes:** {', '.join(f['notes'])}")
                    lines.append(f"</details>")
                    lines.append("")
            
            lines.append(f"### Translation Summary")
            lines.append(f"- High confidence: {len(high_conf)}")
            lines.append(f"- Medium confidence: {len(med_conf)}")
            lines.append(f"- Low confidence: {len(low_conf)}")
            lines.append(f"- Failed: {len(failed)}")
            lines.append("")
        
        # Recommendations
        if self.recommendations:
            lines.extend([
                "---",
                "",
                "## Recommendations",
                "",
            ])
            for rec in self.recommendations:
                lines.append(f"- {rec}")
            lines.append("")
        
        return "\n".join(lines)


class ValidationReportGenerator:
    """
    Generates validation reports for Tableau to Power BI conversions.
    """
    
    def __init__(self):
        """Initialize the validation report generator."""
        self.issues: List[ValidationIssue] = []
    
    def generate(self, 
                 workbook: TableauWorkbook,
                 report: PowerBIReport,
                 formula_results: List[tuple],
                 visual_results: List[VisualMappingResult]) -> ValidationReport:
        """
        Generate a validation report for a conversion.
        
        Args:
            workbook: Original Tableau workbook
            report: Generated Power BI report
            formula_results: List of (TableauCalculatedField, TranslationResult) tuples
            visual_results: List of VisualMappingResult objects
            
        Returns:
            ValidationReport with all validation details
        """
        self.issues = []
        
        validation = ValidationReport(workbook_name=workbook.name)
        
        # Validate formulas
        validation.formulas = self._validate_formulas(formula_results)
        validation.formula_translations = self._get_formula_details(formula_results)
        
        # Validate visuals
        validation.visuals = self._validate_visuals(visual_results)
        validation.visual_mappings = self._get_visual_details(visual_results)
        
        # Validate data sources
        validation.data_sources = self._validate_data_sources(workbook, report)
        
        # Validate parameters
        validation.parameters = self._validate_parameters(workbook)
        
        # Check for unsupported features
        self._check_unsupported_features(workbook)
        
        # Calculate overall success rate
        total = (validation.formulas.total + validation.visuals.total + 
                validation.data_sources.total + validation.parameters.total)
        successful = (validation.formulas.successful + validation.visuals.successful + 
                     validation.data_sources.successful + validation.parameters.successful)
        
        if total > 0:
            validation.overall_success_rate = round(successful / total * 100, 1)
        else:
            validation.overall_success_rate = 100.0
        
        # Add all issues
        validation.issues = self.issues
        
        # Generate recommendations
        validation.recommendations = self._generate_recommendations(validation)
        
        return validation
    
    def _validate_formulas(self, formula_results: List[tuple]) -> ComponentSummary:
        """Validate formula translations."""
        summary = ComponentSummary(total=len(formula_results))
        
        for calc_field, result in formula_results:
            if result.confidence == TranslationConfidence.HIGH:
                summary.successful += 1
            elif result.confidence == TranslationConfidence.MEDIUM:
                summary.successful += 1
                summary.warnings += 1
                self.issues.append(ValidationIssue(
                    severity=SeverityLevel.WARNING,
                    category="Formula Translation",
                    component=calc_field.display_name,
                    message=f"Medium confidence translation - verify behavior",
                    suggestion="Compare output values with Tableau for sample data",
                    tableau_reference=calc_field.formula,
                    powerbi_reference=result.dax_expression,
                ))
            elif result.confidence == TranslationConfidence.LOW:
                summary.warnings += 1
                self.issues.append(ValidationIssue(
                    severity=SeverityLevel.WARNING,
                    category="Formula Translation",
                    component=calc_field.display_name,
                    message=f"Low confidence translation - requires manual review",
                    suggestion="Review DAX logic and test thoroughly",
                    tableau_reference=calc_field.formula,
                    powerbi_reference=result.dax_expression,
                ))
            else:
                summary.errors += 1
                self.issues.append(ValidationIssue(
                    severity=SeverityLevel.ERROR,
                    category="Formula Translation",
                    component=calc_field.display_name,
                    message=f"Translation failed: {', '.join(result.notes)}",
                    suggestion="Manually recreate this calculation in DAX",
                    tableau_reference=calc_field.formula,
                ))
            
            # Check for specific problematic patterns
            if calc_field.is_table_calc:
                self.issues.append(ValidationIssue(
                    severity=SeverityLevel.WARNING,
                    category="Table Calculation",
                    component=calc_field.display_name,
                    message="Table calculations have different semantics in Power BI",
                    suggestion="Verify calculation direction (WINDOW function ORDERBY clause)",
                    tableau_reference=calc_field.table_calc_type,
                ))
        
        return summary
    
    def _validate_visuals(self, visual_results: List[VisualMappingResult]) -> ComponentSummary:
        """Validate visual mappings."""
        summary = ComponentSummary(total=len(visual_results))
        
        for result in visual_results:
            if result.confidence == MappingConfidence.EXACT:
                summary.successful += 1
            elif result.confidence == MappingConfidence.GOOD:
                summary.successful += 1
            elif result.confidence == MappingConfidence.PARTIAL:
                summary.warnings += 1
                self.issues.append(ValidationIssue(
                    severity=SeverityLevel.WARNING,
                    category="Visual Mapping",
                    component=result.powerbi_visual.source_tableau_worksheet or "Unknown",
                    message=f"Partial mapping - some features may not translate",
                    suggestion="; ".join(result.notes) if result.notes else "Review visual configuration",
                ))
            elif result.confidence == MappingConfidence.CUSTOM:
                summary.warnings += 1
                self.issues.append(ValidationIssue(
                    severity=SeverityLevel.WARNING,
                    category="Visual Mapping",
                    component=result.powerbi_visual.source_tableau_worksheet or "Unknown",
                    message="Requires custom visual from marketplace",
                    suggestion=f"Install custom visual: {result.custom_visual_id}",
                ))
            else:
                summary.errors += 1
                self.issues.append(ValidationIssue(
                    severity=SeverityLevel.ERROR,
                    category="Visual Mapping",
                    component=result.powerbi_visual.source_tableau_worksheet or "Unknown",
                    message="No equivalent visual type in Power BI",
                    suggestion="Consider alternative visualization or custom visual",
                ))
            
            # Check for unmapped features
            if result.unmapped_features:
                for feature in result.unmapped_features:
                    self.issues.append(ValidationIssue(
                        severity=SeverityLevel.INFO,
                        category="Unmapped Feature",
                        component=result.powerbi_visual.source_tableau_worksheet or "Unknown",
                        message=f"Feature not mapped: {feature}",
                    ))
        
        return summary
    
    def _validate_data_sources(self, workbook: TableauWorkbook, 
                               report: PowerBIReport) -> ComponentSummary:
        """Validate data source conversions."""
        summary = ComponentSummary(total=len(workbook.datasources))
        
        for ds in workbook.datasources:
            if ds.connection:
                conn_type = ds.connection.class_name or "unknown"
                
                # Check if connection type is supported
                supported_types = ["sqlserver", "postgres", "mysql", "oracle", 
                                  "snowflake", "bigquery", "excel", "textscan"]
                
                if conn_type.lower() in supported_types:
                    summary.successful += 1
                elif conn_type.lower() == "hyper":
                    summary.warnings += 1
                    self.issues.append(ValidationIssue(
                        severity=SeverityLevel.WARNING,
                        category="Data Source",
                        component=ds.display_name,
                        message="Tableau extract (.hyper) - data will need to be re-imported",
                        suggestion="Export data from Tableau or connect to original source",
                    ))
                else:
                    summary.warnings += 1
                    self.issues.append(ValidationIssue(
                        severity=SeverityLevel.WARNING,
                        category="Data Source",
                        component=ds.display_name,
                        message=f"Unknown connection type: {conn_type}",
                        suggestion="Manually configure data source in Power BI",
                    ))
            else:
                summary.warnings += 1
                self.issues.append(ValidationIssue(
                    severity=SeverityLevel.INFO,
                    category="Data Source",
                    component=ds.display_name,
                    message="No connection information found",
                ))
        
        return summary
    
    def _validate_parameters(self, workbook: TableauWorkbook) -> ComponentSummary:
        """Validate parameter conversions."""
        summary = ComponentSummary(total=len(workbook.parameters))
        
        for param in workbook.parameters:
            summary.warnings += 1  # All parameters need manual setup
            
            self.issues.append(ValidationIssue(
                severity=SeverityLevel.WARNING,
                category="Parameter",
                component=param.display_name,
                message="Parameters require manual setup in Power BI",
                suggestion=f"Create as What-If parameter or slicer (type: {param.allowable_values_type})",
                tableau_reference=f"Current value: {param.current_value}",
            ))
        
        return summary
    
    def _check_unsupported_features(self, workbook: TableauWorkbook) -> None:
        """Check for features that have no Power BI equivalent."""
        # Check for dashboard actions
        for dashboard in workbook.dashboards:
            if dashboard.actions:
                for action in dashboard.actions:
                    self.issues.append(ValidationIssue(
                        severity=SeverityLevel.WARNING,
                        category="Dashboard Action",
                        component=dashboard.name,
                        message=f"Action '{action.get('name', 'Unknown')}' requires manual setup",
                        suggestion="Configure as Power BI drillthrough or cross-filter",
                    ))
        
        # Check for complex LOD expressions
        for ds in workbook.datasources:
            for calc in ds.calculated_fields:
                if len(calc.lod_dimensions) > 2:
                    self.issues.append(ValidationIssue(
                        severity=SeverityLevel.INFO,
                        category="Complex LOD",
                        component=calc.display_name,
                        message=f"LOD with {len(calc.lod_dimensions)} dimensions - verify performance",
                        suggestion="Consider breaking into multiple measures or using calculated tables",
                    ))
    
    def _get_formula_details(self, formula_results: List[tuple]) -> List[Dict[str, Any]]:
        """Get detailed formula translation information."""
        details = []
        
        for calc_field, result in formula_results:
            details.append({
                "name": calc_field.display_name,
                "source_formula": calc_field.formula,
                "dax_expression": result.dax_expression,
                "confidence": result.confidence.value,
                "requires_review": result.requires_review,
                "notes": result.notes,
                "calculation_type": calc_field.calculation_type.value,
            })
        
        return details
    
    def _get_visual_details(self, visual_results: List[VisualMappingResult]) -> List[Dict[str, Any]]:
        """Get detailed visual mapping information."""
        details = []
        
        for result in visual_results:
            details.append({
                "tableau_worksheet": result.powerbi_visual.source_tableau_worksheet,
                "powerbi_visual_type": result.powerbi_visual.visual_type.value,
                "confidence": result.confidence.value,
                "requires_custom_visual": result.requires_custom_visual,
                "custom_visual_id": result.custom_visual_id,
                "notes": result.notes,
                "unmapped_features": result.unmapped_features,
            })
        
        return details
    
    def _generate_recommendations(self, validation: ValidationReport) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Based on success rates
        if validation.formulas.success_rate < 80:
            recommendations.append(
                "Formula success rate is below 80% - consider reviewing complex "
                "calculations before importing and prioritize manual review of "
                "failed translations."
            )
        
        if validation.formulas.errors > 0:
            recommendations.append(
                f"{validation.formulas.errors} formula(s) failed to translate. "
                "Review these manually and recreate in DAX."
            )
        
        # Table calculations
        table_calc_issues = [i for i in validation.issues 
                           if i.category == "Table Calculation"]
        if table_calc_issues:
            recommendations.append(
                f"Found {len(table_calc_issues)} table calculations. These require "
                "careful review as they behave differently in Power BI. "
                "Test with sample data to verify results match."
            )
        
        # Parameters
        if validation.parameters.total > 0:
            recommendations.append(
                f"Found {validation.parameters.total} parameter(s). Create these as "
                "What-If parameters or slicers in Power BI. The generated measures "
                "reference parameter tables that need to be created."
            )
        
        # Custom visuals
        custom_visual_issues = [i for i in validation.issues 
                               if "custom visual" in i.message.lower()]
        if custom_visual_issues:
            recommendations.append(
                "Some visuals require custom visuals from AppSource. "
                "Install these before importing the report."
            )
        
        # Data sources
        hyper_issues = [i for i in validation.issues 
                       if "hyper" in i.message.lower() or "extract" in i.message.lower()]
        if hyper_issues:
            recommendations.append(
                "Tableau extract data detected. You'll need to export this data "
                "or connect directly to the original data source in Power BI."
            )
        
        # General recommendations
        if validation.overall_success_rate >= 90:
            recommendations.append(
                "High success rate achieved! Review flagged items and test the "
                "report with representative data before deployment."
            )
        elif validation.overall_success_rate >= 70:
            recommendations.append(
                "Moderate success rate. Plan for some manual adjustment work, "
                "especially for complex calculations and visualizations."
            )
        else:
            recommendations.append(
                "Lower success rate indicates significant manual work needed. "
                "Consider a phased approach, converting simpler reports first."
            )
        
        return recommendations
    
    def save_report(self, report: ValidationReport, output_path: str, 
                   format: str = "markdown") -> Path:
        """
        Save validation report to file.
        
        Args:
            report: ValidationReport to save
            output_path: Path to save the report
            format: "markdown", "json", or "html"
            
        Returns:
            Path to saved file
        """
        output = Path(output_path)
        
        if format == "json":
            content = report.to_json()
            if not output.suffix:
                output = output.with_suffix(".json")
        elif format == "html":
            # Convert markdown to basic HTML
            md = report.to_markdown()
            content = f"<html><body><pre>{md}</pre></body></html>"
            if not output.suffix:
                output = output.with_suffix(".html")
        else:
            content = report.to_markdown()
            if not output.suffix:
                output = output.with_suffix(".md")
        
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, 'w') as f:
            f.write(content)
        
        return output
