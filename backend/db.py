"""
Database connection helpers for SQLite and DuckDB.
"""

import os
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from uuid import UUID

import aiosqlite
import duckdb
from duckdb import DuckDBPyConnection
import asyncio
import json

from schemas import ParseStatus, LogFileType, FlightMetrics

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration."""

    def __init__(self):
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)

        self.uploads_dir = Path("uploads")
        self.uploads_dir.mkdir(exist_ok=True)

        self.sqlite_path = self.data_dir / "sessions.sqlite"
        self.duckdb_path = self.data_dir / "telemetry.duckdb"


class SQLiteManager:
    """SQLite database manager for session metadata."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_tables()

    def _init_tables(self):
        """Initialize SQLite tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS flight_sessions (
                        session_id TEXT PRIMARY KEY,
                        filename TEXT NOT NULL,
                        file_size INTEGER NOT NULL,
                        log_type TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'processing',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        processed_at TIMESTAMP NULL,
                        error_message TEXT NULL,
                        
                        -- Flight metadata
                        flight_duration_seconds REAL NULL,
                        start_time TIMESTAMP NULL,
                        end_time TIMESTAMP NULL,
                        message_count INTEGER NULL,
                        available_message_types TEXT NULL, -- JSON array as string
                        
                        -- Basic metrics
                        max_altitude REAL NULL,
                        min_altitude REAL NULL,
                        max_speed REAL NULL,
                        max_battery_voltage REAL NULL,
                        min_battery_voltage REAL NULL,
                        gps_fix_count INTEGER NULL,
                        total_distance REAL NULL,
                        
                        -- Vehicle and flight specific data
                        vehicle_type TEXT NULL,
                        flight_modes_used TEXT NULL, -- JSON array as string
                        total_distance_km REAL NULL,
                        max_altitude_m REAL NULL,
                        min_altitude_m REAL NULL,
                        max_speed_ms REAL NULL,
                        gps_fix_type_max INTEGER NULL,
                        error_count INTEGER NULL,
                        warning_count INTEGER NULL,
                        autopilot_version TEXT NULL
                    );
                    
                    CREATE TABLE IF NOT EXISTS chat_conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        message_type TEXT NOT NULL, -- 'user' or 'assistant'
                        message TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT NULL, -- JSON as string
                        response_id TEXT NULL, -- OpenAI response ID for assistant messages
                        
                        FOREIGN KEY (session_id) REFERENCES flight_sessions (session_id)
                    );
                    
                    CREATE TABLE IF NOT EXISTS detected_anomalies (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        anomaly_type TEXT NOT NULL,
                        severity TEXT NOT NULL DEFAULT 'info', -- info, warning, error
                        message TEXT NOT NULL,
                        start_time REAL NULL, -- time_boot_ms
                        end_time REAL NULL, -- time_boot_ms
                        context TEXT NULL, -- JSON as string
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        
                        FOREIGN KEY (session_id) REFERENCES flight_sessions (session_id)
                    );
                    
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NULL, -- NULL for global preferences
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    -- Indexes for performance
                    CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_conversations(session_id);
                    CREATE INDEX IF NOT EXISTS idx_chat_conversation ON chat_conversations(conversation_id);
                    CREATE INDEX IF NOT EXISTS idx_anomalies_session ON detected_anomalies(session_id);
                    CREATE INDEX IF NOT EXISTS idx_anomalies_time ON detected_anomalies(start_time, end_time);
                    CREATE INDEX IF NOT EXISTS idx_chat_conversation_timestamp ON chat_conversations(conversation_id, timestamp);
                    CREATE INDEX IF NOT EXISTS idx_chat_last_resp ON chat_conversations(conversation_id, response_id);
                """
                )

                # Run migrations after table creation
                self._run_migrations(conn)

            logger.info(f"SQLite database initialized at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize SQLite database: {e}")
            raise

    def _run_migrations(self, conn: sqlite3.Connection):
        """Run database migrations for schema updates."""
        try:
            # Check if response_id column exists in chat_conversations
            cursor = conn.execute("PRAGMA table_info(chat_conversations)")
            columns = [row[1] for row in cursor.fetchall()]

            if "response_id" not in columns:
                logger.info("Adding response_id column to chat_conversations table")
                conn.execute(
                    "ALTER TABLE chat_conversations ADD COLUMN response_id TEXT NULL"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_chat_last_resp ON chat_conversations(conversation_id, response_id)"
                )
                conn.commit()
                logger.info("Migration completed: response_id column added")
        except sqlite3.Error as e:
            logger.error(f"Migration failed: {e}")
            raise

    async def create_session(
        self, session_id: UUID, filename: str, file_size: int, log_type: LogFileType
    ) -> None:
        """Create a new flight session record."""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """
                    INSERT INTO flight_sessions 
                    (session_id, filename, file_size, log_type, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(session_id),
                        filename,
                        file_size,
                        log_type.value,
                        ParseStatus.PROCESSING.value,
                        datetime.utcnow(),
                    ),
                )
                await conn.commit()
            logger.info(f"Created session record for {session_id}")
        except aiosqlite.Error as e:
            logger.error(f"Failed to create session {session_id}: {e}")
            raise

    async def get_session(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        """Get session information."""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute(
                    "SELECT * FROM flight_sessions WHERE session_id = ?",
                    (str(session_id),),
                ) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        return None

                    # Convert row to dict and parse JSON fields
                    session_data = dict(row)

                    # Parse JSON string fields back to Python objects
                    if session_data.get("available_message_types"):
                        try:
                            session_data["available_message_types"] = json.loads(
                                session_data["available_message_types"]
                            )
                        except (json.JSONDecodeError, TypeError):
                            logger.warning(
                                f"Failed to parse available_message_types for session {session_id}"
                            )
                            session_data["available_message_types"] = []

                    if session_data.get("flight_modes_used"):
                        try:
                            session_data["flight_modes_used"] = json.loads(
                                session_data["flight_modes_used"]
                            )
                        except (json.JSONDecodeError, TypeError):
                            logger.warning(
                                f"Failed to parse flight_modes_used for session {session_id}"
                            )
                            session_data["flight_modes_used"] = []

                    return session_data
        except aiosqlite.Error as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    async def store_conversation(
        self,
        *,
        conversation_id: UUID,
        session_id: UUID,
        message_type: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        response_id: Optional[str] = None,
    ) -> None:
        """Persist a single conversation message.

        Parameters
        ----------
        conversation_id: UUID
            The logical conversation identifier (stays constant across turns).
        session_id: UUID
            The flight-log session this conversation refers to.
        message_type: str
            Either ``"user"`` or ``"assistant"``. No other values allowed.
        message: str
            The raw text content.
        metadata: Optional[dict]
            Arbitrary JSON-serialisable payload (token counts, model name, etc.).
        response_id: Optional[str]
            OpenAI response ID for assistant messages (None for user messages).
        """
        if message_type not in {"user", "assistant"}:
            raise ValueError("message_type must be 'user' or 'assistant'")

        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """
                    INSERT INTO chat_conversations (
                        conversation_id,
                        session_id,
                        message_type,
                        message,
                        metadata,
                        timestamp,
                        response_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(conversation_id),
                        str(session_id),
                        message_type,
                        message,
                        json.dumps(metadata) if metadata is not None else None,
                        datetime.utcnow(),
                        response_id,
                    ),
                )
                await conn.commit()
        except aiosqlite.Error as e:
            logger.error(
                "Failed to store conversation message %s (conv=%s sess=%s): %s",
                message_type,
                conversation_id,
                session_id,
                e,
            )
            raise RuntimeError(f"Database error storing conversation: {e}") from e

    async def get_conversation(
        self, conversation_id: UUID, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve messages for a conversation ordered by timestamp ascending."""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                query = "SELECT * FROM chat_conversations WHERE conversation_id = ? ORDER BY timestamp ASC"
                if limit is not None:
                    query += " LIMIT ?"
                    params = (str(conversation_id), limit)
                else:
                    params = (str(conversation_id),)
                cursor = await conn.execute(query, params)
                rows = await cursor.fetchall()
                # Convert to list[dict] and parse JSON metadata
                messages: List[Dict[str, Any]] = []
                for row in rows:
                    record = dict(row)
                    if record.get("metadata"):
                        try:
                            record["metadata"] = json.loads(record["metadata"])
                        except (json.JSONDecodeError, TypeError):
                            record["metadata"] = None
                    messages.append(record)
                return messages
        except aiosqlite.Error as e:
            logger.error(
                "Failed to fetch conversation %s (limit=%s): %s",
                conversation_id,
                limit,
                e,
            )
            raise RuntimeError(f"Database error fetching conversation: {e}") from e

    async def get_last_assistant_response_id(
        self, conversation_id: UUID
    ) -> Optional[str]:
        """Get the response_id of the most recent assistant message in a conversation.

        Parameters
        ----------
        conversation_id: UUID
            The conversation to search in.

        Returns
        -------
        Optional[str]
            The response_id of the last assistant message, or None if no assistant
            messages exist or the last assistant message has no response_id.
        """
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    """
                    SELECT response_id FROM chat_conversations 
                    WHERE conversation_id = ? AND message_type = 'assistant' AND response_id IS NOT NULL
                    ORDER BY timestamp DESC 
                    LIMIT 1
                    """,
                    (str(conversation_id),),
                )
                row = await cursor.fetchone()
                return row[0] if row else None
        except aiosqlite.Error as e:
            logger.error(
                "Failed to get last assistant response_id for conversation %s: %s",
                conversation_id,
                e,
            )
            raise RuntimeError(f"Database error getting last response_id: {e}") from e

    async def update_session_status(
        self,
        session_id: UUID,
        status: ParseStatus,
        error_message: Optional[str] = None,
        flight_metrics: Optional[FlightMetrics] = None,
        available_message_types: Optional[List[str]] = None,
        vehicle_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update session status and metadata."""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                params = [status.value]
                query_parts = ["status = ?"]

                if status == ParseStatus.COMPLETED:
                    query_parts.append("processed_at = ?")
                    params.append(datetime.utcnow())

                if error_message:
                    query_parts.append("error_message = ?")
                    params.append(error_message)

                if flight_metrics:
                    metrics_fields = [
                        "max_altitude",
                        "min_altitude",
                        "max_speed",
                        "max_battery_voltage",
                        "min_battery_voltage",
                        "gps_fix_count",
                        "total_distance",
                        "total_distance_km",
                        "max_altitude_m",
                        "min_altitude_m",
                        "max_speed_ms",
                        "gps_fix_type_max",
                        "error_count",
                        "warning_count",
                    ]
                    for field in metrics_fields:
                        value = getattr(flight_metrics, field, None)
                        if value is not None:
                            query_parts.append(f"{field} = ?")
                            params.append(value)

                if available_message_types:
                    query_parts.append("available_message_types = ?")
                    params.append(json.dumps(available_message_types))

                if vehicle_metadata:
                    vehicle_fields = [
                        "vehicle_type",
                        "flight_modes_used",
                        "autopilot_version",
                    ]
                    for field in vehicle_fields:
                        value = vehicle_metadata.get(field)
                        if value is not None:
                            if field == "flight_modes_used" and isinstance(value, list):
                                query_parts.append(f"{field} = ?")
                                params.append(json.dumps(value))
                            else:
                                query_parts.append(f"{field} = ?")
                                params.append(value)

                params.append(str(session_id))

                await conn.execute(
                    f"UPDATE flight_sessions SET {', '.join(query_parts)} WHERE session_id = ?",
                    params,
                )
                await conn.commit()

            logger.info(f"Updated session {session_id} status to {status.value}")
        except aiosqlite.Error as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            raise

    async def list_session_ids(self, limit: Optional[int] = None) -> List[UUID]:
        """Return a list of all session IDs ordered by creation date (newest first).

        Parameters
        ----------
        limit: Optional[int]
            If provided, restrict the maximum number of IDs returned.
        """
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                query = (
                    "SELECT session_id FROM flight_sessions ORDER BY created_at DESC"
                )
                params: tuple = ()
                if limit is not None:
                    query += " LIMIT ?"
                    params = (limit,)
                cursor = await conn.execute(query, params)
                rows = await cursor.fetchall()
                # Convert to UUID objects before returning
                return [UUID(row[0]) for row in rows]
        except aiosqlite.Error as e:
            logger.error("Failed to list session IDs: %s", e)
            raise RuntimeError(f"Database error listing sessions: {e}") from e


class DuckDBManager:
    """DuckDB manager for telemetry data."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: Optional[DuckDBPyConnection] = None
        self._init_connection()

    def _init_connection(self):
        """Initialize DuckDB connection and tables."""
        try:
            self._conn = duckdb.connect(str(self.db_path))
            self._create_tables()
            logger.info(f"DuckDB connection initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize DuckDB: {e}")
            raise

    def _create_tables(self):
        """Create DuckDB tables for telemetry data."""
        if not self._conn:
            raise RuntimeError("DuckDB connection not initialized")

        try:
            # Create telemetry tables (execute each statement individually)
            tables_sql = [
                """
                CREATE TABLE IF NOT EXISTS gps_telemetry (
                    session_id VARCHAR NOT NULL,
                    time_boot_ms BIGINT NOT NULL,
                    timestamp_utc TIMESTAMP,
                    lat DOUBLE,
                    lon DOUBLE,
                    alt DOUBLE,
                    relative_alt DOUBLE,
                    vx DOUBLE,
                    vy DOUBLE,
                    vz DOUBLE,
                    hdg DOUBLE,
                    eph DOUBLE,
                    epv DOUBLE,
                    vel DOUBLE,
                    cog DOUBLE,
                    fix_type INTEGER,
                    satellites_visible INTEGER,
                    dgps_numch INTEGER,
                    dgps_age INTEGER
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS attitude_telemetry (
                    session_id VARCHAR NOT NULL,
                    time_boot_ms BIGINT NOT NULL,
                    timestamp_utc TIMESTAMP,
                    roll DOUBLE,
                    pitch DOUBLE,
                    yaw DOUBLE,
                    rollspeed DOUBLE,
                    pitchspeed DOUBLE,
                    yawspeed DOUBLE
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS sensor_telemetry (
                    session_id VARCHAR NOT NULL,
                    time_boot_ms BIGINT NOT NULL,
                    timestamp_utc TIMESTAMP,
                    xacc DOUBLE,
                    yacc DOUBLE,
                    zacc DOUBLE,
                    xgyro DOUBLE,
                    ygyro DOUBLE,
                    zgyro DOUBLE,
                    xmag DOUBLE,
                    ymag DOUBLE,
                    zmag DOUBLE
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS flight_events (
                    session_id VARCHAR NOT NULL,
                    time_boot_ms BIGINT NOT NULL,
                    timestamp_utc TIMESTAMP,
                    event_type VARCHAR NOT NULL,
                    event_description VARCHAR,
                    severity VARCHAR DEFAULT 'info',
                    parameters VARCHAR
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS system_status (
                    session_id VARCHAR NOT NULL,
                    time_boot_ms BIGINT NOT NULL,
                    timestamp_utc TIMESTAMP,
                    battery_voltage DOUBLE,
                    battery_current DOUBLE,
                    battery_remaining INTEGER,
                    battery_temperature DOUBLE,
                    radio_rssi INTEGER,
                    radio_remrssi INTEGER,
                    radio_noise INTEGER,
                    radio_remnoise INTEGER,
                    mode VARCHAR,
                    armed BOOLEAN
                )
                """,
            ]

            # Execute each table creation statement
            for sql in tables_sql:
                self._conn.execute(sql)

            # Setup ArduPilot documentation search infrastructure
            self._setup_doc_search_tables()

            # Create indexes for performance
            tables = [
                "gps_telemetry",
                "attitude_telemetry",
                "sensor_telemetry",
                "flight_events",
                "system_status",
            ]

            for table in tables:
                self._conn.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{table}_session_time "
                    f"ON {table}(session_id, time_boot_ms)"
                )

            # Additional indexes to speed up UTC-timestamp range filtering
            for table in tables:
                self._conn.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{table}_session_timestamp "
                    f"ON {table}(session_id, timestamp_utc)"
                )

            logger.info("DuckDB tables and indexes created successfully")
        except Exception as e:
            logger.error(f"Failed to create DuckDB tables: {e}")
            raise

    def _setup_doc_search_tables(self):
        """Setup ArduPilot documentation search tables and VSS extension."""
        try:
            # Install and load VSS extension (idempotent operations)
            self._conn.execute("INSTALL vss")
            self._conn.execute("LOAD vss")
            logger.debug("VSS extension loaded for documentation search")

            # Create doc_chunks table for ArduPilot documentation
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS doc_chunks (
                    id INTEGER PRIMARY KEY,
                    content_hash VARCHAR UNIQUE,
                    source VARCHAR NOT NULL,
                    heading VARCHAR,
                    text VARCHAR NOT NULL,
                    embedding FLOAT[384]
                )
                """
            )

            logger.info("ArduPilot documentation search infrastructure initialized")
        except Exception as e:
            # Log warning but don't fail the entire initialization
            # This allows the system to work even if VSS extension is unavailable
            logger.warning(f"Failed to setup documentation search: {e}")
            logger.warning("Documentation search features will be unavailable")

    def get_connection(self) -> DuckDBPyConnection:
        """Get DuckDB connection."""
        if not self._conn:
            raise RuntimeError("DuckDB connection not initialized")
        return self._conn

    def close(self):
        """Close DuckDB connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


# Global database instances
_db_config = DatabaseConfig()
_sqlite_manager = SQLiteManager(_db_config.sqlite_path)
_duckdb_manager = DuckDBManager(_db_config.duckdb_path)


def get_sqlite_manager() -> SQLiteManager:
    """Get SQLite manager instance."""
    return _sqlite_manager


def get_duckdb_manager() -> DuckDBManager:
    """Get DuckDB manager instance."""
    return _duckdb_manager


def get_uploads_dir() -> Path:
    """Get uploads directory path."""
    return _db_config.uploads_dir
