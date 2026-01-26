"""
Connection String Templates for Power BI Data Sources.

This module provides templates and builders for generating
Power BI data source connection configurations from Tableau
connection information.
"""

from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from enum import Enum


class ConnectionType(Enum):
    """Supported connection types."""
    SQL_SERVER = "SQL Server"
    POSTGRESQL = "PostgreSQL"
    MYSQL = "MySQL"
    ORACLE = "Oracle"
    SNOWFLAKE = "Snowflake"
    BIGQUERY = "BigQuery"
    AZURE_SQL = "Azure SQL Database"
    AZURE_SYNAPSE = "Azure Synapse Analytics"
    REDSHIFT = "Amazon Redshift"
    DATABRICKS = "Databricks"
    EXCEL = "Excel"
    CSV = "CSV/Text"
    SHAREPOINT = "SharePoint"
    WEB = "Web"
    ODATA = "OData"
    REST_API = "REST API"
    TABLEAU_EXTRACT = "Tableau Extract"
    UNKNOWN = "Unknown"


@dataclass
class ConnectionTemplate:
    """Template for a connection type."""
    connection_type: ConnectionType
    m_query_template: str
    connection_string_template: str
    required_params: List[str]
    optional_params: List[str] = field(default_factory=list)
    notes: str = ""
    power_query_source_function: str = ""
    
    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        """Validate that required parameters are present."""
        missing = []
        for param in self.required_params:
            if param not in params or not params[param]:
                missing.append(param)
        return missing
    
    def build_m_query(self, params: Dict[str, Any]) -> str:
        """Build M query from template and parameters."""
        query = self.m_query_template
        for key, value in params.items():
            query = query.replace(f"{{{key}}}", str(value))
        return query
    
    def build_connection_string(self, params: Dict[str, Any]) -> str:
        """Build connection string from template and parameters."""
        conn_str = self.connection_string_template
        for key, value in params.items():
            conn_str = conn_str.replace(f"{{{key}}}", str(value))
        return conn_str


# =============================================================================
# CONNECTION TEMPLATES
# =============================================================================

