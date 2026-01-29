"""
Semantic Model Generator for Power BI.

Generates the Power BI semantic model (data model) including:
- Tables and columns
- DAX measures (translated from Tableau calculated fields)
- Relationships between tables
- Data source connections
"""

import uuid
import re
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

from models.tableau_models import (
    TableauWorkbook, TableauDataSource, TableauCalculatedField,
    TableauParameter, TableauColumn, DataType
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
        "federated": "Federated",
    }
    
    # Common semantic roles for auto-detection
    SEMANTIC_ROLES = {
        "country": "Geography.Country",
        "state": "Geography.StateOrProvince", 
        "city": "Geography.City",
        "postal": "Geography.PostalCode",
        "zip": "Geography.PostalCode",
        "latitude": "Geography.Latitude",
        "longitude": "Geography.Longitude",
        "address": "Geography.Address",
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
        self._table_name_counter: Dict[str, int] = {}
    
    def generate(self, workbook: TableauWorkbook) -> PowerBIReport:
        """
        Generate a Power BI report from a Tableau workbook.
        
        Args:
            workbook: Parsed Tableau workbook
            
        Returns:
            PowerBIReport with semantic model
        """
        # Reset state for new generation
        self.translation_results = []
        self._table_name_counter = {}
        
        report = PowerBIReport(
            name=workbook.name,
            source_tableau_workbook=workbook.source_file,
        )
        
        # Track table names to handle duplicates
        table_name_map: Dict[str, str] = {}
        
        # Process each data source
        for ds in workbook.datasources:
            # Create table for this data source
            table = self._create_table_from_datasource(ds, workbook)
            
            # Handle duplicate table names
            original_name = table.name
            table.name = self._get_unique_table_name(table.name)
            table_name_map[ds.name] = table.name
            
            report.tables.append(table)
            
            # Create data source connection
            if ds.connection:
                pbi_ds = self._create_datasource(ds)
                report.data_sources.append(pbi_ds)
        
        # Infer and add relationships
        relationships = self.infer_relationships(workbook, table_name_map)
        report.relationships = relationships
        
        # Create a dedicated measures table if there are many calculated fields
        all_calc_fields = workbook.get_all_calculated_fields()
        if len(all_calc_fields) > 10:
            measures_table = self.generate_measures_table()
            report.tables.append(measures_table)
        
        # Process parameters as What-If parameters
        params_table = None
        for param in workbook.parameters:
            param_measure = self._create_parameter_measure(param)
            if param_measure:
                if params_table is None:
                    params_table = PowerBITable(name="Parameters")
                    # Add a placeholder column for the parameters table
                    params_table.columns.append(PowerBIColumn(
                        name="ParameterValue",
                        data_type=PowerBIDataType.DOUBLE,
                        is_hidden=True,
                    ))
                params_table.measures.append(param_measure)
        
        if params_table:
            report.tables.append(params_table)
        
        # Generate translation statistics
        report.translation_stats = self._generate_stats()
        
        return report
    
    def _get_unique_table_name(self, name: str) -> str:
        """Get a unique table name, handling duplicates."""
        if name not in self._table_name_counter:
            self._table_name_counter[name] = 0
            return name
        
        self._table_name_counter[name] += 1
        return f"{name}_{self._table_name_counter[name]}"
    
    def _create_table_from_datasource(self, ds: TableauDataSource, 
                                        workbook: TableauWorkbook = None) -> PowerBITable:
        """Create a Power BI table from a Tableau data source."""
        # Sanitize table name for Power BI compatibility
        table_name = self._sanitize_name(ds.display_name)
        
        table = PowerBITable(
            name=table_name,
        )
        
        # Track column names to avoid duplicates
        column_names_seen: Dict[str, int] = {}
        
        # Add columns with proper formatting
        for col in ds.columns:
            pbi_col = self._create_column_from_tableau(col, column_names_seen)
            if pbi_col:
                table.columns.append(pbi_col)
        
        # If no columns were found, try to infer from worksheets
        if not table.columns and workbook:
            inferred_columns = self._infer_columns_from_worksheets(ds.name, workbook)
            for col in inferred_columns:
                if col.name not in column_names_seen:
                    table.columns.append(col)
                    column_names_seen[col.name] = 1
        
        # Ensure table has at least one column (required for Power BI)
        if not table.columns:
            table.columns.append(PowerBIColumn(
                name="ID",
                data_type=PowerBIDataType.INT64,
                is_hidden=True,
            ))
        
        # Translate calculated fields to measures
        for calc_field in ds.calculated_fields:
            translation = self.formula_translator.translate(calc_field, table_name)
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
            
            # Set format string based on data type
            if calc_field.datatype in [DataType.REAL, DataType.INTEGER]:
                measure.format_string = "#,##0.00"
            elif calc_field.datatype == DataType.DATE:
                measure.format_string = "yyyy-MM-dd"
            
            table.measures.append(measure)
        
        return table
    
    def _create_column_from_tableau(self, col: TableauColumn, 
                                     seen_names: Dict[str, int]) -> Optional[PowerBIColumn]:
        """Create a Power BI column from a Tableau column with proper handling."""
        col_name = self._sanitize_name(col.display_name)
        
        # Handle duplicate column names
        if col_name in seen_names:
            seen_names[col_name] += 1
            col_name = f"{col_name}_{seen_names[col_name]}"
        else:
            seen_names[col_name] = 1
        
        # Skip if name is empty after sanitization
        if not col_name:
            return None
        
        pbi_col = PowerBIColumn(
            name=col_name,
            source_column=col.name,
            data_type=self.DATATYPE_MAP.get(col.datatype, PowerBIDataType.STRING),
            is_hidden=col.hidden,
        )
        
        # Add format strings based on data type
        if col.datatype == DataType.REAL:
            if col.role == "measure":
                pbi_col.format_string = "#,##0.00"
            else:
                pbi_col.format_string = "0.00"
        elif col.datatype == DataType.INTEGER:
            if col.role == "measure":
                pbi_col.format_string = "#,##0"
        elif col.datatype == DataType.DATE:
            pbi_col.format_string = "yyyy-MM-dd"
        elif col.datatype == DataType.DATETIME:
            pbi_col.format_string = "yyyy-MM-dd HH:mm:ss"
        
        # Set summarization for measures
        if col.role == "measure":
            agg_map = {
                "sum": "sum",
                "avg": "average",
                "count": "count",
                "countd": "distinctCount",
                "min": "min",
                "max": "max",
            }
            pbi_col.summarize_by = agg_map.get(
                col.aggregation.value if col.aggregation else "none", 
                "sum"
            )
        else:
            pbi_col.summarize_by = "none"
        
        # Detect semantic roles from column name
        lower_name = col_name.lower()
        for keyword, role in self.SEMANTIC_ROLES.items():
            if keyword in lower_name:
                # Store semantic role in sort_by_column as a workaround
                # (Power BI models don't have a direct semantic role property in basic model)
                break
        
        return pbi_col
    
    def _infer_columns_from_worksheets(self, ds_name: str, 
                                        workbook: TableauWorkbook) -> List[PowerBIColumn]:
        """Infer columns from worksheet field usage when datasource has no column metadata."""
        columns = []
        field_names: set = set()
        
        for ws in workbook.worksheets:
            if ws.datasource_name == ds_name or not ws.datasource_name:
                # Collect all fields from this worksheet
                for mapping in ws.rows + ws.columns + ws.label_fields + ws.detail_fields:
                    field_names.add(mapping.field)
                if ws.color_field:
                    field_names.add(ws.color_field.field)
                if ws.size_field:
                    field_names.add(ws.size_field.field)
        
        # Create columns for each unique field
        for field in field_names:
            # Try to determine data type from aggregation
            data_type = PowerBIDataType.STRING  # Default
            
            columns.append(PowerBIColumn(
                name=self._sanitize_name(field),
                source_column=field,
                data_type=data_type,
            ))
        
        return columns
    
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
    
    def infer_relationships(self, workbook: TableauWorkbook, 
                             table_name_map: Dict[str, str] = None) -> List[PowerBIRelationship]:
        """
        Attempt to infer relationships from Tableau joins.
        
        Args:
            workbook: Parsed Tableau workbook
            table_name_map: Mapping from Tableau DS names to Power BI table names
            
        Returns:
            List of inferred relationships
        """
        relationships = []
        table_name_map = table_name_map or {}
        
        for ds in workbook.datasources:
            for join in ds.joins:
                if "left_table" in join and "right_table" in join:
                    left_table = join.get("left_table", "")
                    right_table = join.get("right_table", "")
                    
                    # Map to Power BI table names if available
                    left_table = table_name_map.get(left_table, self._sanitize_name(left_table))
                    right_table = table_name_map.get(right_table, self._sanitize_name(right_table))
                    
                    # Get column names
                    left_column = join.get("left_column", "")
                    right_column = join.get("right_column", "")
                    
                    # Try to infer column names if not specified
                    if not left_column or not right_column:
                        left_column, right_column = self._guess_join_columns(
                            left_table, right_table, workbook
                        )
                    
                    if left_table and right_table and left_column and right_column:
                        rel = PowerBIRelationship(
                            name=f"Rel_{left_table}_{right_table}",
                            from_table=left_table,
                            from_column=self._sanitize_name(left_column),
                            to_table=right_table,
                            to_column=self._sanitize_name(right_column),
                            cardinality=self._map_join_type(join.get("type", "inner")),
                            is_active=True,
                        )
                        relationships.append(rel)
        
        # Also try to infer relationships from common field names
        if len(workbook.datasources) > 1:
            inferred = self._infer_relationships_from_common_fields(workbook, table_name_map)
            for rel in inferred:
                # Avoid duplicates
                exists = any(
                    r.from_table == rel.from_table and r.to_table == rel.to_table
                    for r in relationships
                )
                if not exists:
                    relationships.append(rel)
        
        return relationships
    
    def _guess_join_columns(self, left_table: str, right_table: str, 
                            workbook: TableauWorkbook) -> Tuple[str, str]:
        """Guess join columns based on common naming patterns."""
        # Common ID column patterns
        common_patterns = [
            ("ID", "ID"),
            (f"{right_table}ID", "ID"),
            (f"{right_table}_ID", "ID"),
            ("Key", "Key"),
        ]
        
        # Try to find matching columns
        for ds in workbook.datasources:
            col_names = [c.name for c in ds.columns]
            
            # Look for ID patterns
            for left_pattern, right_pattern in common_patterns:
                if left_pattern in col_names:
                    return left_pattern, right_pattern
        
        return "ID", "ID"  # Default fallback
    
    def _infer_relationships_from_common_fields(self, workbook: TableauWorkbook,
                                                  table_name_map: Dict[str, str]) -> List[PowerBIRelationship]:
        """Infer relationships from common field names across datasources."""
        relationships = []
        
        # Build a map of field names to datasources
        field_to_ds: Dict[str, List[str]] = {}
        
        for ds in workbook.datasources:
            pbi_table = table_name_map.get(ds.name, self._sanitize_name(ds.display_name))
            for col in ds.columns:
                field_name = col.name.lower()
                # Look for ID-like fields
                if 'id' in field_name or 'key' in field_name:
                    if field_name not in field_to_ds:
                        field_to_ds[field_name] = []
                    field_to_ds[field_name].append((pbi_table, col.name))
        
        # Create relationships for fields that appear in multiple tables
        for field_name, tables in field_to_ds.items():
            if len(tables) > 1:
                # Create relationship between first two tables with this field
                from_table, from_col = tables[0]
                to_table, to_col = tables[1]
                
                rel = PowerBIRelationship(
                    name=f"Inferred_{from_table}_{to_table}",
                    from_table=from_table,
                    from_column=self._sanitize_name(from_col),
                    to_table=to_table,
                    to_column=self._sanitize_name(to_col),
                    cardinality="manyToOne",
                    is_active=True,
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
