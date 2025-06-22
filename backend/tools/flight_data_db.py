import duckdb
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import os
import logging
from pathlib import Path
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FlightDataDBError(Exception):
    """Base exception class for FlightDataDB errors"""
    pass

class DatabaseConnectionError(FlightDataDBError):
    """Raised when there are issues with database connections"""
    pass

class DataValidationError(FlightDataDBError):
    """Raised when data validation fails"""
    pass

class FlightDataDB:
    def __init__(self, db_dir: str = "flight_data"):
        try:
            self.db_dir = Path(db_dir)
            self.connections: Dict[str, duckdb.DuckDBPyConnection] = {}
            self.message_tables: Dict[str, set] = {}
            # Create directory if it doesn't exist
            self.db_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Initialized FlightDataDB with directory: {self.db_dir}")
        except Exception as e:
            logger.error(f"Failed to initialize FlightDataDB: {str(e)}")
            raise FlightDataDBError(f"Failed to initialize database: {str(e)}")

    def _get_connection(self, session_id: str) -> duckdb.DuckDBPyConnection:
        if not session_id or not isinstance(session_id, str):
            raise DataValidationError("Invalid session_id: must be a non-empty string")
        
        try:
            if session_id not in self.connections:
                logger.debug(f"Creating new connection for session {session_id}")
                db_path = self.db_dir / f"{session_id}.db"
                logger.debug(f"Database path: {db_path}")
                
                try:
                    self.connections[session_id] = duckdb.connect(str(db_path))
                    self.message_tables[session_id] = set()
                except duckdb.Error as e:
                    raise DatabaseConnectionError(f"Failed to create database connection: {str(e)}")
                
            return self.connections[session_id]
        except Exception as e:
            logger.error(f"Error getting connection for session {session_id}: {str(e)}")
            raise DatabaseConnectionError(f"Failed to get database connection: {str(e)}")

    def _infer_duckdb_type(self, sample: Any) -> str:
        """
        Infers the DuckDB type for a given sample value.

        Args:
            sample (Any): The sample value to infer the type of.

        Returns:
            str: The DuckDB type for the sample value.
        """
        try:
            if isinstance(sample, int):
                return "BIGINT"
            elif isinstance(sample, float):
                return "DOUBLE"
            elif isinstance(sample, str):
                return "VARCHAR"
            elif isinstance(sample, bool):
                return "BOOLEAN"
            elif isinstance(sample, list):
                # Special handling for time_unix_usec which comes as a list of arrays
                if len(sample) > 0 and isinstance(sample[0], list) and len(sample[0]) > 0:
                    # If it's a list of arrays, use the first element of the first array
                    return "BIGINT"
                # Convert other lists to JSON strings for storage
                return "VARCHAR"
            else:
                logger.warning(f"Unknown type for sample value: {type(sample)}, defaulting to VARCHAR")
                return "VARCHAR"
        except Exception as e:
            logger.error(f"Error inferring DuckDB type: {str(e)}")
            raise DataValidationError(f"Failed to infer data type: {str(e)}")

    def _create_table_for_message(self, session_id: str, msg_name: str, fields: List[str], sample_row: Dict[str, Any]) -> None:
        """
        Creates a table for a given message in the database.

        Args:
            session_id (str): The session ID to create the table for.
            msg_name (str): The name of the message to create the table for.
            fields (List[str]): The fields to create the table for.
            sample_row (Dict[str, Any]): The sample row to use to infer the types of the fields.

        """

        if not all([session_id, msg_name, fields, sample_row]):
            raise DataValidationError("Missing required parameters for table creation")
        
        try:
            logger.debug(f"Creating table for message: {msg_name}")
            logger.debug(f"Session ID: {session_id}")
            logger.debug(f"Fields to create: {fields}")
            # logger.debug(f"Sample row: {sample_row}")
            
            conn = self._get_connection(session_id)
            columns = []
            
            for field in fields:
                if field not in sample_row:
                    raise DataValidationError(f"Field '{field}' not found in sample row")
                
                duckdb_type = self._infer_duckdb_type(sample_row[field])
                if field.lower() in ("timeus", "time_boot_ms", "timestamp"):
                    duckdb_type = "BIGINT"
                # logger.debug(f"Field '{field}' inferred as type: {duckdb_type}")
                columns.append(f'"{field}" {duckdb_type}')
            
            sql = f'CREATE TABLE IF NOT EXISTS "{msg_name}" ({", ".join(columns)})'
            
            try:
                conn.execute(sql)
                self.message_tables[session_id].add(msg_name)
                logger.debug(f"Successfully created table '{msg_name}'")
            except duckdb.Error as e:
                raise DatabaseConnectionError(f"Failed to create table: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error creating table for message {msg_name}: {str(e)}")
            raise FlightDataDBError(f"Failed to create table: {str(e)}")

    def _get_message_description(self, msg_name: str) -> Optional[str]:
        """
        Gets the description of a given message from the knowledge base.

        Args:
            msg_name (str): The name of the message to get the description of.
        """
        if not msg_name or not isinstance(msg_name, str):
            raise DataValidationError("Invalid msg_name: must be a non-empty string")
        
        try:
            # Read the knowledge base file
            knowledge_base_path = os.path.join(os.path.dirname(__file__), '..', 'knowledge_base', 'knowledge_base.txt')
            
            with open(knowledge_base_path, 'r') as f:
                content = f.read()
                
            # Find the section for this message'
            if f'### {msg_name}' not in content:
                logger.warning(f"No description found for message {msg_name}")
                return ""
            
            msg_section = content.split(f'### {msg_name} ')[1].split('###')[0]
            return msg_section
            
        except FileNotFoundError:
            logger.warning(f"Knowledge base file not found at {knowledge_base_path}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting message description for {msg_name}: {str(e)}")
            raise FlightDataDBError(f"Failed to get message description: {str(e)}")

    def store_flight_data(self, session_id: str, parsed_json: Dict[str, Dict[str, List[Any]]], start_time: Optional[datetime] = None) -> None:
        """
        Stores flight data in the database.

        Args:
            session_id (str): The session ID to store the flight data for.
            parsed_json (Dict[str, Dict[str, List[Any]]]): The parsed JSON data to store.
            start_time (Optional[datetime]): The start time of the flight data.
        """
        if not session_id or not isinstance(session_id, str):
            raise DataValidationError("Invalid session_id: must be a non-empty string")
        if not parsed_json or not isinstance(parsed_json, dict):
            raise DataValidationError("Invalid parsed_json: must be a non-empty dictionary")
        
        try:
            conn = self._get_connection(session_id)
            logger.info(f"Storing flight data for session {session_id}")
            logger.debug(f"Parsed JSON keys: {parsed_json.keys()}")

            for msg_name, msg_data in parsed_json.items():
                if not msg_data or not isinstance(msg_data, dict):
                    raise DataValidationError(f"Invalid message data format for {msg_name}: must be a non-empty dictionary")
                
                fields = list(msg_data.keys())
                if not fields:
                    raise DataValidationError(f"No fields found for message {msg_name}")

                try:
                    num_rows = max([len(msg_data[field]) for field in fields])
                    if num_rows == 0:
                        logger.warning(f"No data rows found for message {msg_name}")
                        continue

                    rows = []
                    for i in range(num_rows):
                        try:
                            row = {}
                            for field in fields:
                                if i < len(msg_data[field]):
                                    value = msg_data[field][i]
                                    # Validate value type
                                    if value is not None and not isinstance(value, (int, float, str, bool, list)):
                                        raise DataValidationError(
                                            f"Invalid data type for field '{field}' in message {msg_name}: {type(value)}"
                                        )
                                    
                                    # Convert lists to JSON strings
                                    if isinstance(value, list):
                                        # Special handling for time_unix_usec which comes as a list of arrays
                                        if field == "time_unix_usec" and len(value) > 0 and isinstance(value[0], list):
                                            if not value[0] or not isinstance(value[0][0], (int, float)):
                                                raise DataValidationError(
                                                    f"Invalid time_unix_usec format in message {msg_name}: expected list of numeric arrays"
                                                )
                                            value = value[0][0]  # Take the first element of the first array
                                        else:
                                            try:
                                                value = json.dumps(value)
                                            except (TypeError, ValueError) as e:
                                                raise DataValidationError(
                                                    f"Failed to serialize list data for field '{field}' in message {msg_name}: {str(e)}"
                                                )
                                    row[field] = value
                            rows.append(row)
                        except IndexError as e:
                            raise DataValidationError(
                                f"Data inconsistency in message {msg_name} at row {i}: {str(e)}"
                            )

                    if msg_name not in self.message_tables[session_id]:
                        try:
                            sample_row = rows[0]
                            self._create_table_for_message(session_id, msg_name, fields, sample_row)
                        except Exception as e:
                            raise DatabaseConnectionError(
                                f"Failed to create table for message {msg_name}: {str(e)}"
                            )

                    insert_fields = fields
                    placeholders = ", ".join(["?"] * len(insert_fields))
                    sql = f'INSERT INTO "{msg_name}" ({", ".join(insert_fields)}) VALUES ({placeholders})'
                    
                    for row in rows:
                        try:
                            values = [row.get(f) for f in fields]
                            conn.execute(sql, values)
                        except duckdb.Error as e:
                            logger.error(f"Failed to insert row into {msg_name}: {str(e)}")
                            raise DatabaseConnectionError(f"Failed to insert data: {str(e)}")

                    logger.debug(f"Successfully inserted rows into '{msg_name}'")
                except Exception as e:
                    logger.error(f"Error processing message {msg_name}: {str(e)}")
                    raise FlightDataDBError(f"Failed to process message {msg_name}: {str(e)}")

            logger.info(f"Successfully stored flight data for session {session_id}")
        except Exception as e:
            logger.error(f"Error storing flight data: {str(e)}")
            raise FlightDataDBError(f"Failed to store flight data: {str(e)}")

    def query(self, session_id: str, sql: str) -> pd.DataFrame:
        """
        Executes a SQL query on the database.

        Args:
            session_id (str): The session ID to execute the query on.
            sql (str): The SQL query to execute.

        Returns:
            pd.DataFrame: The result of the query.
        """
        if not session_id or not isinstance(session_id, str):
            raise DataValidationError("Invalid session_id: must be a non-empty string")
        if not sql or not isinstance(sql, str):
            raise DataValidationError("Invalid SQL query: must be a non-empty string")
        
        try:
            conn = self._get_connection(session_id)
            return conn.execute(sql).fetchdf()
        except duckdb.Error as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise DatabaseConnectionError(f"Failed to execute query: {str(e)}")
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            raise FlightDataDBError(f"Query execution failed: {str(e)}")

    def get_database_information(self, session_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Gets the database information for a given session.

        Args:
            session_id (str): The session ID to get the database information for.
        """
        if not session_id or not isinstance(session_id, str):
            raise DataValidationError("Invalid session_id: must be a non-empty string")
        
        try:
            tables = self.message_tables[session_id]
            queries = [f"PRAGMA table_info('{table_name}')" for table_name in tables]
            results = {table_name: {"description": self._get_message_description(table_name), "schema": self.query(session_id, query)} for table_name, query in zip(tables, queries)}
            return results
        except Exception as e:
            logger.error(f"Error getting database information: {str(e)}")
            raise FlightDataDBError(f"Failed to get database information: {str(e)}")

    def close(self):
        """Close all database connections"""
        try:
            for session_id, conn in self.connections.items():
                try:
                    conn.close()
                    logger.debug(f"Closed connection for session {session_id}")
                except Exception as e:
                    logger.error(f"Error closing connection for session {session_id}: {str(e)}")
            self.connections.clear()
            self.message_tables.clear()
            logger.info("All database connections closed")
        except Exception as e:
            logger.error(f"Error during database cleanup: {str(e)}")
            raise FlightDataDBError(f"Failed to close database connections: {str(e)}")
