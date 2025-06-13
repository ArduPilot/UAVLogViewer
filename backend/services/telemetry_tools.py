"""
Telemetry Analysis Tools

This module implements concrete analysis tools for flight data.
Each tool performs specific analysis tasks like querying telemetry data,
calculating statistics, or detecting anomalies.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Union
from uuid import UUID

from services.tool_registry import BaseTool
from services.types import ToolResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Column sanitisation utility
# ---------------------------------------------------------------------------


def sanitize_columns(columns: List[str]) -> List[str]:
    """Return a safe list of column identifiers for SQL interpolation.

    The function performs *very* conservative cleaning – it strips quotes and
    maps a handful of convenience aliases (``altitude`` → ``alt``,
    ``timestamp`` → ``timestamp_utc``).  No other transformations are carried
    out.  The returned identifiers should be interpolated **directly** into
    SQL (not passed as parameters) *only* after this sanitisation.
    """
    sanitized: List[str] = []
    for raw in columns:
        col = raw.replace('"', "").replace("'", "")  # strip quoting chars
        if col in {"altitude", "relative_altitude"}:
            sanitized.append("alt")
        elif col == "timestamp":
            sanitized.append("timestamp_utc")
        else:
            sanitized.append(col)
    return sanitized


class FlightSummaryTool(BaseTool):
    """Tool to get a quick summary of flight metrics and metadata."""

    @property
    def name(self) -> str:
        return "get_flight_summary"

    @property
    def description(self) -> str:
        return "Get a comprehensive summary of the flight including duration, distance, altitude, and key metrics"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "include_errors": {
                    "type": "boolean",
                    "description": "Whether to include error and warning counts.  Set to false when you only need performance metrics without diagnostic information.",
                    "default": True,
                }
            },
            "required": [],
        }

    async def execute(self, include_errors: bool = True, **kwargs) -> ToolResult:
        """Execute flight summary analysis."""
        try:
            # Get session data from SQLite
            session_data = await self.sqlite_manager.get_session(self.session_id)
            if not session_data:
                raise ValueError(f"Session {self.session_id} not found")

            # Build comprehensive summary
            summary = {
                "session_id": str(self.session_id),
                "filename": session_data.get("filename"),
                "log_type": session_data.get("log_type"),
                "status": session_data.get("status"),
                # Flight timing
                "flight_duration_seconds": session_data.get("flight_duration_seconds"),
                "start_time": session_data.get("start_time"),
                "end_time": session_data.get("end_time"),
                # Basic metrics
                "max_altitude_m": session_data.get("max_altitude_m"),
                "min_altitude_m": session_data.get("min_altitude_m"),
                "max_speed_ms": session_data.get("max_speed_ms"),
                "total_distance_km": session_data.get("total_distance_km"),
                # Vehicle information
                "vehicle_type": session_data.get("vehicle_type"),
                "flight_modes_used": self._parse_json_field(
                    session_data.get("flight_modes_used")
                ),
                # GPS fix quality is often misinterpreted; omit to avoid misleading conclusions
                # "gps_fix_type_max": session_data.get("gps_fix_type_max"),
                # Data availability
                "message_count": session_data.get("message_count"),
                "available_message_types": self._parse_json_field(
                    session_data.get("available_message_types")
                ),
            }

            # Add error information if requested
            if include_errors:
                summary.update(
                    {
                        "error_count": session_data.get("error_count", 0),
                        "warning_count": session_data.get("warning_count", 0),
                    }
                )

            # Calculate derived metrics
            summary["flight_duration_minutes"] = (
                summary["flight_duration_seconds"] / 60.0
                if summary["flight_duration_seconds"]
                else None
            )

            metadata = {
                "source": "session_metadata",
                "fields_included": len([v for v in summary.values() if v is not None]),
            }

            return ToolResult(
                tool_name=self.name,
                call_id=None,
                success=True,
                data=summary,
                metadata=metadata,
                execution_time=0.0,  # Will be set by _safe_execute
            )

        except Exception as e:
            logger.error(f"FlightSummaryTool failed: {e}")
            raise

    def _parse_json_field(self, field_value: Any) -> Any:
        """Parse JSON string fields safely."""
        if isinstance(field_value, str):
            try:
                return json.loads(field_value)
            except json.JSONDecodeError:
                return field_value
        return field_value


class SessionInfoTool(BaseTool):
    """Tool to get basic session information and upload details."""

    @property
    def name(self) -> str:
        return "get_session_info"

    @property
    def description(self) -> str:
        return "Get basic session information including filename, file size, upload time, and processing status"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, **kwargs) -> ToolResult:
        """Execute session info query."""
        try:
            session_data = await self.sqlite_manager.get_session(self.session_id)
            if not session_data:
                raise ValueError(f"Session {self.session_id} not found")

            info = {
                "session_id": str(self.session_id),
                "filename": session_data.get("filename"),
                "file_size": session_data.get("file_size"),
                "log_type": session_data.get("log_type"),
                "status": session_data.get("status"),
                "created_at": session_data.get("created_at"),
                "processed_at": session_data.get("processed_at"),
                "error_message": session_data.get("error_message"),
            }

            metadata = {"source": "session_table", "status": session_data.get("status")}

            return ToolResult(
                tool_name=self.name,
                call_id=None,
                success=True,
                data=info,
                metadata=metadata,
                execution_time=0.0,
            )

        except Exception as e:
            logger.error(f"SessionInfoTool failed: {e}")
            raise


class DataAvailabilityTool(BaseTool):
    """Tool to check what telemetry data is available for analysis."""

    @property
    def name(self) -> str:
        return "check_data_availability"

    @property
    def description(self) -> str:
        return "Check what types of telemetry data are available and their data density/coverage"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message_type": {
                    "type": "string",
                    "description": "Telemetry table (or raw message type). Omit for overview.",
                    "enum": [
                        "gps_telemetry",
                        "attitude_telemetry",
                        "sensor_telemetry",
                        "flight_events",
                        "system_status",
                    ],
                    "enumDescriptions": [
                        "lat/lon/alt, velocities, fix_type, satellites",
                        "roll, pitch, yaw angles and angular rates",
                        "raw IMU accel/gyro/mag axes",
                        "event_type, event_description, severity (error/warn)",
                        "battery voltage/current/temp, radio RSSI/noise, mode, armed flag",
                    ],
                }
            },
            "required": [],
        }

    async def execute(self, message_type: Optional[str] = None, **kwargs) -> ToolResult:
        """Execute data availability check with awareness of logical table names."""
        try:
            # Mapping of logical table names to underlying raw message types for backward-compatibility
            TABLE_TO_MSG_TYPES = {
                "gps_telemetry": [
                    "GLOBAL_POSITION_INT",
                    "GPS_RAW_INT",
                    "GPS2_RAW",
                    "GPS",
                    "POS",
                ],
                "attitude_telemetry": ["ATTITUDE", "AHR2", "ATT"],
                "sensor_telemetry": ["RAW_IMU", "SCALED_IMU", "IMU"],
                "flight_events": ["STATUSTEXT", "MODE", "MSG", "ERR"],
                "system_status": [
                    "SYS_STATUS",
                    "BATTERY_STATUS",
                    "POWR",
                    "RADIO_STATUS",
                    "BARO",
                ],
            }

            # Fetch cached list of raw message types parsed
            session_data = await self.sqlite_manager.get_session(self.session_id)
            if not session_data:
                raise ValueError(f"Session {self.session_id} not found")

            available_raw = session_data.get("available_message_types", [])
            if isinstance(available_raw, str):
                import json

                try:
                    available_raw = json.loads(available_raw)
                except json.JSONDecodeError:
                    available_raw = []

            conn = self.duckdb_manager.get_connection()

            def table_row_count(tbl: str) -> int:
                try:
                    return conn.execute(
                        f"SELECT COUNT(*) FROM {tbl} WHERE session_id = ?",
                        [str(self.session_id)],
                    ).fetchone()[0]
                except Exception:
                    return 0  # Table missing or other error

            # If a specific message_type/table requested --------------------------------
            if message_type:
                # First treat as logical table name
                rows = table_row_count(message_type)
                if rows > 0:
                    return ToolResult(
                        tool_name=self.name,
                        call_id=None,
                        success=True,
                        data={"available": True, "rows": rows, "table": message_type},
                        metadata={"query_type": "table_name"},
                        execution_time=0.0,
                    )

                # Fallback – treat as raw message type
                is_available = message_type in available_raw
                return ToolResult(
                    tool_name=self.name,
                    call_id=None,
                    success=True,
                    data={"available": is_available, "message_type": message_type},
                    metadata={"query_type": "raw_message_type"},
                    execution_time=0.0,
                )

            # No specific message_type – return overview ----------------------------------
            overview = {}
            for tbl in TABLE_TO_MSG_TYPES.keys():
                overview[tbl] = table_row_count(tbl)

            return ToolResult(
                tool_name=self.name,
                call_id=None,
                success=True,
                data=overview,
                metadata={"query_type": "overview", "tables_checked": len(overview)},
                execution_time=0.0,
            )

        except Exception as e:
            logger.error(f"DataAvailabilityTool failed: {e}")
            raise


class TelemetryQueryTool(BaseTool):
    """Tool to query telemetry data from DuckDB with flexible filtering."""

    @property
    def name(self) -> str:
        return "query_telemetry"

    @property
    def description(self) -> str:
        return "Query telemetry data with flexible filtering by message type, time range, and columns"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message_type": {
                    "type": "string",
                    "description": "Telemetry table to query (run 'check_data_availability' first).",
                    "enum": [
                        "gps_telemetry",
                        "attitude_telemetry",
                        "sensor_telemetry",
                        "flight_events",
                        "system_status",
                    ],
                    "enumDescriptions": [
                        "lat/lon/alt, velocities, fix_type, satellites",
                        "roll, pitch, yaw angles and angular rates",
                        "raw IMU accel/gyro/mag axes",
                        "event_type, event_description, severity (error/warn)",
                        "battery voltage/current/temp, radio RSSI/noise, mode, armed flag",
                    ],
                },
                "columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific columns to retrieve.  Use to minimise payload size – e.g. ['time_boot_ms', 'alt'] – otherwise the entire row is returned.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of rows to return.  Start small (<=100) when exploring; may be increased up to 1000 for bulk downloads.",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 1000,
                },
                "start_time": {
                    "type": "number",
                    "description": "Start of window (UTC ms).  Retrieve the session start_time via 'get_flight_summary' and add your offset (e.g. +60000 for first minute).",
                },
                "end_time": {
                    "type": "number",
                    "description": "End of window (UTC ms, exclusive).  Pair with start_time to bound the query to a segment.",
                },
            },
            "required": ["message_type"],
        }

    async def execute(
        self,
        message_type: str,
        columns: Optional[List[str]] = None,
        limit: int = 100,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        **kwargs,
    ) -> ToolResult:
        """Execute telemetry query with validation and alias support."""
        try:
            # Map common aliases to real column names
            alias_map = {
                "event_id": "event_type",
                "message": "event_description",
                "severity_level": "severity",
                "timestamp": "timestamp_utc",
                "time": "time_boot_ms",
            }

            # Validate limit against tool registry limits
            max_allowed = 1000  # Could be configurable
            limit = min(limit, max_allowed)

            conn = self.duckdb_manager.get_connection()

            # Retrieve real columns from DuckDB for validation
            try:
                table_info = conn.execute(
                    f"PRAGMA table_info('{message_type}')"
                ).fetchall()
                real_columns = {row[1] for row in table_info}
            except Exception as e:
                return ToolResult(
                    tool_name=self.name,
                    call_id=None,
                    success=False,
                    data=None,
                    metadata={"error_type": "database_error"},
                    execution_time=0.0,
                    error_message=f"Table '{message_type}' not found or inaccessible: {e}",
                )

            # -----------------------------------------------------------------
            # Column handling (alias resolution + validation)
            # -----------------------------------------------------------------
            selected_columns: List[str] = []
            invalid_columns: List[str] = []

            if columns:
                for col in columns:
                    real_col = alias_map.get(col, col)
                    if real_col in real_columns:
                        selected_columns.append(real_col)
                    else:
                        invalid_columns.append(col)

                if invalid_columns:
                    return ToolResult(
                        tool_name=self.name,
                        call_id=None,
                        success=False,
                        data=None,
                        metadata={
                            "reason": "invalid_columns",
                            "invalid": invalid_columns,
                            "valid_columns": sorted(real_columns),
                        },
                        execution_time=0.0,
                        error_message="One or more requested columns are invalid.",
                    )
            else:
                selected_columns = list(real_columns)

            # Build SELECT clause
            column_str = ", ".join(selected_columns) if selected_columns else "*"

            # Build query
            query = f"SELECT {column_str} FROM {message_type} WHERE session_id = ?"
            params = [str(self.session_id)]

            # Add time filters
            if start_time is not None:
                query += " AND timestamp_utc >= EPOCH_MS(?)"
                params.append(int(start_time))

            if end_time is not None:
                query += " AND timestamp_utc < EPOCH_MS(?)"
                params.append(int(end_time))

            # Add ordering and limit
            query += " ORDER BY timestamp_utc LIMIT ?"
            params.append(limit)

            # Execute query
            try:
                result = conn.execute(query, params).fetchall()
                column_names = (
                    [desc[0] for desc in conn.description] if conn.description else []
                )

                data = [dict(zip(column_names, row)) for row in result]

                metadata = {
                    "query": query,
                    "row_count": len(data),
                    "columns": column_names,
                    "message_type": message_type,
                    "limit_applied": limit,
                    "source": "duckdb_telemetry",
                }

                return ToolResult(
                    tool_name=self.name,
                    call_id=None,
                    success=True,
                    data=data,
                    metadata=metadata,
                    execution_time=0.0,
                )
            except Exception as query_error:
                return ToolResult(
                    tool_name=self.name,
                    call_id=None,
                    success=False,
                    data=None,
                    metadata={"query": query, "error_type": "database_error"},
                    execution_time=0.0,
                    error_message=f"Database query failed: {query_error}",
                )

        except Exception as e:
            logger.error(f"TelemetryQueryTool failed: {e}")
            raise


class StatisticsTool(BaseTool):
    """Tool to calculate statistics on telemetry data."""

    @property
    def name(self) -> str:
        return "calculate_statistics"

    @property
    def description(self) -> str:
        return "Calculate statistical measures (min, max, mean, std, percentiles) for telemetry data columns"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message_type": {
                    "type": "string",
                    "description": "Type of telemetry message to analyze",
                    "enum": [
                        "gps_telemetry",
                        "attitude_telemetry",
                        "sensor_telemetry",
                        "system_status",
                    ],
                },
                "column": {
                    "type": "string",
                    "description": "Column name to calculate statistics for",
                },
                "operations": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "min",
                            "max",
                            "mean",
                            "median",
                            "std",
                            "count",
                            "percentile_25",
                            "percentile_75",
                            "percentile_95",
                            "iqr",
                            "zscore",
                        ],
                    },
                    "description": "Statistical operations to perform.  Classic aggregations ('min', 'mean', …) give raw statistics.  Use 'iqr' to understand central spread/outliers, 'zscore' to count anomalies beyond the threshold.",
                    "default": ["min", "max", "mean", "count"],
                },
                "start_time": {
                    "type": "number",
                    "description": "(Optional) Start of analysis window (inclusive, UTC ms).  Obtain session start_time from 'get_flight_summary' and add offset to focus on a flight phase.",
                },
                "end_time": {
                    "type": "number",
                    "description": "(Optional) End of analysis window (exclusive, UTC ms).  Pair with start_time to bound the statistics to a segment.",
                },
                "threshold": {
                    "type": "number",
                    "description": "Z-score threshold (absolute value) for outlier detection.  Typical values: 2–3.  Ignored unless 'zscore' is among operations.",
                    "default": 3.0,
                },
            },
            "required": ["message_type", "column"],
        }

    async def execute(
        self,
        message_type: str,
        column: str,
        operations: List[str] = None,
        threshold: float = 3.0,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        **kwargs,
    ) -> ToolResult:
        """Execute statistical analysis."""
        try:
            if operations is None:
                operations = ["min", "max", "mean", "count"]

            # Alias map similar to TelemetryQueryTool to translate user-friendly names
            alias_map = {
                "value": column,  # will be resolved after validation
                "timestamp": "timestamp_utc",
                "time": "time_boot_ms",
            }

            conn = self.duckdb_manager.get_connection()

            # Fetch actual columns for validation
            try:
                real_cols = {
                    row[1]
                    for row in conn.execute(
                        f"PRAGMA table_info('{message_type}')"
                    ).fetchall()
                }
            except Exception as e:
                return ToolResult(
                    tool_name=self.name,
                    call_id=None,
                    success=False,
                    data=None,
                    metadata={"error_type": "database_error"},
                    execution_time=0.0,
                    error_message=f"Table '{message_type}' not found: {e}",
                )

            # Resolve alias
            resolved_col = alias_map.get(column, column)

            if resolved_col not in real_cols:
                return ToolResult(
                    tool_name=self.name,
                    call_id=None,
                    success=False,
                    data=None,
                    metadata={
                        "reason": "invalid_column",
                        "invalid": column,
                        "valid_columns": sorted(real_cols),
                    },
                    execution_time=0.0,
                    error_message=f"Column '{column}' not found in table '{message_type}'",
                )

            column = resolved_col  # use validated column

            # -----------------------------------------------------------------
            # WHERE-clause construction (session + non-null + optional window)
            # -----------------------------------------------------------------
            where_clauses = ["session_id = ?", f"{column} IS NOT NULL"]
            params: List[Any] = [str(self.session_id)]

            if start_time is not None:
                where_clauses.append("timestamp_utc >= EPOCH_MS(?)")
                params.append(int(start_time))

            if end_time is not None:
                where_clauses.append("timestamp_utc < EPOCH_MS(?)")  # end exclusive
                params.append(int(end_time))

            where_sql = " AND ".join(where_clauses)

            # -----------------------------------------------------------------
            # Primary aggregation query for standard operations (if any)
            # -----------------------------------------------------------------
            statistics: Dict[str, Any] = {}

            standard_ops = [op for op in operations if op not in {"iqr", "zscore"}]

            if standard_ops:
                stat_functions: List[str] = []
                for op in standard_ops:
                    if op == "std":
                        stat_functions.append(f"STDDEV({column}) as std")
                    elif op == "percentile_25":
                        stat_functions.append(
                            f"PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY {column}) as percentile_25"
                        )
                    elif op == "percentile_75":
                        stat_functions.append(
                            f"PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY {column}) as percentile_75"
                        )
                    elif op == "percentile_95":
                        stat_functions.append(
                            f"PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY {column}) as percentile_95"
                        )
                    elif op == "median":
                        stat_functions.append(
                            f"PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {column}) as median"
                        )
                    else:
                        stat_functions.append(f"{op.upper()}({column}) as {op}")

                agg_query = (
                    f"SELECT {', '.join(stat_functions)} FROM {message_type} "
                    f"WHERE {where_sql}"
                )

                row = conn.execute(agg_query, params).fetchone()
                if row:
                    for i, op in enumerate(standard_ops):
                        statistics[op] = row[i]

            # -----------------------------------------------------------------
            # IQR calculation, if requested
            # -----------------------------------------------------------------
            if "iqr" in operations:
                iqr_query = (
                    f"SELECT PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY {column}) as q1, "
                    f"PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY {column}) as q3 "
                    f"FROM {message_type} WHERE {where_sql}"
                )
                q1, q3 = conn.execute(iqr_query, params).fetchone()
                if q1 is not None and q3 is not None:
                    iqr_val = q3 - q1
                    statistics["iqr"] = {
                        "q1": q1,
                        "q3": q3,
                        "iqr": iqr_val,
                        "lower_whisker": q1 - 1.5 * iqr_val,
                        "upper_whisker": q3 + 1.5 * iqr_val,
                    }

            # -----------------------------------------------------------------
            # Z-score outlier summary, if requested
            # -----------------------------------------------------------------
            if "zscore" in operations:
                # Build robust query using CTEs to avoid GROUP BY issues
                z_query = (
                    f"WITH base AS (\n"
                    f"  SELECT {column} AS value\n"
                    f"  FROM {message_type}\n"
                    f"  WHERE {where_sql}\n"
                    f"), stats AS (\n"
                    f"  SELECT AVG(value) AS mean_val, STDDEV(value) AS std_val FROM base\n"
                    f"), outliers AS (\n"
                    f"  SELECT COUNT(*) AS outlier_count FROM base, stats\n"
                    f"  WHERE stats.std_val > 0 AND ABS((value - stats.mean_val)/stats.std_val) > ?\n"
                    f")\n"
                    f"SELECT stats.mean_val, stats.std_val, outliers.outlier_count\n"
                    f"FROM stats, outliers"
                )

                z_params = params + [threshold]

                mean_val, std_val, outliers = conn.execute(z_query, z_params).fetchone()
                statistics["zscore"] = {
                    "mean": mean_val,
                    "std": std_val,
                    "threshold": threshold,
                    "outlier_count": outliers,
                }

            # -----------------------------------------------------------------
            # Prepare ToolResult
            # -----------------------------------------------------------------
            if statistics:
                data = {
                    "column": column,
                    "message_type": message_type,
                    "window": {
                        "start_time": start_time,
                        "end_time": end_time,
                    },
                    "statistics": statistics,
                }

                metadata = {
                    "operations_performed": operations,
                    "source": "duckdb_aggregation",
                    "row_filter": where_sql,
                }

                return ToolResult(
                    tool_name=self.name,
                    call_id=None,
                    success=True,
                    data=data,
                    metadata=metadata,
                    execution_time=0.0,
                )

            # If no stats produced
            return ToolResult(
                tool_name=self.name,
                call_id=None,
                success=False,
                data=None,
                metadata={"reason": "no_data"},
                execution_time=0.0,
                error_message=f"No data found for {column} in {message_type}",
            )

        except Exception as e:
            logger.error(f"StatisticsTool failed: {e}")
            raise


# --- Temporarily disabled AnomalyDetectionTool --------------------------------
'''
class AnomalyDetectionTool(BaseTool):
    """Tool to detect simple anomalies in telemetry data."""

    @property
    def name(self) -> str:
        return "detect_anomalies"

    @property
    def description(self) -> str:
        return "Detect anomalies in telemetry data using statistical methods (Z-score, IQR)"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message_type": {
                    "type": "string",
                    "description": "Type of telemetry message to analyze",
                    "enum": [
                        "gps_telemetry",
                        "attitude_telemetry",
                        "sensor_telemetry",
                        "system_status",
                    ],
                },
                "column": {
                    "type": "string",
                    "description": "Column name to analyze for anomalies",
                },
                "method": {
                    "type": "string",
                    "description": "Anomaly detection method",
                    "enum": ["zscore", "iqr"],
                    "default": "zscore",
                },
                "threshold": {
                    "type": "number",
                    "description": "Threshold for anomaly detection (e.g., 3.0 for Z-score)",
                    "default": 3.0,
                },
            },
            "required": ["message_type", "column"],
        }

    async def execute(
        self,
        message_type: str,
        column: str,
        method: str = "zscore",
        threshold: float = 3.0,
        **kwargs,
    ) -> ToolResult:
        """Execute anomaly detection."""
        try:
            if method == "zscore":
                # Z-score based anomaly detection
                query = f"""
                    WITH stats AS (
                        SELECT 
                            AVG({column}) as mean_val,
                            STDDEV({column}) as std_val
                        FROM {message_type}
                        WHERE session_id = ? AND {column} IS NOT NULL
                    ),
                    anomalies AS (
                        SELECT 
                            timestamp,
                            {column} as value,
                            ABS(({column} - stats.mean_val) / stats.std_val) as zscore
                        FROM {message_type}, stats
                        WHERE session_id = ? 
                            AND {column} IS NOT NULL
                            AND ABS(({column} - stats.mean_val) / stats.std_val) > ?
                        ORDER BY timestamp
                        LIMIT 100
                    )
                    SELECT * FROM anomalies
                """
                params = [str(self.session_id), str(self.session_id), threshold]

            elif method == "iqr":
                # IQR-based anomaly detection
                query = f"""
                    WITH quartiles AS (
                        SELECT 
                            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY {column}) as q1,
                            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY {column}) as q3
                        FROM {message_type}
                        WHERE session_id = ? AND {column} IS NOT NULL
                    ),
                    anomalies AS (
                        SELECT 
                            timestamp,
                            {column} as value,
                            CASE 
                                WHEN {column} < (q1 - {threshold} * (q3 - q1)) THEN 'low_outlier'
                                WHEN {column} > (q3 + {threshold} * (q3 - q1)) THEN 'high_outlier'
                            END as anomaly_type
                        FROM {message_type}, quartiles
                        WHERE session_id = ? 
                            AND {column} IS NOT NULL
                            AND ({column} < (q1 - {threshold} * (q3 - q1)) 
                                 OR {column} > (q3 + {threshold} * (q3 - q1)))
                        ORDER BY timestamp
                        LIMIT 100
                    )
                    SELECT * FROM anomalies
                """
                params = [str(self.session_id), str(self.session_id)]

            else:
                raise ValueError(f"Unknown anomaly detection method: {method}")

            conn = self.duckdb_manager.get_connection()

            try:
                result = conn.execute(query, params).fetchall()
                column_names = (
                    [desc[0] for desc in conn.description] if conn.description else []
                )

                # Convert to list of dictionaries
                anomalies = []
                for row in result:
                    anomalies.append(dict(zip(column_names, row)))

                data = {
                    "method": method,
                    "column": column,
                    "message_type": message_type,
                    "threshold": threshold,
                    "anomalies_found": len(anomalies),
                    "anomalies": anomalies,
                }

                metadata = {
                    "method": method,
                    "threshold": threshold,
                    "anomaly_count": len(anomalies),
                    "source": "duckdb_analysis",
                }

                return ToolResult(
                    tool_name=self.name,
                    call_id=None,
                    success=True,
                    data=data,
                    metadata=metadata,
                    execution_time=0.0,
                )

            except Exception as query_error:
                error_msg = f"Anomaly detection failed: {str(query_error)}"
                return ToolResult(
                    tool_name=self.name,
                    call_id=None,
                    success=False,
                    data=None,
                    metadata={"query": query, "error_type": "database_error"},
                    execution_time=0.0,
                    error_message=error_msg,
                )

        except Exception as e:
            logger.error(f"AnomalyDetectionTool failed: {e}")
            raise
'''


class TableInfoTool(BaseTool):
    """Tool to list available columns for a telemetry table."""

    @property
    def name(self) -> str:
        return "list_table_columns"

    @property
    def description(self) -> str:
        return "List all column names available for a given telemetry table so the LLM can craft valid queries."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message_type": {
                    "type": "string",
                    "description": "Telemetry table to inspect (columns list).",
                    "enum": [
                        "gps_telemetry",
                        "attitude_telemetry",
                        "sensor_telemetry",
                        "flight_events",
                        "system_status",
                    ],
                    "enumDescriptions": [
                        "lat/lon/alt, velocities, fix_type, satellites",
                        "roll, pitch, yaw angles and angular rates",
                        "raw IMU accel/gyro/mag axes",
                        "event_type, event_description, severity (error/warn)",
                        "battery voltage/current/temp, radio RSSI/noise, mode, armed flag",
                    ],
                }
            },
            "required": ["message_type"],
        }

    async def execute(self, message_type: str, **kwargs) -> ToolResult:
        try:
            conn = self.duckdb_manager.get_connection()
            table_info = conn.execute(f"PRAGMA table_info('{message_type}')").fetchall()
            columns = [row[1] for row in table_info]

            return ToolResult(
                tool_name=self.name,
                call_id=None,
                success=True,
                data={"columns": columns, "table": message_type},
                metadata={"source": "duckdb_schema", "column_count": len(columns)},
                execution_time=0.0,
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                call_id=None,
                success=False,
                data=None,
                metadata={"error_type": "database_error"},
                execution_time=0.0,
                error_message=str(e),
            )


# ---------------------------------------------------------------------------
# Documentation fetch tool
# ---------------------------------------------------------------------------


class DocumentationFetchTool(BaseTool):
    """Tool to fetch raw HTML (or text) from a URL with simple pagination."""

    @property
    def name(self) -> str:
        return "fetch_url_content"

    @property
    def description(self) -> str:
        return (
            "Retrieve portions of the official ArduPilot log-message documentation (https://ardupilot.org/plane/docs/logmessages.html). "
            "Use offset & max_chars to paginate large pages so you can look up the meaning of a specific column or message."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "offset": {
                    "type": "integer",
                    "description": "Character offset in the page from which to start returning content (for pagination)",
                    "default": 0,
                    "minimum": 0,
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum number of characters to return in this call (server cap 4000)",
                    "default": 2000,
                    "minimum": 100,
                    "maximum": 4000,
                },
                "as_text": {
                    "type": "boolean",
                    "description": "If true, attempt to strip HTML tags and return plain text. If false, return raw HTML.",
                    "default": True,
                },
            },
            "required": [],
        }

    async def execute(
        self,
        offset: int = 0,
        max_chars: int = 10000,
        as_text: bool = True,
        **kwargs,
    ) -> ToolResult:
        """Fetch URL content safely with timeout and pagination."""
        import asyncio
        import re
        from html import unescape
        from html.parser import HTMLParser
        import requests

        DOC_URL = "https://ardupilot.org/plane/docs/logmessages.html"

        class _TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.parts: list[str] = []

            def handle_data(self, data: str):
                if data and not data.isspace():
                    self.parts.append(data)

            def get_text(self) -> str:
                return " ".join(self.parts)

        def _fetch() -> str:
            resp = requests.get(DOC_URL, timeout=8)
            resp.raise_for_status()
            return resp.text

        try:
            loop = asyncio.get_running_loop()
            html_content: str = await loop.run_in_executor(None, _fetch)

            if as_text:
                extractor = _TextExtractor()
                extractor.feed(html_content)
                text_content = unescape(extractor.get_text())
                # collapse whitespace
                text_content = re.sub(r"\s+", " ", text_content)
                content = text_content
            else:
                content = html_content

            total_len = len(content)
            # Guard bounds
            if offset < 0:
                offset = 0
            if max_chars < 100:
                max_chars = 100
            if max_chars > 4000:
                max_chars = 10000

            slice_end = min(offset + max_chars, total_len)
            paginated = content[offset:slice_end]

            metadata = {
                "url": DOC_URL,
                "offset": offset,
                "returned_chars": len(paginated),
                "total_chars": total_len,
                "has_more": slice_end < total_len,
                "as_text": as_text,
            }

            return ToolResult(
                tool_name=self.name,
                call_id=None,
                success=True,
                data=paginated,
                metadata=metadata,
                execution_time=0.0,  # Filled by _safe_execute
            )
        except Exception as e:
            logger.error(f"DocumentationFetchTool failed: {e}")
            raise
