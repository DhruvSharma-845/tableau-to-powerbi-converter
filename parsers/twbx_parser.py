"""
Parser for Tableau workbook files (.twbx and .twb).

TWBX files are ZIP archives containing:
- A .twb file (XML workbook definition)
- A Data/ folder with extract files (.hyper)
- Optional image and resource files

This parser extracts all components into our data model.
"""

import zipfile
import tempfile
import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from lxml import etree

from models.tableau_models import (
    TableauWorkbook,
    TableauDataSource,
    TableauConnection,
    TableauCalculatedField,
    TableauParameter,
    TableauWorksheet,
    TableauDashboard,
    TableauFilter,
    TableauColumn,
    TableauMark,
    FieldMapping,
    DashboardObject,
    DataType,
    AggregationType,
    MarkType,
    CalculationType,
)


class TWBXParser:
    """Parser for Tableau workbook files."""
    
    # Mapping from Tableau datatypes to our enum
    DATATYPE_MAP = {
        "string": DataType.STRING,
        "integer": DataType.INTEGER,
        "real": DataType.REAL,
        "boolean": DataType.BOOLEAN,
        "date": DataType.DATE,
        "datetime": DataType.DATETIME,
    }
    
    # Mapping from Tableau aggregations to our enum
    AGGREGATION_MAP = {
        "sum": AggregationType.SUM,
        "avg": AggregationType.AVG,
        "count": AggregationType.COUNT,
        "countd": AggregationType.COUNTD,
        "min": AggregationType.MIN,
        "max": AggregationType.MAX,
        "median": AggregationType.MEDIAN,
        "attr": AggregationType.ATTR,
    }
    
    # Mapping from Tableau mark types to our enum
    MARK_TYPE_MAP = {
        "bar": MarkType.BAR,
        "line": MarkType.LINE,
        "area": MarkType.AREA,
        "square": MarkType.SQUARE,
        "circle": MarkType.CIRCLE,
        "shape": MarkType.SHAPE,
        "text": MarkType.TEXT,
        "map": MarkType.MAP,
        "pie": MarkType.PIE,
        "ganttBar": MarkType.GANTT,
        "polygon": MarkType.POLYGON,
        "Automatic": MarkType.AUTOMATIC,
    }
    
    def __init__(self, file_path: str):
        """
        Initialize parser with file path.
        
        Args:
            file_path: Path to .twbx or .twb file
        """
        self.file_path = Path(file_path)
        self.workbook_name = self.file_path.stem
        self.is_packaged = self.file_path.suffix.lower() == ".twbx"
        self.temp_dir: Optional[tempfile.TemporaryDirectory] = None
        self.twb_path: Optional[Path] = None
        self.extract_files: List[str] = []
        
    def parse(self) -> TableauWorkbook:
        """
        Parse the Tableau workbook and return structured data.
        
        Returns:
            TableauWorkbook: Parsed workbook model
        """
        try:
            # Extract if packaged
            if self.is_packaged:
                self._extract_twbx()
            else:
                self.twb_path = self.file_path
            
            # Parse the TWB XML
            tree = etree.parse(str(self.twb_path))
            root = tree.getroot()
            
            # Extract workbook version
            version = root.get("version", "unknown")
            
            # Parse all components
            datasources = self._parse_datasources(root)
            parameters = self._parse_parameters(root)
            worksheets = self._parse_worksheets(root)
            dashboards = self._parse_dashboards(root)
            
            # Build workbook model
            workbook = TableauWorkbook(
                name=self.workbook_name,
                version=version,
                datasources=datasources,
                worksheets=worksheets,
                dashboards=dashboards,
                parameters=parameters,
                source_file=str(self.file_path),
                has_extract=len(self.extract_files) > 0,
                extract_files=self.extract_files,
            )
            
            return workbook
            
        finally:
            # Cleanup temp directory
            if self.temp_dir:
                self.temp_dir.cleanup()
    
    def _extract_twbx(self) -> None:
        """Extract TWBX archive to temporary directory."""
        self.temp_dir = tempfile.TemporaryDirectory()
        
        with zipfile.ZipFile(self.file_path, 'r') as zip_ref:
            zip_ref.extractall(self.temp_dir.name)
        
        # Find the .twb file
        for item in os.listdir(self.temp_dir.name):
            if item.endswith(".twb"):
                self.twb_path = Path(self.temp_dir.name) / item
                break
        
        # Find extract files
        data_dir = Path(self.temp_dir.name) / "Data"
        if data_dir.exists():
            for item in data_dir.rglob("*"):
                if item.suffix in [".hyper", ".tde"]:
                    self.extract_files.append(str(item))
        
        if not self.twb_path:
            raise ValueError(f"No .twb file found in {self.file_path}")
    
    def _parse_datasources(self, root: etree._Element) -> List[TableauDataSource]:
        """Parse all data sources from the workbook."""
        datasources = []
        
        for ds_elem in root.findall(".//datasource"):
            # Skip parameters datasource
            ds_name = ds_elem.get("name", "")
            if ds_name == "Parameters":
                continue
            
            datasource = self._parse_single_datasource(ds_elem)
            if datasource:
                datasources.append(datasource)
        
        return datasources
    
    def _parse_single_datasource(self, ds_elem: etree._Element) -> Optional[TableauDataSource]:
        """Parse a single data source element."""
        name = ds_elem.get("name", "Unnamed")
        caption = ds_elem.get("caption")
        
        # Parse connection
        connection = self._parse_connection(ds_elem)
        
        # Parse columns
        columns = self._parse_columns(ds_elem)
        
        # Parse calculated fields
        calculated_fields = self._parse_calculated_fields(ds_elem)
        
        # Parse tables and joins
        tables, joins = self._parse_tables_and_joins(ds_elem)
        
        return TableauDataSource(
            name=name,
            caption=caption,
            connection=connection,
            columns=columns,
            calculated_fields=calculated_fields,
            tables=tables,
            joins=joins,
        )
    
    def _parse_connection(self, ds_elem: etree._Element) -> Optional[TableauConnection]:
        """Parse connection information from a data source."""
        conn_elem = ds_elem.find(".//connection")
        if conn_elem is None:
            return None
        
        class_name = conn_elem.get("class", "unknown")
        
        return TableauConnection(
            class_name=class_name,
            server=conn_elem.get("server"),
            port=int(conn_elem.get("port")) if conn_elem.get("port") else None,
            database=conn_elem.get("dbname"),
            schema_name=conn_elem.get("schema"),
            username=conn_elem.get("username"),
            filename=conn_elem.get("filename"),
            connection_type=self._infer_connection_type(class_name),
        )
    
    def _infer_connection_type(self, class_name: str) -> str:
        """Infer connection type from class name."""
        type_map = {
            "sqlserver": "SQL Server",
            "postgres": "PostgreSQL",
            "mysql": "MySQL",
            "oracle": "Oracle",
            "snowflake": "Snowflake",
            "bigquery": "BigQuery",
            "excel": "Excel",
            "textscan": "CSV/Text",
            "hyper": "Tableau Extract",
            "federated": "Federated",
        }
        return type_map.get(class_name.lower(), class_name)
    
    def _clean_field_name(self, name: str) -> str:
        """
        Clean internal Tableau field names and resolve aliases.
        Example: [federated.14v...].[none:Product Name:nk] -> Product Name
        """
        if not name:
            return ""
            
        # Handle multipart names like [ds].[field] or [field]
        # First, normalize by removing outer brackets if the whole thing is wrapped
        if name.startswith("[") and name.endswith("]"):
            # Check if it's a multipart [A].[B]
            if "].[" in name:
                parts = name.split("].[")
                # Take the last part and clean it
                name = parts[-1].strip("[]")
            else:
                name = name.strip("[]")
        
        # Handle cases like federated.14vgqpy1xbzasr1g68vql17hz4ef.Product Name
        if "." in name and not name.startswith("["):
            parts = name.split(".")
            # If the first part looks like a Tableau internal ID (long hash)
            if len(parts) > 1 and (len(parts[0]) > 15 or parts[0].startswith("federated")):
                name = parts[-1]

        # Handle prefixes like none:Product Name:nk or sum:Sales:qk
        if ":" in name:
            # Common Tableau prefixes in internal names
            prefixes = ["none", "sum", "avg", "min", "max", "count", "countd", "attr", "usr", "calculation"]
            parts = name.split(":")
            
            # If we have prefix:name:suffix or prefix:name
            if parts[0].lower() in prefixes:
                if len(parts) >= 2:
                    name = parts[1]
            elif len(parts) > 1:
                # If not a known prefix, it might be the name itself contains a colon
                # or it's a name:suffix pattern
                name = parts[0]
                
        return name.strip("[] ")

    def _parse_columns(self, ds_elem: etree._Element) -> List[TableauColumn]:
        """Parse column definitions from a data source."""
        columns = []
        
        for col_elem in ds_elem.findall(".//column"):
            name = col_elem.get("name", "")
            caption = col_elem.get("caption")
            
            if not name or name.startswith("[Calculation_"):
                continue
            
            # Clean up field name
            clean_name = self._clean_field_name(name)
            
            # Use caption if available, it's the user-facing name
            display_name = caption if caption else clean_name
            
            datatype_str = col_elem.get("datatype", "string")
            datatype = self.DATATYPE_MAP.get(datatype_str, DataType.UNKNOWN)
            
            role = col_elem.get("role", "dimension")
            hidden = col_elem.get("hidden") == "true"
            
            agg_str = col_elem.get("aggregation", "")
            aggregation = self.AGGREGATION_MAP.get(agg_str, AggregationType.NONE)
            
            columns.append(TableauColumn(
                name=clean_name,
                caption=caption,
                datatype=datatype,
                role=role,
                aggregation=aggregation,
                hidden=hidden,
                semantic_role=col_elem.get("semantic-role"),
            ))
        
        return columns
    
    def _parse_calculated_fields(self, ds_elem: etree._Element) -> List[TableauCalculatedField]:
        """Parse calculated field definitions from a data source."""
        calc_fields = []
        
        for col_elem in ds_elem.findall(".//column"):
            name = col_elem.get("name", "")
            caption = col_elem.get("caption")
            
            # Check if this is a calculated field
            calc_elem = col_elem.find(".//calculation")
            if calc_elem is None:
                continue
            
            formula = calc_elem.get("formula", "")
            if not formula:
                continue
            
            # Clean up field name
            clean_name = self._clean_field_name(name)
            
            # Determine calculation type
            calc_type, lod_dims, table_calc_info = self._analyze_formula(formula)
            
            # Get referenced fields - we should clean these too
            raw_references = self._extract_field_references(formula)
            referenced_fields = [self._clean_field_name(ref) for ref in raw_references]
            
            datatype_str = col_elem.get("datatype", "string")
            datatype = self.DATATYPE_MAP.get(datatype_str, DataType.UNKNOWN)
            
            calc_fields.append(TableauCalculatedField(
                name=clean_name,
                caption=caption,
                formula=formula,
                datatype=datatype,
                calculation_type=calc_type,
                role=col_elem.get("role", "measure"),
                lod_dimensions=[self._clean_field_name(d) for d in lod_dims],
                table_calc_type=table_calc_info.get("type"),
                table_calc_direction=table_calc_info.get("direction"),
                referenced_fields=referenced_fields,
            ))
        
        return calc_fields
    
    def _analyze_formula(self, formula: str) -> Tuple[CalculationType, List[str], Dict[str, str]]:
        """
        Analyze a formula to determine its type and extract metadata.
        
        Returns:
            Tuple of (calculation_type, lod_dimensions, table_calc_info)
        """
        formula_upper = formula.upper()
        lod_dims = []
        table_calc_info = {}
        
        # Check for LOD expressions
        if "{FIXED" in formula_upper:
            lod_dims = self._extract_lod_dimensions(formula)
            return CalculationType.LOD_FIXED, lod_dims, table_calc_info
        elif "{INCLUDE" in formula_upper:
            lod_dims = self._extract_lod_dimensions(formula)
            return CalculationType.LOD_INCLUDE, lod_dims, table_calc_info
        elif "{EXCLUDE" in formula_upper:
            lod_dims = self._extract_lod_dimensions(formula)
            return CalculationType.LOD_EXCLUDE, lod_dims, table_calc_info
        
        # Check for table calculations
        table_calc_patterns = [
            "RUNNING_SUM", "RUNNING_AVG", "RUNNING_COUNT", "RUNNING_MIN", "RUNNING_MAX",
            "WINDOW_SUM", "WINDOW_AVG", "WINDOW_COUNT", "WINDOW_MIN", "WINDOW_MAX",
            "INDEX()", "FIRST()", "LAST()", "SIZE()",
            "LOOKUP", "PREVIOUS_VALUE", "RANK", "RANK_DENSE", "RANK_MODIFIED",
            "RANK_PERCENTILE", "RANK_UNIQUE",
        ]
        
        for pattern in table_calc_patterns:
            if pattern.replace("()", "") in formula_upper:
                table_calc_info["type"] = pattern.replace("()", "").lower()
                return CalculationType.TABLE_CALC, lod_dims, table_calc_info
        
        # Check for aggregate functions
        agg_patterns = ["SUM(", "AVG(", "COUNT(", "COUNTD(", "MIN(", "MAX(", "MEDIAN("]
        for pattern in agg_patterns:
            if pattern in formula_upper:
                return CalculationType.AGGREGATE, lod_dims, table_calc_info
        
        # Default to simple/row-level
        return CalculationType.SIMPLE, lod_dims, table_calc_info
    
    def _extract_lod_dimensions(self, formula: str) -> List[str]:
        """Extract dimension names from LOD expression."""
        # Pattern: {FIXED [Dim1], [Dim2] : ...}
        pattern = r'\{(?:FIXED|INCLUDE|EXCLUDE)\s+([^:]+):'
        match = re.search(pattern, formula, re.IGNORECASE)
        
        if match:
            dims_str = match.group(1)
            # Extract field names in brackets
            dims = re.findall(r'\[([^\]]+)\]', dims_str)
            return dims
        
        return []
    
    def _extract_field_references(self, formula: str) -> List[str]:
        """Extract all field references from a formula."""
        # Fields are in square brackets
        fields = re.findall(r'\[([^\]]+)\]', formula)
        return list(set(fields))
    
    def _parse_parameters(self, root: etree._Element) -> List[TableauParameter]:
        """Parse parameters from the workbook."""
        parameters = []
        
        # Find the Parameters datasource
        params_ds = root.find(".//datasource[@name='Parameters']")
        if params_ds is None:
            return parameters
        
        for col_elem in params_ds.findall(".//column"):
            name = col_elem.get("name", "").strip("[]")
            if not name:
                continue
            
            datatype_str = col_elem.get("datatype", "string")
            datatype = self.DATATYPE_MAP.get(datatype_str, DataType.STRING)
            
            # Get parameter value
            calc_elem = col_elem.find(".//calculation")
            current_value = calc_elem.get("formula") if calc_elem is not None else None
            
            # Parse allowable values
            range_elem = col_elem.find(".//range")
            allowable_type = "all"
            allowable_values = []
            min_val = max_val = step = None
            
            if range_elem is not None:
                range_type = range_elem.get("granularity")
                if range_type:
                    allowable_type = "range"
                    min_val = range_elem.get("min")
                    max_val = range_elem.get("max")
                    step = float(range_elem.get("step", 1))
            
            members_elem = col_elem.find(".//members")
            if members_elem is not None:
                allowable_type = "list"
                for member in members_elem.findall(".//member"):
                    allowable_values.append(member.get("value"))
            
            parameters.append(TableauParameter(
                name=name,
                caption=col_elem.get("caption"),
                datatype=datatype,
                current_value=current_value,
                allowable_values_type=allowable_type,
                allowable_values=allowable_values,
                min_value=min_val,
                max_value=max_val,
                step_size=step,
            ))
        
        return parameters
    
    def _parse_worksheets(self, root: etree._Element) -> List[TableauWorksheet]:
        """Parse all worksheets from the workbook."""
        worksheets = []
        
        for ws_elem in root.findall(".//worksheet"):
            worksheet = self._parse_single_worksheet(ws_elem)
            if worksheet:
                worksheets.append(worksheet)
        
        return worksheets
    
    def _parse_single_worksheet(self, ws_elem: etree._Element) -> Optional[TableauWorksheet]:
        """Parse a single worksheet element."""
        name = ws_elem.get("name", "Unnamed")
        
        # Parse table/view configuration
        table_elem = ws_elem.find(".//table")
        
        # Parse mark type
        mark = TableauMark()
        if table_elem is not None:
            panes = table_elem.find(".//panes")
            if panes is not None:
                mark_elem = panes.find(".//mark")
                if mark_elem is not None:
                    mark_class = mark_elem.get("class", "Automatic")
                    mark.mark_type = self.MARK_TYPE_MAP.get(mark_class, MarkType.AUTOMATIC)
        
        # Parse rows and columns shelves
        rows = self._parse_shelf(ws_elem, "rows")
        columns = self._parse_shelf(ws_elem, "cols")
        
        # Parse encoding shelves (color, size, etc.)
        color_field = self._parse_encoding(ws_elem, "color")
        size_field = self._parse_encoding(ws_elem, "size")
        label_fields = self._parse_encoding_list(ws_elem, "text")
        detail_fields = self._parse_encoding_list(ws_elem, "lod")
        tooltip_fields = self._parse_encoding_list(ws_elem, "tooltip")
        
        # Parse filters
        filters = self._parse_worksheet_filters(ws_elem)
        
        # Get datasource reference
        datasource_name = None
        ds_deps = ws_elem.find(".//datasource-dependencies")
        if ds_deps is not None:
            datasource_name = ds_deps.get("datasource")
        
        return TableauWorksheet(
            name=name,
            title=ws_elem.get("title"),
            mark=mark,
            rows=rows,
            columns=columns,
            filters=filters,
            color_field=color_field,
            size_field=size_field,
            label_fields=label_fields,
            detail_fields=detail_fields,
            tooltip_fields=tooltip_fields,
            datasource_name=datasource_name,
        )
    
    def _parse_shelf(self, ws_elem: etree._Element, shelf_name: str) -> List[FieldMapping]:
        """Parse a shelf (rows or columns) from worksheet."""
        mappings = []
        
        shelf_elem = ws_elem.find(f".//{shelf_name}")
        if shelf_elem is not None:
            shelf_text = shelf_elem.text or ""
            # Parse field references from shelf text
            fields = re.findall(r'\[([^\]]+)\]', shelf_text)
            
            for field in fields:
                # Check for aggregation prefix
                agg = AggregationType.NONE
                field_name = field
                
                # Tableau internal shelf text often looks like [avg:Sales:qk] or [none:Category:nk]
                # or [federated.123].[none:Category:nk]
                
                # Check for aggregation prefixes in the field string
                for agg_name in ["SUM", "AVG", "COUNT", "COUNTD", "MIN", "MAX", "MEDIAN", "ATTR"]:
                    if field.upper().startswith(f"{agg_name}("):
                        agg = self.AGGREGATION_MAP.get(agg_name.lower(), AggregationType.NONE)
                        # Extract inner field
                        inner_match = re.search(r'\(([^)]+)\)', field)
                        if inner_match:
                            field_name = inner_match.group(1)
                        break
                
                # If no aggregation found yet, check for the none: / sum: style in the name itself
                if agg == AggregationType.NONE:
                    if ":" in field:
                        parts = field.split(":")
                        if parts[0].lower() in self.AGGREGATION_MAP:
                            agg = self.AGGREGATION_MAP.get(parts[0].lower())
                
                mappings.append(FieldMapping(
                    field=self._clean_field_name(field_name),
                    shelf=shelf_name,
                    aggregation=agg,
                ))
        
        return mappings
    
    def _parse_encoding(self, ws_elem: etree._Element, encoding_type: str) -> Optional[FieldMapping]:
        """Parse a single encoding shelf (color, size)."""
        # Look for encoding in pane marks
        encoding_elem = ws_elem.find(f".//panes//mark[@class]//encoding[@attr='{encoding_type}']")
        if encoding_elem is not None:
            field = encoding_elem.get("column", "")
            if field:
                return FieldMapping(
                    field=self._clean_field_name(field),
                    shelf=encoding_type,
                )
        return None
    
    def _parse_encoding_list(self, ws_elem: etree._Element, encoding_type: str) -> List[FieldMapping]:
        """Parse encoding shelves that can have multiple fields."""
        mappings = []
        
        for encoding_elem in ws_elem.findall(f".//panes//mark[@class]//encoding[@attr='{encoding_type}']"):
            field = encoding_elem.get("column", "")
            if field:
                mappings.append(FieldMapping(
                    field=self._clean_field_name(field),
                    shelf=encoding_type,
                ))
        
        return mappings
    
    def _parse_worksheet_filters(self, ws_elem: etree._Element) -> List[TableauFilter]:
        """Parse filters applied to a worksheet."""
        filters = []
        
        for filter_elem in ws_elem.findall(".//filter"):
            field_raw = filter_elem.get("column", "")
            if not field_raw:
                continue
            
            field = self._clean_field_name(field_raw)
            
            filter_type = "categorical"
            values = []
            
            # Check for categorical filter
            groupfilter = filter_elem.find(".//groupfilter")
            if groupfilter is not None:
                function = groupfilter.get("function", "")
                if function == "member":
                    values.append(groupfilter.get("member"))
                elif function in ["union", "intersection"]:
                    for member in groupfilter.findall(".//groupfilter[@function='member']"):
                        values.append(member.get("member"))
            
            filters.append(TableauFilter(
                field=field,
                filter_type=filter_type,
                values=values,
            ))
        
        return filters
    
    def _parse_dashboards(self, root: etree._Element) -> List[TableauDashboard]:
        """Parse all dashboards from the workbook."""
        dashboards = []
        
        for dash_elem in root.findall(".//dashboard"):
            dashboard = self._parse_single_dashboard(dash_elem)
            if dashboard:
                dashboards.append(dashboard)
        
        return dashboards
    
    def _parse_single_dashboard(self, dash_elem: etree._Element) -> Optional[TableauDashboard]:
        """Parse a single dashboard element."""
        name = dash_elem.get("name", "Unnamed")
        
        # Parse size
        size_elem = dash_elem.find(".//size")
        width = int(size_elem.get("maxwidth", 1000)) if size_elem is not None else 1000
        height = int(size_elem.get("maxheight", 800)) if size_elem is not None else 800
        
        # Parse zones (dashboard objects)
        objects = []
        for zone_elem in dash_elem.findall(".//zone"):
            obj = self._parse_dashboard_zone(zone_elem)
            if obj:
                objects.append(obj)
        
        # Parse actions
        actions = self._parse_dashboard_actions(dash_elem)
        
        return TableauDashboard(
            name=name,
            title=dash_elem.get("title"),
            width=width,
            height=height,
            objects=objects,
            actions=actions,
        )
    
    def _parse_dashboard_zone(self, zone_elem: etree._Element) -> Optional[DashboardObject]:
        """Parse a dashboard zone into a DashboardObject."""
        zone_name = zone_elem.get("name", "")
        zone_type = zone_elem.get("type", "")
        
        # Determine object type
        obj_type = "blank"
        worksheet_name = None
        
        if zone_type == "text":
            obj_type = "text"
        elif zone_type == "web":
            obj_type = "web"
        elif zone_type == "image":
            obj_type = "image"
        elif zone_name:
            obj_type = "worksheet"
            worksheet_name = zone_name
        
        # Get position and size
        x = float(zone_elem.get("x", 0))
        y = float(zone_elem.get("y", 0))
        w = float(zone_elem.get("w", 100))
        h = float(zone_elem.get("h", 100))
        
        return DashboardObject(
            object_type=obj_type,
            name=zone_name,
            worksheet_name=worksheet_name,
            x=x,
            y=y,
            width=w,
            height=h,
        )
    
    def _parse_dashboard_actions(self, dash_elem: etree._Element) -> List[Dict[str, Any]]:
        """Parse dashboard actions (filter, highlight, URL)."""
        actions = []
        
        for action_elem in dash_elem.findall(".//action"):
            action = {
                "name": action_elem.get("name", ""),
                "type": action_elem.get("type", ""),
            }
            
            # Parse source and target worksheets
            source_elem = action_elem.find(".//source")
            if source_elem is not None:
                action["source"] = source_elem.get("worksheet")
            
            target_elem = action_elem.find(".//target")
            if target_elem is not None:
                action["target"] = target_elem.get("worksheet")
            
            actions.append(action)
        
        return actions
    
    def _parse_tables_and_joins(self, ds_elem: etree._Element) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Parse table names and join relationships from a data source."""
        tables = []
        joins = []
        
        # Find relation elements
        for relation in ds_elem.findall(".//relation"):
            table_name = relation.get("name") or relation.get("table")
            if table_name and table_name not in tables:
                tables.append(table_name)
            
            # Check for joins
            join_type = relation.get("join")
            if join_type:
                left_table = None
                right_table = None
                
                for clause in relation.findall(".//clause"):
                    expression = clause.find(".//expression")
                    if expression is not None:
                        op = expression.get("op")
                        if op == "=":
                            # This is a join condition
                            pass
                
                if left_table and right_table:
                    joins.append({
                        "type": join_type,
                        "left_table": left_table,
                        "right_table": right_table,
                    })
        
        return tables, joins