CONNECTION_TEMPLATES: Dict[ConnectionType, ConnectionTemplate] = {
    ConnectionType.SQL_SERVER: ConnectionTemplate(
        connection_type=ConnectionType.SQL_SERVER,
        m_query_template="""let
    Source = Sql.Database("{server}", "{database}"),
    {table} = Source{{[Schema="{schema}",Item="{table}"]}}[Data]
in
    {table}""",
        connection_string_template="Data Source={server};Initial Catalog={database};Integrated Security=True",
        required_params=["server", "database"],
        optional_params=["schema", "table", "query", "username", "password"],
        power_query_source_function="Sql.Database",
        notes="Supports Windows Authentication and SQL Authentication"
    ),
    
    ConnectionType.AZURE_SQL: ConnectionTemplate(
        connection_type=ConnectionType.AZURE_SQL,
        m_query_template="""let
    Source = AzureSQL.Database("{server}.database.windows.net", "{database}"),
    {table} = Source{{[Schema="{schema}",Item="{table}"]}}[Data]
in
    {table}""",
        connection_string_template="Server={server}.database.windows.net;Database={database};Authentication=Active Directory Integrated",
        required_params=["server", "database"],
        optional_params=["schema", "table", "query"],
        power_query_source_function="AzureSQL.Database",
        notes="Requires Azure Active Directory authentication"
    ),
    
    ConnectionType.POSTGRESQL: ConnectionTemplate(
        connection_type=ConnectionType.POSTGRESQL,
        m_query_template="""let
    Source = PostgreSQL.Database("{server}", "{database}"),
    {table} = Source{{[Schema="{schema}",Item="{table}"]}}[Data]
in
    {table}""",
        connection_string_template="Host={server};Port={port};Database={database}",
        required_params=["server", "database"],
        optional_params=["port", "schema", "table", "username", "password"],
        power_query_source_function="PostgreSQL.Database",
        notes="Default port is 5432"
    ),
    
    ConnectionType.MYSQL: ConnectionTemplate(
        connection_type=ConnectionType.MYSQL,
        m_query_template="""let
    Source = MySQL.Database("{server}", "{database}"),
    {table} = Source{{[Schema="{database}",Item="{table}"]}}[Data]
in
    {table}""",
        connection_string_template="Server={server};Port={port};Database={database}",
        required_params=["server", "database"],
        optional_params=["port", "table", "username", "password"],
        power_query_source_function="MySQL.Database",
        notes="Default port is 3306"
    ),
    
    ConnectionType.ORACLE: ConnectionTemplate(
        connection_type=ConnectionType.ORACLE,
        m_query_template="""let
    Source = Oracle.Database("{server}", [HierarchicalNavigation=true]),
    {schema} = Source{{[Schema="{schema}"]}}[Data],
    {table} = {schema}{{[Name="{table}"]}}[Data]
in
    {table}""",
        connection_string_template="Data Source={server};User Id={username};Password={password}",
        required_params=["server"],
        optional_params=["schema", "table", "username", "password", "service_name"],
        power_query_source_function="Oracle.Database",
        notes="Requires Oracle client installation"
    ),
    
    ConnectionType.SNOWFLAKE: ConnectionTemplate(
        connection_type=ConnectionType.SNOWFLAKE,
        m_query_template="""let
    Source = Snowflake.Databases("{account}.snowflakecomputing.com", "{warehouse}"),
    {database} = Source{{[Name="{database}"]}}[Data],
    {schema} = {database}{{[Name="{schema}"]}}[Data],
    {table} = {schema}{{[Name="{table}"]}}[Data]
in
    {table}""",
        connection_string_template="Account={account};Warehouse={warehouse};Database={database};Schema={schema}",
        required_params=["account", "warehouse", "database"],
        optional_params=["schema", "table", "role"],
        power_query_source_function="Snowflake.Databases",
        notes="Requires Snowflake account identifier (e.g., xy12345.us-east-1)"
    ),
    
    ConnectionType.BIGQUERY: ConnectionTemplate(
        connection_type=ConnectionType.BIGQUERY,
        m_query_template="""let
    Source = GoogleBigQuery.Database([BillingProject="{project}"]),
    {dataset} = Source{{[Name="{dataset}"]}}[Data],
    {table} = {dataset}{{[Name="{table}"]}}[Data]
in
    {table}""",
        connection_string_template="Project={project};Dataset={dataset}",
        required_params=["project"],
        optional_params=["dataset", "table"],
        power_query_source_function="GoogleBigQuery.Database",
        notes="Requires Google Cloud authentication"
    ),
    
    ConnectionType.REDSHIFT: ConnectionTemplate(
        connection_type=ConnectionType.REDSHIFT,
        m_query_template="""let
    Source = AmazonRedshift.Database("{server}", "{database}"),
    {schema} = Source{{[Schema="{schema}"]}}[Data],
    {table} = {schema}{{[Name="{table}"]}}[Data]
in
    {table}""",
        connection_string_template="Server={server};Database={database};Port={port}",
        required_params=["server", "database"],
        optional_params=["port", "schema", "table", "username", "password"],
        power_query_source_function="AmazonRedshift.Database",
        notes="Default port is 5439"
    ),
    
    ConnectionType.DATABRICKS: ConnectionTemplate(
        connection_type=ConnectionType.DATABRICKS,
        m_query_template="""let
    Source = Databricks.Catalogs("{server}", "{http_path}"),
    {catalog} = Source{{[Name="{catalog}"]}}[Data],
    {schema} = {catalog}{{[Name="{schema}"]}}[Data],
    {table} = {schema}{{[Name="{table}"]}}[Data]
in
    {table}""",
        connection_string_template="Server={server};HTTPPath={http_path}",
        required_params=["server", "http_path"],
        optional_params=["catalog", "schema", "table"],
        power_query_source_function="Databricks.Catalogs",
        notes="Requires Databricks workspace URL and SQL warehouse HTTP path"
    ),
    
    ConnectionType.EXCEL: ConnectionTemplate(
        connection_type=ConnectionType.EXCEL,
        m_query_template="""let
    Source = Excel.Workbook(File.Contents("{file_path}"), null, true),
    {sheet} = Source{{[Item="{sheet}",Kind="Sheet"]}}[Data],
    PromotedHeaders = Table.PromoteHeaders({sheet}, [PromoteAllScalars=true])
in
    PromotedHeaders""",
        connection_string_template="{file_path}",
        required_params=["file_path"],
        optional_params=["sheet", "range"],
        power_query_source_function="Excel.Workbook",
        notes="Can also use Excel.CurrentWorkbook for embedded data"
    ),
    
    ConnectionType.CSV: ConnectionTemplate(
        connection_type=ConnectionType.CSV,
        m_query_template="""let
    Source = Csv.Document(File.Contents("{file_path}"), [Delimiter="{delimiter}", Encoding=65001]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
in
    PromotedHeaders""",
        connection_string_template="{file_path}",
        required_params=["file_path"],
        optional_params=["delimiter", "encoding", "skip_rows"],
        power_query_source_function="Csv.Document",
        notes="Default delimiter is comma. Encoding 65001 is UTF-8."
    ),
    
    ConnectionType.SHAREPOINT: ConnectionTemplate(
        connection_type=ConnectionType.SHAREPOINT,
        m_query_template="""let
    Source = SharePoint.Files("{site_url}", [ApiVersion = 15]),
    FilteredRows = Table.SelectRows(Source, each [Name] = "{file_name}"),
    Content = FilteredRows{{0}}[Content],
    ImportedData = Excel.Workbook(Content)
in
    ImportedData""",
        connection_string_template="{site_url}",
        required_params=["site_url"],
        optional_params=["file_name", "folder_path"],
        power_query_source_function="SharePoint.Files",
        notes="Requires SharePoint Online or SharePoint Server"
    ),
    
    ConnectionType.WEB: ConnectionTemplate(
        connection_type=ConnectionType.WEB,
        m_query_template="""let
    Source = Web.Contents("{url}"),
    ImportedData = Json.Document(Source)
in
    ImportedData""",
        connection_string_template="{url}",
        required_params=["url"],
        optional_params=["headers", "query_params"],
        power_query_source_function="Web.Contents",
        notes="Use for REST APIs and web data. May require authentication."
    ),
    
    ConnectionType.ODATA: ConnectionTemplate(
        connection_type=ConnectionType.ODATA,
        m_query_template="""let
    Source = OData.Feed("{url}"),
    {entity} = Source{{[Name="{entity}"]}}[Data]
in
    {entity}""",
        connection_string_template="{url}",
        required_params=["url"],
        optional_params=["entity"],
        power_query_source_function="OData.Feed",
        notes="Supports OData v2, v3, and v4"
    ),
    
    ConnectionType.AZURE_SYNAPSE: ConnectionTemplate(
        connection_type=ConnectionType.AZURE_SYNAPSE,
        m_query_template="""let
    Source = AzureSynapseAnalytics.Database("{server}", "{database}"),
    {table} = Source{{[Schema="{schema}",Item="{table}"]}}[Data]
in
    {table}""",
        connection_string_template="Server={server};Database={database}",
        required_params=["server", "database"],
        optional_params=["schema", "table"],
        power_query_source_function="AzureSynapseAnalytics.Database",
        notes="For Azure Synapse dedicated SQL pools"
    ),
    
    ConnectionType.TABLEAU_EXTRACT: ConnectionTemplate(
        connection_type=ConnectionType.TABLEAU_EXTRACT,
        m_query_template="""/* 
Tableau Extract (.hyper) cannot be directly imported into Power BI.

Options:
1. Export from Tableau to CSV/Excel and import
2. Connect to the original data source
3. Use Tableau's export functionality
*/
let
    Source = #table(type table [Column1 = text], {})
in
    Source""",
        connection_string_template="",
        required_params=[],
        optional_params=[],
        power_query_source_function="",
        notes="Tableau extracts need to be converted or source data accessed directly"
    ),
}


