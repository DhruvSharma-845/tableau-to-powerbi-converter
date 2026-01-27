#!/usr/bin/env python3
"""
Tableau to Power BI Converter

A command-line tool for converting Tableau workbooks (.twbx/.twb) 
to Power BI reports in PBIR format.

Usage:
    python main.py convert <workbook> -o <output_dir>
    python main.py batch <directory> -o <output_dir>
    python main.py validate <workbook>
    python main.py analyze <workbook>
"""

import os
import sys
import platform
from pathlib import Path
from typing import Optional, List
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.syntax import Syntax

# Fix Windows console encoding issues
if platform.system() == "Windows":
    # Force UTF-8 mode on Windows
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add package to path
sys.path.insert(0, str(Path(__file__).parent))

from parsers.twbx_parser import TWBXParser
from translators.formula_translator import FormulaTranslator
from translators.visual_mapper import VisualMapper
from generators.pbir_generator import PBIRGenerator
from generators.semantic_model_generator import SemanticModelGenerator
from validation_report import ValidationReportGenerator, ValidationReport


# Use force_terminal=False on Windows to avoid legacy console issues
console = Console(force_terminal=False if platform.system() == "Windows" else None)


class TableauToPowerBIConverter:
    """Main converter class that orchestrates the conversion process."""
    
    def __init__(self, use_genai: bool = True, openai_api_key: Optional[str] = None):
        """
        Initialize the converter.
        
        Args:
            use_genai: Whether to use GenAI for complex translations
            openai_api_key: OpenAI API key (or from environment)
        """
        self.use_genai = use_genai
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        
        self.formula_translator = FormulaTranslator(
            use_genai=use_genai,
            openai_api_key=self.openai_api_key
        )
        self.visual_mapper = VisualMapper()
        self.validation_generator = ValidationReportGenerator()
    
    def convert(self, input_path: str, output_dir: str, 
                generate_report: bool = True) -> tuple:
        """
        Convert a Tableau workbook to Power BI format.
        
        Args:
            input_path: Path to .twbx or .twb file
            output_dir: Directory for output files
            generate_report: Whether to generate validation report
            
        Returns:
            Tuple of (output_path, validation_report)
        """
        # Parse Tableau workbook
        console.print(f"[cyan]Parsing Tableau workbook: {input_path}[/cyan]")
        parser = TWBXParser(input_path)
        workbook = parser.parse()
        
        console.print(f"  Found {len(workbook.datasources)} data source(s)")
        console.print(f"  Found {len(workbook.worksheets)} worksheet(s)")
        console.print(f"  Found {len(workbook.dashboards)} dashboard(s)")
        console.print(f"  Found {workbook.total_calculated_fields} calculated field(s)")
        
        # Generate semantic model
        console.print("\n[cyan]Generating semantic model...[/cyan]")
        model_generator = SemanticModelGenerator(
            use_genai=self.use_genai,
            openai_api_key=self.openai_api_key
        )
        report = model_generator.generate(workbook)
        
        # Map visuals
        console.print("[cyan]Mapping visualizations...[/cyan]")
        visual_results = []
        worksheets_dict = {ws.name: ws for ws in workbook.worksheets}
        
        for worksheet in workbook.worksheets:
            result = self.visual_mapper.map_worksheet(worksheet)
            visual_results.append(result)
        
        # Map dashboards to pages
        for dashboard in workbook.dashboards:
            page = self.visual_mapper.map_dashboard_to_page(dashboard, worksheets_dict)
            report.pages.append(page)
        
        # If no dashboards, create pages from worksheets
        if not workbook.dashboards:
            for result in visual_results:
                from models.powerbi_models import PowerBIPage
                page = PowerBIPage(
                    name=result.powerbi_visual.source_tableau_worksheet or "Page1",
                    display_name=result.powerbi_visual.title,
                    visuals=[result.powerbi_visual]
                )
                report.pages.append(page)
        
        # Generate PBIR output
        console.print("[cyan]Generating Power BI PBIR files...[/cyan]")
        pbir_generator = PBIRGenerator(output_dir)
        output_path = pbir_generator.generate(report)
        
        console.print(f"  Output: {output_path}")
        
        # Generate validation report
        validation_report = None
        if generate_report:
            console.print("\n[cyan]Generating validation report...[/cyan]")
            validation_report = self.validation_generator.generate(
                workbook=workbook,
                report=report,
                formula_results=model_generator.translation_results,
                visual_results=visual_results
            )
            
            # Save report
            report_path = Path(output_dir) / f"{workbook.name}_validation_report.md"
            self.validation_generator.save_report(validation_report, str(report_path))
            console.print(f"  Report: {report_path}")
        
        return output_path, validation_report
    
    def analyze(self, input_path: str) -> dict:
        """
        Analyze a Tableau workbook without converting.
        
        Args:
            input_path: Path to .twbx or .twb file
            
        Returns:
            Analysis results dictionary
        """
        parser = TWBXParser(input_path)
        workbook = parser.parse()
        
        # Analyze complexity
        calc_fields = workbook.get_all_calculated_fields()
        
        lod_count = sum(1 for c in calc_fields if c.is_lod)
        table_calc_count = sum(1 for c in calc_fields if c.is_table_calc)
        simple_count = len(calc_fields) - lod_count - table_calc_count
        
        # Estimate conversion difficulty
        difficulty_score = (
            simple_count * 1 +
            lod_count * 3 +
            table_calc_count * 5 +
            len(workbook.parameters) * 2
        )
        
        if difficulty_score < 20:
            difficulty = "Low"
        elif difficulty_score < 50:
            difficulty = "Medium"
        elif difficulty_score < 100:
            difficulty = "High"
        else:
            difficulty = "Very High"
        
        return {
            "name": workbook.name,
            "version": workbook.version,
            "datasources": len(workbook.datasources),
            "worksheets": len(workbook.worksheets),
            "dashboards": len(workbook.dashboards),
            "total_fields": workbook.total_fields,
            "calculated_fields": {
                "total": len(calc_fields),
                "simple": simple_count,
                "lod_expressions": lod_count,
                "table_calculations": table_calc_count,
            },
            "parameters": len(workbook.parameters),
            "has_extract": workbook.has_extract,
            "difficulty": difficulty,
            "difficulty_score": difficulty_score,
        }


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Tableau to Power BI Converter - Convert Tableau workbooks to Power BI format."""
    pass


@cli.command()
@click.argument('workbook', type=click.Path(exists=True))
@click.option('-o', '--output', 'output_dir', required=True, 
              type=click.Path(), help='Output directory')
@click.option('--no-genai', is_flag=True, 
              help='Disable GenAI for formula translation')
@click.option('--api-key', envvar='OPENAI_API_KEY', 
              help='OpenAI API key for GenAI translation')
@click.option('--no-report', is_flag=True, 
              help='Skip validation report generation')
def convert(workbook: str, output_dir: str, no_genai: bool, 
            api_key: Optional[str], no_report: bool):
    """Convert a single Tableau workbook to Power BI format."""
    
    console.print(Panel.fit(
        "[bold blue]Tableau to Power BI Converter[/bold blue]",
        subtitle="Single File Conversion"
    ))
    
    try:
        converter = TableauToPowerBIConverter(
            use_genai=not no_genai,
            openai_api_key=api_key
        )
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Converting...", total=None)
            output_path, validation = converter.convert(
                workbook, output_dir, 
                generate_report=not no_report
            )
        
        # Display summary
        console.print("\n[bold green]Conversion Complete![/bold green]")
        console.print(f"Output: {output_path}")
        
        if validation:
            console.print(f"\n[bold]Conversion Summary:[/bold]")
            
            table = Table(show_header=True, header_style="bold")
            table.add_column("Component")
            table.add_column("Total", justify="right")
            table.add_column("Success", justify="right")
            table.add_column("Rate", justify="right")
            
            table.add_row(
                "Formulas",
                str(validation.formulas.total),
                str(validation.formulas.successful),
                f"{validation.formulas.success_rate}%"
            )
            table.add_row(
                "Visuals",
                str(validation.visuals.total),
                str(validation.visuals.successful),
                f"{validation.visuals.success_rate}%"
            )
            
            console.print(table)
            console.print(f"\n[bold]Overall Success Rate: {validation.overall_success_rate}%[/bold]")
            
            # Show critical issues
            critical = [i for i in validation.issues if i.severity.value in ['critical', 'error']]
            if critical:
                console.print(f"\n[bold red]Issues requiring attention: {len(critical)}[/bold red]")
                for issue in critical[:5]:
                    console.print(f"  - [{issue.severity.value.upper()}] {issue.component}: {issue.message}")
                if len(critical) > 5:
                    console.print(f"  ... and {len(critical) - 5} more (see validation report)")
    
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        raise click.Abort()


@cli.command()
@click.argument('directory', type=click.Path(exists=True))
@click.option('-o', '--output', 'output_dir', required=True, 
              type=click.Path(), help='Output directory')
@click.option('--no-genai', is_flag=True, 
              help='Disable GenAI for formula translation')
@click.option('--api-key', envvar='OPENAI_API_KEY', 
              help='OpenAI API key for GenAI translation')
@click.option('--pattern', default='*.twbx', 
              help='File pattern to match (default: *.twbx)')
def batch(directory: str, output_dir: str, no_genai: bool, 
          api_key: Optional[str], pattern: str):
    """Batch convert multiple Tableau workbooks."""
    
    console.print(Panel.fit(
        "[bold blue]Tableau to Power BI Converter[/bold blue]",
        subtitle="Batch Conversion"
    ))
    
    # Find all matching files
    input_dir = Path(directory)
    files = list(input_dir.glob(pattern))
    
    if not files:
        console.print(f"[yellow]No files matching '{pattern}' found in {directory}[/yellow]")
        return
    
    console.print(f"Found {len(files)} file(s) to convert")
    
    converter = TableauToPowerBIConverter(
        use_genai=not no_genai,
        openai_api_key=api_key
    )
    
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task("Converting workbooks...", total=len(files))
        
        for file_path in files:
            try:
                progress.update(task, description=f"Converting {file_path.name}...")
                
                file_output_dir = Path(output_dir) / file_path.stem
                output_path, validation = converter.convert(
                    str(file_path), str(file_output_dir)
                )
                
                results.append({
                    "file": file_path.name,
                    "status": "success",
                    "success_rate": validation.overall_success_rate if validation else 0,
                    "output": str(output_path)
                })
                
            except Exception as e:
                results.append({
                    "file": file_path.name,
                    "status": "failed",
                    "error": str(e)
                })
            
            progress.advance(task)
    
    # Display results
    console.print("\n[bold]Batch Conversion Results:[/bold]")
    
    table = Table(show_header=True, header_style="bold")
    table.add_column("File")
    table.add_column("Status")
    table.add_column("Success Rate", justify="right")
    
    for result in results:
        status_color = "green" if result["status"] == "success" else "red"
        rate = f"{result.get('success_rate', 0)}%" if result["status"] == "success" else "-"
        table.add_row(
            result["file"],
            f"[{status_color}]{result['status']}[/{status_color}]",
            rate
        )
    
    console.print(table)
    
    successful = sum(1 for r in results if r["status"] == "success")
    console.print(f"\n[bold]Completed: {successful}/{len(files)} files converted successfully[/bold]")


@cli.command()
@click.argument('workbook', type=click.Path(exists=True))
@click.option('-o', '--output', 'output_path', 
              type=click.Path(), help='Output path for validation report')
@click.option('--format', 'report_format', 
              type=click.Choice(['markdown', 'json', 'html']), 
              default='markdown', help='Report format')
def validate(workbook: str, output_path: Optional[str], report_format: str):
    """Generate a validation report for a Tableau workbook without converting."""
    
    console.print(Panel.fit(
        "[bold blue]Tableau to Power BI Converter[/bold blue]",
        subtitle="Validation Report"
    ))
    
    try:
        # Parse and analyze
        parser = TWBXParser(workbook)
        wb = parser.parse()
        
        # Generate semantic model (for formula translation)
        model_gen = SemanticModelGenerator(use_genai=False)
        report = model_gen.generate(wb)
        
        # Map visuals
        visual_mapper = VisualMapper()
        visual_results = [visual_mapper.map_worksheet(ws) for ws in wb.worksheets]
        
        # Generate validation report
        validator = ValidationReportGenerator()
        validation = validator.generate(
            workbook=wb,
            report=report,
            formula_results=model_gen.translation_results,
            visual_results=visual_results
        )
        
        # Output report
        if output_path:
            saved_path = validator.save_report(validation, output_path, report_format)
            console.print(f"Report saved to: {saved_path}")
        else:
            # Print to console
            console.print(validation.to_markdown())
    
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        raise click.Abort()


@cli.command()
@click.argument('workbook', type=click.Path(exists=True))
def analyze(workbook: str):
    """Analyze a Tableau workbook and estimate conversion difficulty."""
    
    console.print(Panel.fit(
        "[bold blue]Tableau to Power BI Converter[/bold blue]",
        subtitle="Workbook Analysis"
    ))
    
    try:
        converter = TableauToPowerBIConverter(use_genai=False)
        analysis = converter.analyze(workbook)
        
        console.print(f"\n[bold]Workbook: {analysis['name']}[/bold]")
        console.print(f"Version: {analysis['version']}")
        
        console.print("\n[bold]Components:[/bold]")
        table = Table(show_header=False)
        table.add_column("Component", style="cyan")
        table.add_column("Count", justify="right")
        
        table.add_row("Data Sources", str(analysis['datasources']))
        table.add_row("Worksheets", str(analysis['worksheets']))
        table.add_row("Dashboards", str(analysis['dashboards']))
        table.add_row("Total Fields", str(analysis['total_fields']))
        table.add_row("Parameters", str(analysis['parameters']))
        
        console.print(table)
        
        console.print("\n[bold]Calculated Fields:[/bold]")
        calc_table = Table(show_header=False)
        calc_table.add_column("Type", style="cyan")
        calc_table.add_column("Count", justify="right")
        
        calc_fields = analysis['calculated_fields']
        calc_table.add_row("Simple", str(calc_fields['simple']))
        calc_table.add_row("LOD Expressions", str(calc_fields['lod_expressions']))
        calc_table.add_row("Table Calculations", str(calc_fields['table_calculations']))
        calc_table.add_row("[bold]Total[/bold]", f"[bold]{calc_fields['total']}[/bold]")
        
        console.print(calc_table)
        
        # Difficulty assessment
        difficulty_color = {
            "Low": "green",
            "Medium": "yellow",
            "High": "orange3",
            "Very High": "red"
        }.get(analysis['difficulty'], "white")
        
        console.print(f"\n[bold]Conversion Difficulty: [{difficulty_color}]{analysis['difficulty']}[/{difficulty_color}][/bold]")
        console.print(f"Difficulty Score: {analysis['difficulty_score']}")
        
        if analysis['has_extract']:
            console.print("\n[yellow]Note: Workbook contains Tableau extract data (.hyper).[/yellow]")
            console.print("[yellow]You'll need to re-import this data in Power BI.[/yellow]")
        
        # Recommendations
        console.print("\n[bold]Recommendations:[/bold]")
        
        if analysis['difficulty'] == "Low":
            console.print("  - This workbook should convert smoothly")
            console.print("  - Run the converter and review the validation report")
        elif analysis['difficulty'] == "Medium":
            console.print("  - Some manual adjustments may be needed")
            console.print("  - Pay attention to LOD expressions and parameters")
        elif analysis['difficulty'] == "High":
            console.print("  - Significant manual work expected")
            console.print("  - Review table calculations carefully")
            console.print("  - Consider phased conversion approach")
        else:
            console.print("  - Complex workbook - expect substantial manual effort")
            console.print("  - Consider simplifying Tableau workbook first")
            console.print("  - May want to rebuild some visuals from scratch")
    
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        raise click.Abort()


@cli.command()
def mappings():
    """Show all visual type mappings."""
    
    console.print(Panel.fit(
        "[bold blue]Visual Type Mappings[/bold blue]",
        subtitle="Tableau to Power BI"
    ))
    
    mappings = VisualMapper.get_all_mappings()
    
    table = Table(show_header=True, header_style="bold")
    table.add_column("Tableau Mark Type")
    table.add_column("Power BI Visual")
    table.add_column("Confidence")
    table.add_column("Custom Visual")
    
    for mark_type, mapping in mappings.items():
        confidence_color = {
            "exact": "green",
            "good": "green",
            "partial": "yellow",
            "custom": "orange3",
            "unsupported": "red"
        }.get(mapping["confidence"], "white")
        
        table.add_row(
            mark_type,
            mapping["powerbi_visual"],
            f"[{confidence_color}]{mapping['confidence']}[/{confidence_color}]",
            mapping.get("custom_visual") or "-"
        )
    
    console.print(table)


@cli.command()
@click.argument('pbip_path', type=click.Path(exists=True))
@click.option('-o', '--output', 'output_path', 
              type=click.Path(), help='Output PBIX file path')
@click.option('--workspace', '-w', envvar='POWERBI_WORKSPACE_ID',
              help='Power BI workspace ID')
@click.option('--no-cleanup', is_flag=True,
              help='Keep temporary report in Power BI Service after conversion')
def to_pbix(pbip_path: str, output_path: Optional[str], 
            workspace: Optional[str], no_cleanup: bool):
    """Convert PBIP folder to PBIX via Power BI Service.
    
    This command uploads the PBIP to Power BI Service and downloads it
    as a PBIX file. Requires Azure AD authentication.
    
    Required environment variable:
        AZURE_TENANT_ID - Your Azure AD tenant ID
    
    Optional environment variables (for service principal auth):
        AZURE_CLIENT_ID - Service principal client ID
        AZURE_CLIENT_SECRET - Service principal secret
    """
    
    console.print(Panel.fit(
        "[bold blue]PBIP to PBIX Converter[/bold blue]",
        subtitle="via Power BI Service"
    ))
    
    # Check for tenant ID
    if not os.environ.get("AZURE_TENANT_ID"):
        console.print("\n[bold red]Error: AZURE_TENANT_ID environment variable is required[/bold red]")
        console.print("\nTo set it up:")
        console.print("  1. Go to https://portal.azure.com")
        console.print("  2. Search for 'Azure Active Directory'")
        console.print("  3. Copy the 'Tenant ID' from the Overview page")
        console.print("\nThen run:")
        console.print("  [cyan]export AZURE_TENANT_ID='your-tenant-id-here'[/cyan]")
        raise click.Abort()
    
    # Determine output path
    if not output_path:
        pbip_name = Path(pbip_path).stem
        output_path = str(Path(pbip_path).parent / f"{pbip_name}.pbix")
    
    try:
        from powerbi_service import PowerBIServiceClient
        
        client = PowerBIServiceClient()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Converting to PBIX...", total=None)
            
            result_path = client.convert_pbip_to_pbix(
                pbip_path,
                output_path,
                workspace_id=workspace,
                cleanup=not no_cleanup
            )
        
        console.print(f"\n[bold green]Conversion Complete![/bold green]")
        console.print(f"Output: {result_path}")
    
    except ImportError as e:
        console.print(f"[bold red]Error: Missing dependency - {e}[/bold red]")
        console.print("Run: pip install requests")
        raise click.Abort()
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        raise click.Abort()


@cli.command()
@click.option('--workspace', '-w', envvar='POWERBI_WORKSPACE_ID',
              help='Power BI workspace ID')
def workspaces(workspace: Optional[str]):
    """List available Power BI workspaces.
    
    Requires AZURE_TENANT_ID environment variable.
    """
    
    console.print(Panel.fit(
        "[bold blue]Power BI Workspaces[/bold blue]"
    ))
    
    if not os.environ.get("AZURE_TENANT_ID"):
        console.print("\n[bold red]Error: AZURE_TENANT_ID environment variable is required[/bold red]")
        raise click.Abort()
    
    try:
        from powerbi_service import PowerBIServiceClient
        
        client = PowerBIServiceClient()
        ws_list = client.list_workspaces()
        
        if not ws_list:
            console.print("\n[yellow]No workspaces found.[/yellow]")
            return
        
        table = Table(show_header=True, header_style="bold")
        table.add_column("Workspace Name")
        table.add_column("Workspace ID")
        
        for ws in ws_list:
            table.add_row(ws['name'], ws['id'])
        
        console.print(table)
        console.print(f"\n[dim]Set POWERBI_WORKSPACE_ID to use a specific workspace[/dim]")
    
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        raise click.Abort()


if __name__ == "__main__":
    cli()
