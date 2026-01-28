"""
Semantic Model Generator for Power BI.

Generates the Power BI semantic model (data model) including:
- Tables and columns
- DAX measures (translated from Tableau calculated fields)
- Relationships between tables
- Data source connections
"""

import uuid
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

from models.tableau_models import (
    TableauWorkbook, TableauDataSource, TableauCalculatedField,
    TableauParameter, DataType
)
from models.powerbi_models import (
    PowerBIReport, PowerBITable, PowerBIColumn, PowerBIMeasure,
    PowerBIDataSource, PowerBIRelationship, PowerBIDataType
)
from translators.formula_translator import FormulaTranslator, TranslationResult


class SemanticModelGenerator:
    """
    Generates Power BI semantic model from Tableau workbook.
    """
    
    # Data type mapping from Tableau to Power BI
    DATATYPE_MAP = {
        DataType.STRING: PowerBIDataType.STRING,
        DataType.INTEGER: PowerBIDataType.INT64,
        DataType.REAL: PowerBIDataType.DOUBLE,
        DataType.BOOLEAN: PowerBIDataType.BOOLEAN,
        DataType.DATE: PowerBIDataType.DATETIME,
        DataType.DATETIME: PowerBIDataType.DATETIME,
        DataType.UNKNOWN: PowerBIDataType.STRING,
    }
    
    # Connection type mapping
    CONNECTION_TYPE_MAP = {
        "sqlserver": "SQL Server",
        "postgres": "PostgreSQL",
        "mysql": "MySQL",
        "oracle": "Oracle",
        "snowflake": "Snowflake",
        "bigquery": "BigQuery",
        "excel": "Excel",
        "textscan": "CSV",
        "hyper": "TableauExtract",
    }
    
    def __init__(self, use_genai: bool = True, openai_api_key: Optional[str] = None):
        """
        Initialize the semantic model generator.
        
        Args:
            use_genai: Whether to use GenAI for formula translation
            openai_api_key: OpenAI API key for GenAI translations
        """
        self.formula_translator = FormulaTranslator(
            use_genai=use_genai,
            openai_api_key=openai_api_key
        )
        self.translation_results: List[Tuple[TableauCalculatedField, TranslationResult]] = []
    
    def generate(self, workbook: TableauWorkbook) -> PowerBIReport:
        """
        Generate a Power BI report from a Tableau workbook.
        
        Args:
            workbook: Parsed Tableau workbook
            
        Returns:
            PowerBIReport with semantic model
        """
        report = PowerBIReport(
            name=workbook.name,
            source_tableau_workbook=workbook.source_file,
        )
        
        # Process each data source
        for ds in workbook.datasources:
            # Create table for this data source
            table = self._create_table_from_datasource(ds)
            report.tables.append(table)
            
            # Create data source connection
            if ds.connection:
                pbi_ds = self._create_datasource(ds)
                report.data_sources.append(pbi_ds)
        
        # Process parameters as What-If parameters
        for param in workbook.parameters:
            param_measure = self._create_parameter_measure(param)
            if param_measure:
                # Add to first table or create a Parameters table
                if report.tables:
                    report.tables[0].measures.append(param_measure)
                else:
                    params_table = PowerBITable(name="Parameters")
                    params_table.measures.append(param_measure)
                    report.tables.append(params_table)
        
        # Generate translation statistics
        report.translation_stats = self._generate_stats()
        
        return report
    
    def _create_table_from_datasource(self, ds: TableauDataSource) -> PowerBITable:
        """Create a Power BI table from a Tableau data source."""
        # Sanitize table name for Power BI compatibility
        table_name = self._sanitize_name(ds.display_name)
        
        table = PowerBITable(
            name=table_name,
        )
        
        # Add columns with proper formatting
        for col in ds.columns:
            pbi_col = PowerBIColumn(
                name=self._sanitize_name(col.display_name),
                source_column=col.name,
                data_type=self.DATATYPE_MAP.get(col.datatype, PowerBIDataType.STRING),
                is_hidden=col.hidden,
            )
            
            # Add format strings based on data type
            if col.datatype in [DataType.REAL, DataType.INTEGER]:
                if col.role == "measure":
                    pbi_col.format_string = "#,##0.00"
            elif col.datatype in [DataType.DATE, DataType.DATETIME]:
                pbi_col.format_string = "yyyy-MM-dd"
            
            # Set summarization for measures
            if col.role == "measure":
                pbi_col.summarize_by = "sum"
            
            table.columns.append(pbi_col)
        
        # Translate calculated fields to measures
        for calc_field in ds.calculated_fields:
            translation = self.formula_translator.translate(calc_field)
            self.translation_results.append((calc_field, translation))
            
            measure = self.formula_translator.to_measure(
                calc_field, translation, table_name
            )
            
            # Add display folder for organization
            if calc_field.is_lod:
                measure.display_folder = "LOD Calculations"
            elif calc_field.is_table_calc:
                measure.display_folder = "Table Calculations"
            else:
                measure.display_folder = "Calculated Measures"
            
            table.measures.append(measure)
        
        return table
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize a name for Power BI compatibility."""
        if not name:
            return "Unnamed"
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*[]'
        result = name
        for char in invalid_chars:
            result = result.replace(char, '_')
        # Clean up multiple underscores
        while '__' in result:
            result = result.replace('__', '_')
        return result.strip('_').strip()
    
    def _create_datasource(self, ds: TableauDataSource) -> PowerBIDataSource:
        """Create a Power BI data source from Tableau connection."""
        conn = ds.connection
        
        conn_type = self.CONNECTION_TYPE_MAP.get(
            conn.class_name.lower() if conn.class_name else "unknown",
            "Unknown"
        )
        
        pbi_ds = PowerBIDataSource(
            name=ds.display_name,
            connection_type=conn_type,
            server=conn.server,
            database=conn.database,
        )
        
        # Build connection string if possible
        if conn.server and conn.database:
            if conn_type == "SQL Server":
                pbi_ds.connection_string = f"Server={conn.server};Database={conn.database}"
            elif conn_type == "PostgreSQL":
                pbi_ds.connection_string = f"Host={conn.server};Database={conn.database}"
        
        return pbi_ds
    
    def _create_parameter_measure(self, param: TableauParameter) -> Optional[PowerBIMeasure]:
        """
        Create a Power BI measure for a Tableau parameter.
        
        Note: Power BI handles parameters differently - typically through
        What-If parameters or disconnected tables. This creates a simple
        measure that can be modified to use What-If.
        """
        # Determine DAX expression based on parameter type
        if param.datatype == DataType.INTEGER:
            default_value = int(param.current_value) if param.current_value else 0
            expression = f"SELECTEDVALUE('{param.display_name}'[Value], {default_value})"
        elif param.datatype == DataType.REAL:
            default_value = float(param.current_value) if param.current_value else 0.0
            expression = f"SELECTEDVALUE('{param.display_name}'[Value], {default_value})"
        elif param.datatype == DataType.STRING:
            default_value = f'"{param.current_value}"' if param.current_value else '""'
            expression = f"SELECTEDVALUE('{param.display_name}'[Value], {default_value})"
        else:
            expression = f"/* Parameter: {param.display_name} - configure as What-If parameter */"
        
        notes = [
            "Converted from Tableau parameter",
            f"Original type: {param.datatype.value}",
            f"Allowable values: {param.allowable_values_type}",
        ]
        
        if param.allowable_values_type == "range":
            notes.append(f"Range: {param.min_value} to {param.max_value}, step {param.step_size}")
            notes.append("Create as What-If parameter with these range settings")
        elif param.allowable_values_type == "list":
            notes.append(f"List values: {param.allowable_values}")
            notes.append("Create disconnected table with these values")
        
        return PowerBIMeasure(
            name=param.display_name,
            expression=expression,
            description="Tableau parameter - configure as What-If parameter",
            translation_notes=notes,
            requires_review=True,
            translation_confidence=0.5,  # Parameters need manual setup
        )
    
    def _generate_stats(self) -> Dict[str, Any]:
        """Generate translation statistics."""
        from translators.formula_translator import TranslationConfidence
        
        stats = {
            "total_calculated_fields": len(self.translation_results),
            "high_confidence": 0,
            "medium_confidence": 0,
            "low_confidence": 0,
            "failed": 0,
            "requires_review": 0,
            "by_type": {},
        }
        
        for calc_field, result in self.translation_results:
            if result.confidence == TranslationConfidence.HIGH:
                stats["high_confidence"] += 1
            elif result.confidence == TranslationConfidence.MEDIUM:
                stats["medium_confidence"] += 1
            elif result.confidence == TranslationConfidence.LOW:
                stats["low_confidence"] += 1
            else:
                stats["failed"] += 1
            
            if result.requires_review:
                stats["requires_review"] += 1
            
            # Track by calculation type
            calc_type = calc_field.calculation_type.value
            if calc_type not in stats["by_type"]:
                stats["by_type"][calc_type] = {"total": 0, "successful": 0}
            stats["by_type"][calc_type]["total"] += 1
            if result.confidence != TranslationConfidence.FAILED:
                stats["by_type"][calc_type]["successful"] += 1
        
        # Calculate success rate
        total = stats["total_calculated_fields"]
        if total > 0:
            successful = stats["high_confidence"] + stats["medium_confidence"] + stats["low_confidence"]
            stats["success_rate"] = round(successful / total * 100, 1)
        else:
            stats["success_rate"] = 100.0
        
        return stats
    
    def get_translation_report(self) -> List[Dict[str, Any]]:
        """
        Get detailed translation report for all calculated fields.
        
        Returns:
            List of translation details for each field
        """
        report = []
        
        for calc_field, result in self.translation_results:
            report.append({
                "tableau_field": calc_field.display_name,
                "tableau_formula": calc_field.formula,
                "calculation_type": calc_field.calculation_type.value,
                "dax_expression": result.dax_expression,
                "confidence": result.confidence.value,
                "requires_review": result.requires_review,
                "notes": result.notes,
                "referenced_fields": calc_field.referenced_fields,
            })
        
        return report
    
    def generate_measures_table(self) -> PowerBITable:
        """
        Generate a dedicated Measures table.
        
        This is a common Power BI pattern - having a separate table
        for measures rather than attaching them to data tables.
        """
        measures_table = PowerBITable(
            name="_Measures",
            is_hidden=True,
            source_type="calculated",
        )
        
        # Add a dummy column (required for table to exist)
        measures_table.columns.append(PowerBIColumn(
            name="_MeasuresColumn",
            data_type=PowerBIDataType.INT64,
            is_hidden=True,
        ))
        
        return measures_table
    
    def infer_relationships(self, workbook: TableauWorkbook) -> List[PowerBIRelationship]:
        """
        Attempt to infer relationships from Tableau joins.
        
        Args:
            workbook: Parsed Tableau workbook
            
        Returns:
            List of inferred relationships
        """
        relationships = []
        
        for ds in workbook.datasources:
            for join in ds.joins:
                if "left_table" in join and "right_table" in join:
                    # Try to infer join columns from join conditions
                    rel = PowerBIRelationship(
                        from_table=join.get("left_table", ""),
                        from_column=join.get("left_column", "ID"),  # Default guess
                        to_table=join.get("right_table", ""),
                        to_column=join.get("right_column", "ID"),  # Default guess
                        cardinality=self._map_join_type(join.get("type", "inner")),
                    )
                    relationships.append(rel)
        
        return relationships
    
    def _map_join_type(self, tableau_join: str) -> str:
        """Map Tableau join type to Power BI cardinality."""
        join_map = {
            "inner": "manyToOne",
            "left": "manyToOne",
            "right": "oneToMany",
            "full": "manyToMany",
        }
        return join_map.get(tableau_join.lower(), "manyToOne")


class ConnectionStringBuilder:
    """Helper class to build Power BI connection strings."""
    
    @staticmethod
    def build_sql_server(server: str, database: str, 
                        integrated_security: bool = True) -> str:
        """Build SQL Server connection string."""
        if integrated_security:
            return f"Data Source={server};Initial Catalog={database};Integrated Security=True"
        return f"Data Source={server};Initial Catalog={database}"
    
    @staticmethod
    def build_postgresql(server: str, database: str, port: int = 5432) -> str:
        """Build PostgreSQL connection string."""
        return f"Host={server};Port={port};Database={database}"
    
    @staticmethod
    def build_mysql(server: str, database: str, port: int = 3306) -> str:
        """Build MySQL connection string."""
        return f"Server={server};Port={port};Database={database}"
    
    @staticmethod
    def build_snowflake(account: str, warehouse: str, database: str) -> str:
        """Build Snowflake connection string."""
        return f"Account={account};Warehouse={warehouse};Database={database}"
    
    @staticmethod
    def build_from_tableau_connection(conn) -> Optional[str]:
        """
        Build a Power BI connection string from Tableau connection info.
        
        Args:
            conn: TableauConnection object
            
        Returns:
            Connection string or None if not supported
        """
        if not conn:
            return None
        
        class_name = (conn.class_name or "").lower()
        
        if class_name == "sqlserver":
            if conn.server and conn.database:
                return ConnectionStringBuilder.build_sql_server(
                    conn.server, conn.database
                )
        
        elif class_name == "postgres":
            if conn.server and conn.database:
                return ConnectionStringBuilder.build_postgresql(
                    conn.server, conn.database,
                    conn.port or 5432
                )
        
        elif class_name == "mysql":
            if conn.server and conn.database:
                return ConnectionStringBuilder.build_mysql(
                    conn.server, conn.database,
                    conn.port or 3306
                )
        
        elif class_name == "excel":
            if conn.filename:
                return conn.filename
        
        return None