class ConnectionBuilder:
    """Builder for creating Power BI data source connections."""
    
    def __init__(self):
        """Initialize with default templates."""
        self.templates = CONNECTION_TEMPLATES.copy()
    
    def get_template(self, connection_type: ConnectionType) -> Optional[ConnectionTemplate]:
        """Get template for a connection type."""
        return self.templates.get(connection_type)
    
    def infer_connection_type(self, tableau_class: str) -> ConnectionType:
        """
        Infer Power BI connection type from Tableau connection class.
        
        Args:
            tableau_class: Tableau connection class name
            
        Returns:
            Corresponding Power BI connection type
        """
        class_mapping = {
            "sqlserver": ConnectionType.SQL_SERVER,
            "postgres": ConnectionType.POSTGRESQL,
            "postgresql": ConnectionType.POSTGRESQL,
            "mysql": ConnectionType.MYSQL,
            "oracle": ConnectionType.ORACLE,
            "snowflake": ConnectionType.SNOWFLAKE,
            "bigquery": ConnectionType.BIGQUERY,
            "google-bigquery": ConnectionType.BIGQUERY,
            "redshift": ConnectionType.REDSHIFT,
            "amazon-redshift": ConnectionType.REDSHIFT,
            "databricks": ConnectionType.DATABRICKS,
            "excel": ConnectionType.EXCEL,
            "excel-direct": ConnectionType.EXCEL,
            "textscan": ConnectionType.CSV,
            "csv": ConnectionType.CSV,
            "hyper": ConnectionType.TABLEAU_EXTRACT,
            "dataengine": ConnectionType.TABLEAU_EXTRACT,
            "azure-sql-database": ConnectionType.AZURE_SQL,
            "azure-synapse": ConnectionType.AZURE_SYNAPSE,
            "sharepoint-list": ConnectionType.SHAREPOINT,
            "odata": ConnectionType.ODATA,
            "webdata": ConnectionType.WEB,
        }
        return class_mapping.get(tableau_class.lower(), ConnectionType.UNKNOWN)
    
    def build_from_tableau_connection(self, tableau_connection) -> Dict[str, Any]:
        """
        Build Power BI connection configuration from Tableau connection.
        
        Args:
            tableau_connection: TableauConnection object
            
        Returns:
            Dictionary with M query, connection string, and notes
        """
        conn_type = self.infer_connection_type(
            tableau_connection.class_name or "unknown"
        )
        
        template = self.get_template(conn_type)
        if not template:
            return {
                "success": False,
                "error": f"No template for connection type: {conn_type.value}",
                "connection_type": conn_type.value,
            }
        
        # Build parameters from Tableau connection
        params = {
            "server": tableau_connection.server or "",
            "database": tableau_connection.database or "",
            "schema": tableau_connection.schema_name or "dbo",
            "port": tableau_connection.port or "",
            "username": tableau_connection.username or "",
            "file_path": tableau_connection.filename or "",
        }
        
        # Add table if available
        if hasattr(tableau_connection, "table"):
            params["table"] = tableau_connection.table
        else:
            params["table"] = "YourTable"
        
        # Validate required parameters
        missing = template.validate_params(params)
        
        result = {
            "success": len(missing) == 0,
            "connection_type": conn_type.value,
            "m_query": template.build_m_query(params),
            "connection_string": template.build_connection_string(params),
            "notes": template.notes,
            "power_query_function": template.power_query_source_function,
        }
        
        if missing:
            result["missing_params"] = missing
            result["warning"] = f"Missing required parameters: {', '.join(missing)}"
        
        return result
    
    def get_all_connection_types(self) -> List[Dict[str, str]]:
        """Get list of all supported connection types."""
        return [
            {
                "type": ct.value,
                "function": template.power_query_source_function,
                "notes": template.notes,
            }
            for ct, template in self.templates.items()
        ]
    
    def add_custom_template(self, connection_type: ConnectionType, 
                           template: ConnectionTemplate) -> None:
        """Add a custom connection template."""
        self.templates[connection_type] = template
    
    def generate_native_query(self, connection_type: ConnectionType,
                             sql_query: str) -> str:
        """
        Generate M code for a native SQL query.
        
        Args:
            connection_type: Database connection type
            sql_query: SQL query to execute
            
        Returns:
            M query code
        """
        # Escape quotes in SQL
        escaped_sql = sql_query.replace('"', '""')
        
        native_query_templates = {
            ConnectionType.SQL_SERVER: f'''let
    Source = Sql.Database("{{server}}", "{{database}}"),
    Query = Value.NativeQuery(Source, "{escaped_sql}")
in
    Query''',
            ConnectionType.POSTGRESQL: f'''let
    Source = PostgreSQL.Database("{{server}}", "{{database}}"),
    Query = Value.NativeQuery(Source, "{escaped_sql}")
in
    Query''',
            ConnectionType.MYSQL: f'''let
    Source = MySQL.Database("{{server}}", "{{database}}"),
    Query = Value.NativeQuery(Source, "{escaped_sql}")
in
    Query''',
        }
        
        return native_query_templates.get(
            connection_type,
            f'/* Native query not supported for {connection_type.value} */\n{sql_query}'
        )


# Global builder instance
connection_builder = ConnectionBuilder()


def convert_tableau_to_powerbi_connection(tableau_connection) -> Dict[str, Any]:
    """
    Convenience function to convert a Tableau connection to Power BI.
    
    Args:
        tableau_connection: TableauConnection object
        
    Returns:
        Power BI connection configuration
    """
    return connection_builder.build_from_tableau_connection(tableau_connection)
