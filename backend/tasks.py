"""
Background tasks for log parsing and processing.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timezone
import json

from db import get_sqlite_manager, get_duckdb_manager
from parsers import create_parser, LogParseError
from schemas import ParseStatus, LogFileType, FlightMetrics
from multiprocess_parser import (
    MultiprocessLogParser,
)  # multiprocessing ingestion

logger = logging.getLogger(__name__)

# Simple in-memory task tracking (for production, use Celery/Redis)
_active_tasks: Dict[UUID, asyncio.Task] = {}

MULTIPROCESSING_ENABLED = False  # Disable multiprocessing, use simple approach


class TaskManager:
    """Simple task manager for background processing."""

    @staticmethod
    async def parse_and_ingest_log(
        session_id: UUID, file_path: Path, log_type: LogFileType
    ) -> None:
        """
        Background task to parse log file and ingest into databases.
        """
        sqlite_manager = get_sqlite_manager()
        duckdb_manager = get_duckdb_manager()

        try:
            logger.info(f"Starting background parsing for session {session_id}")

            # Create parser
            parser = create_parser(session_id, file_path, log_type)

            # Parse the log file (needed for quick metrics & message list)
            parse_metadata = parser.parse()

            # Extract metrics and message types
            metrics = parser.metrics
            available_message_types = parser.available_message_types

            # Decide ingestion path based on multiprocessing flag
            if MULTIPROCESSING_ENABLED and log_type == LogFileType.BIN:
                mp_parser = MultiprocessLogParser()
                message_count, flight_duration, vehicle_metadata = (
                    await mp_parser.parse_log_async(
                        session_id=session_id,
                        file_path=file_path,
                        log_type=log_type,
                        duckdb_manager=duckdb_manager,
                        max_messages=None,
                    )
                )
            else:
                # Process messages once: extract metadata and ingest to DuckDB
                message_count, flight_duration, vehicle_metadata = (
                    await TaskManager._process_and_ingest_messages(
                        session_id, parser, duckdb_manager
                    )
                )

            # Update session status to completed with full metadata
            await sqlite_manager.update_session_status(
                session_id=session_id,
                status=ParseStatus.COMPLETED,
                flight_metrics=metrics,
                available_message_types=available_message_types,
                vehicle_metadata=vehicle_metadata,
            )

            # Update flight duration and message count
            await TaskManager._update_session_counters(
                sqlite_manager, session_id, message_count, flight_duration
            )

            logger.info(f"Successfully completed parsing for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to parse log for session {session_id}: {e}")

            # Update session status to failed
            try:
                await sqlite_manager.update_session_status(
                    session_id=session_id,
                    status=ParseStatus.FAILED,
                    error_message=str(e),
                )
            except Exception as update_error:
                logger.error(f"Failed to update session status: {update_error}")

        finally:
            # Clean up task tracking
            if session_id in _active_tasks:
                del _active_tasks[session_id]

    @staticmethod
    async def _process_and_ingest_messages(
        session_id: UUID, parser, duckdb_manager
    ) -> tuple[int, Optional[float], Dict[str, Any]]:
        """
        Process messages once: extract session metadata and ingest into DuckDB.
        """
        conn = duckdb_manager.get_connection()

        # Batch insert configuration
        BATCH_SIZE = (
            5000  # Process messages in batches (increased for better performance)
        )
        MAX_MESSAGES_DEV = None  # No limit - process all messages
        USE_MULTIPROCESSING = True  # Enable multiprocessing for better performance
        batches = {"gps": [], "attitude": [], "sensor": [], "events": [], "system": []}

        # Session metadata tracking
        message_count = 0
        flight_modes = set()
        vehicle_type = None
        autopilot_version = None
        start_time = None
        end_time = None

        try:
            # Process messages in single pass for both metadata extraction and DuckDB ingestion
            for message in parser.get_messages():
                message_count += 1

                # Development mode: limit message processing for testing
                if MAX_MESSAGES_DEV is not None and message_count > MAX_MESSAGES_DEV:
                    logger.info(
                        f"Development mode: stopping at {MAX_MESSAGES_DEV} messages"
                    )
                    break

                # Progress logging
                if message_count % 5000 == 0:
                    logger.info(
                        f"Processing progress: {message_count:,} messages processed"
                    )

                # Track timing for flight duration
                time_boot_ms = message.get("time_boot_ms")
                if time_boot_ms is not None:
                    if start_time is None or time_boot_ms < start_time:
                        start_time = time_boot_ms
                    if end_time is None or time_boot_ms > end_time:
                        end_time = time_boot_ms

                # Extract vehicle metadata
                msg_type = message.get("_type", "").upper()

                if msg_type == "HEARTBEAT":
                    custom_mode = message.get("custom_mode")
                    if custom_mode is not None:
                        flight_modes.add(custom_mode)

                    # Extract vehicle type from heartbeat
                    if vehicle_type is None:
                        vehicle_type = message.get("type", "Unknown")

                elif msg_type == "AUTOPILOT_VERSION":
                    # Extract autopilot version if available
                    autopilot_version = message.get("flight_sw_version", "Unknown")

                # Route message to appropriate batch for DuckDB insertion
                # MAVLink messages (from .tlog files)
                if msg_type in ["GLOBAL_POSITION_INT", "GPS_RAW_INT", "GPS2_RAW"]:
                    batches["gps"].append(
                        TaskManager._prepare_gps_record(session_id, message)
                    )
                elif msg_type in ["ATTITUDE", "AHRS", "AHRS2"]:
                    batches["attitude"].append(
                        TaskManager._prepare_attitude_record(session_id, message)
                    )
                elif msg_type in ["RAW_IMU", "SCALED_IMU", "SCALED_IMU2"]:
                    batches["sensor"].append(
                        TaskManager._prepare_sensor_record(session_id, message)
                    )
                elif msg_type in ["STATUSTEXT", "HEARTBEAT"]:
                    batches["events"].append(
                        TaskManager._prepare_event_record(session_id, message)
                    )
                elif msg_type in ["SYS_STATUS", "BATTERY_STATUS", "RADIO_STATUS"]:
                    batches["system"].append(
                        TaskManager._prepare_system_record(session_id, message)
                    )
                # Dataflash messages (from .bin files)
                elif msg_type in ["GPS", "POS"]:  # GPS coordinates from dataflash
                    batches["gps"].append(
                        TaskManager._prepare_dataflash_gps_record(session_id, message)
                    )
                elif msg_type == "ATT":  # Attitude data from dataflash
                    batches["attitude"].append(
                        TaskManager._prepare_dataflash_attitude_record(
                            session_id, message
                        )
                    )
                elif msg_type == "IMU":  # IMU data from dataflash
                    batches["sensor"].append(
                        TaskManager._prepare_dataflash_sensor_record(
                            session_id, message
                        )
                    )
                elif msg_type in ["MSG", "MODE"]:  # Events from dataflash
                    batches["events"].append(
                        TaskManager._prepare_dataflash_event_record(session_id, message)
                    )
                elif msg_type == "BAT":  # Battery data from dataflash
                    batches["system"].append(
                        TaskManager._prepare_dataflash_system_record(
                            session_id, message
                        )
                    )

                # Flush batches when they reach the batch size
                if message_count % BATCH_SIZE == 0:
                    await TaskManager._flush_batches(conn, batches)

            # Flush remaining messages
            await TaskManager._flush_batches(conn, batches)

            # Calculate flight duration
            flight_duration = None
            if start_time is not None and end_time is not None:
                flight_duration = (end_time - start_time) / 1000.0  # Convert to seconds

            # Build vehicle metadata dictionary
            vehicle_metadata = {
                "vehicle_type": vehicle_type,
                "flight_modes_used": list(flight_modes) if flight_modes else [],
                "autopilot_version": autopilot_version,
            }

            logger.info(
                f"Processed and ingested {message_count} messages for session {session_id}"
            )

        except Exception as e:
            logger.error(f"Failed to process and ingest messages: {e}")
            flight_duration = None
            vehicle_metadata = {}
            raise

        return message_count, flight_duration, vehicle_metadata

    @staticmethod
    async def _update_session_counters(
        sqlite_manager,
        session_id: UUID,
        message_count: int,
        flight_duration: Optional[float],
    ) -> None:
        """Update session with message count and flight duration."""
        try:
            import aiosqlite

            async with aiosqlite.connect(sqlite_manager.db_path) as conn:
                query_parts = ["message_count = ?"]
                params = [message_count]

                if flight_duration is not None:
                    query_parts.append("flight_duration_seconds = ?")
                    params.append(flight_duration)

                params.append(str(session_id))

                await conn.execute(
                    f"UPDATE flight_sessions SET {', '.join(query_parts)} WHERE session_id = ?",
                    params,
                )
                await conn.commit()

            logger.info(
                f"Updated session {session_id} with {message_count} messages and {flight_duration}s duration"
            )

        except Exception as e:
            logger.error(f"Failed to update session counters: {e}")

    @staticmethod
    async def _flush_batches(conn, batches: Dict[str, list]) -> None:
        """Flush message batches to DuckDB."""
        for batch_type, records in batches.items():
            if not records:
                continue

            try:
                if batch_type == "gps":
                    conn.executemany(
                        """
                        INSERT INTO gps_telemetry 
                        (session_id, time_boot_ms, timestamp_utc, lat, lon, alt, relative_alt, 
                         vx, vy, vz, hdg, eph, epv, vel, cog, fix_type, satellites_visible, 
                         dgps_numch, dgps_age) VALUES 
                        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        records,
                    )
                elif batch_type == "attitude":
                    conn.executemany(
                        """
                        INSERT INTO attitude_telemetry 
                        (session_id, time_boot_ms, timestamp_utc, roll, pitch, yaw, 
                         rollspeed, pitchspeed, yawspeed) VALUES 
                        (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        records,
                    )
                elif batch_type == "sensor":
                    conn.executemany(
                        """
                        INSERT INTO sensor_telemetry 
                        (session_id, time_boot_ms, timestamp_utc, xacc, yacc, zacc, 
                         xgyro, ygyro, zgyro, xmag, ymag, zmag) VALUES 
                        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        records,
                    )
                elif batch_type == "events":
                    conn.executemany(
                        """
                        INSERT INTO flight_events 
                        (session_id, time_boot_ms, timestamp_utc, event_type, 
                         event_description, severity, parameters) VALUES 
                        (?, ?, ?, ?, ?, ?, ?)
                        """,
                        records,
                    )
                elif batch_type == "system":
                    conn.executemany(
                        """
                        INSERT INTO system_status 
                        (session_id, time_boot_ms, timestamp_utc, battery_voltage, 
                         battery_current, battery_remaining, battery_temperature, 
                         radio_rssi, radio_remrssi, radio_noise, radio_remnoise, 
                         mode, armed) VALUES 
                        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        records,
                    )

                # Clear the batch
                records.clear()

            except Exception as e:
                logger.error(f"Failed to flush {batch_type} batch: {e}")
                # Clear the batch even on error to prevent memory buildup
                records.clear()
                raise

    @staticmethod
    def _prepare_gps_record(session_id: UUID, message: Dict[str, Any]) -> tuple:
        """Prepare GPS message for DuckDB insertion."""
        return (
            str(session_id),
            message.get("time_boot_ms", 0),
            message.get("timestamp_utc"),
            (
                message.get("lat", 0) / 1e7 if message.get("lat") else None
            ),  # Convert to degrees
            (
                message.get("lon", 0) / 1e7 if message.get("lon") else None
            ),  # Convert to degrees
            (
                message.get("alt", 0) / 1000.0 if message.get("alt") else None
            ),  # Convert to meters
            (
                message.get("relative_alt", 0) / 1000.0
                if message.get("relative_alt")
                else None
            ),
            message.get("vx"),
            message.get("vy"),
            message.get("vz"),
            message.get("hdg"),
            message.get("eph"),
            message.get("epv"),
            message.get("vel"),
            message.get("cog"),
            message.get("fix_type"),
            message.get("satellites_visible"),
            message.get("dgps_numch"),
            message.get("dgps_age"),
        )

    @staticmethod
    def _prepare_attitude_record(session_id: UUID, message: Dict[str, Any]) -> tuple:
        """Prepare attitude message for DuckDB insertion."""
        return (
            str(session_id),
            message.get("time_boot_ms", 0),
            message.get("timestamp_utc"),
            message.get("roll"),
            message.get("pitch"),
            message.get("yaw"),
            message.get("rollspeed"),
            message.get("pitchspeed"),
            message.get("yawspeed"),
        )

    @staticmethod
    def _prepare_sensor_record(session_id: UUID, message: Dict[str, Any]) -> tuple:
        """Prepare sensor message for DuckDB insertion."""
        return (
            str(session_id),
            message.get("time_boot_ms", 0),
            message.get("timestamp_utc"),
            message.get("xacc"),
            message.get("yacc"),
            message.get("zacc"),
            message.get("xgyro"),
            message.get("ygyro"),
            message.get("zgyro"),
            message.get("xmag"),
            message.get("ymag"),
            message.get("zmag"),
        )

    @staticmethod
    def _prepare_event_record(session_id: UUID, message: Dict[str, Any]) -> tuple:
        """Prepare event message for DuckDB insertion."""
        msg_type = message.get("_type", "UNKNOWN")
        description = None
        severity = "info"

        if msg_type == "STATUSTEXT":
            description = message.get("text", "")
            severity_level = message.get("severity", 6)  # MAV_SEVERITY_INFO = 6
            if severity_level <= 3:  # MAV_SEVERITY_ERROR = 3
                severity = "error"
            elif severity_level <= 4:  # MAV_SEVERITY_WARNING = 4
                severity = "warning"
        elif msg_type == "HEARTBEAT":
            description = f"Mode: {message.get('custom_mode', 'Unknown')}"

        return (
            str(session_id),
            message.get("time_boot_ms", 0),
            message.get("timestamp_utc"),
            msg_type,
            description,
            severity,
            None,  # parameters (JSON)
        )

    @staticmethod
    def _prepare_system_record(session_id: UUID, message: Dict[str, Any]) -> tuple:
        """Prepare system status message for DuckDB insertion."""
        return (
            str(session_id),
            message.get("time_boot_ms", 0),
            message.get("timestamp_utc"),
            (
                message.get("voltage_battery", 0) / 1000.0
                if message.get("voltage_battery")
                else None
            ),  # Convert to V
            (
                message.get("current_battery", -1) / 100.0
                if message.get("current_battery", -1) >= 0
                else None
            ),  # Convert to A
            message.get("battery_remaining"),
            None,  # battery_temperature (not in SYS_STATUS)
            message.get("rssi"),
            message.get("remrssi"),
            message.get("noise"),
            message.get("remnoise"),
            message.get("mode"),
            message.get("base_mode", 0) & 128 != 0,  # MAV_MODE_FLAG_SAFETY_ARMED
        )

    @staticmethod
    def _prepare_dataflash_attitude_record(
        session_id: UUID, message: Dict[str, Any]
    ) -> tuple:
        """Prepare dataflash ATT message for DuckDB insertion."""
        return (
            str(session_id),
            message.get("time_boot_ms", 0),
            message.get("timestamp_utc"),
            message.get("Roll"),  # Already in radians
            message.get("Pitch"),
            message.get("Yaw"),
            None,  # rollspeed not in ATT message
            None,  # pitchspeed not in ATT message
            None,  # yawspeed not in ATT message
        )

    @staticmethod
    def _prepare_dataflash_sensor_record(
        session_id: UUID, message: Dict[str, Any]
    ) -> tuple:
        """Prepare dataflash IMU message for DuckDB insertion."""
        return (
            str(session_id),
            message.get("time_boot_ms", 0),
            message.get("timestamp_utc"),
            message.get("AccX"),  # Accelerometer data
            message.get("AccY"),
            message.get("AccZ"),
            message.get("GyrX"),  # Gyroscope data
            message.get("GyrY"),
            message.get("GyrZ"),
            None,  # Magnetometer not in IMU message
            None,
            None,
        )

    @staticmethod
    def _prepare_dataflash_event_record(
        session_id: UUID, message: Dict[str, Any]
    ) -> tuple:
        """Prepare dataflash event message for DuckDB insertion."""
        msg_type = message.get("_type", "UNKNOWN")
        description = None
        severity = "info"

        if msg_type == "MSG":
            description = message.get("Message", "")
        elif msg_type == "MODE":
            description = f"Mode changed to {message.get('Mode', 'Unknown')}"

        return (
            str(session_id),
            message.get("time_boot_ms", 0),
            message.get("timestamp_utc"),
            msg_type,
            description,
            severity,
            None,  # parameters (JSON)
        )

    @staticmethod
    def _prepare_dataflash_system_record(
        session_id: UUID, message: Dict[str, Any]
    ) -> tuple:
        """Prepare dataflash system status message for DuckDB insertion."""
        return (
            str(session_id),
            message.get("time_boot_ms", 0),
            message.get("timestamp_utc"),
            message.get("Volt"),  # Battery voltage
            message.get("Curr"),  # Battery current
            message.get("RemPct"),  # Battery remaining percentage
            message.get("Temp"),  # Battery temperature
            None,  # radio_rssi not in BAT message
            None,  # radio_remrssi
            None,  # radio_noise
            None,  # radio_remnoise
            None,  # mode
            None,  # armed status
        )

    @staticmethod
    def _prepare_dataflash_gps_record(
        session_id: UUID, message: Dict[str, Any]
    ) -> tuple:
        """Prepare GPS record from dataflash GPS/POS messages."""
        # Dataflash GPS/POS messages have simple field names
        lat = message.get("Lat")
        lng = message.get("Lng") or message.get("Lon")  # POS uses Lon, GPS uses Lng
        alt = message.get("Alt")
        status = message.get("Status", 0)  # GPS fix status
        spd = message.get("Spd", 0)  # Speed
        hdg = message.get("GCrs") or message.get("Hdg", 0)  # Course/Heading

        return (
            str(session_id),
            message.get("time_boot_ms", 0),
            message.get("timestamp_utc"),
            lat,  # Latitude
            lng,  # Longitude
            alt,  # Altitude
            None,  # relative_alt
            None,  # velocity_north
            None,  # velocity_east
            None,  # velocity_down
            hdg,  # heading/course
            None,  # eph (accuracy)
            None,  # epv (accuracy)
            spd,  # ground speed
            None,  # cog
            status,  # fix_type (GPS status)
            None,  # satellites_visible
            None,  # dgps_numch
            None,  # dgps_age
        )


async def start_parse_task(
    session_id: UUID, file_path: Path, log_type: LogFileType
) -> None:
    """Start a background parsing task."""
    if session_id in _active_tasks:
        logger.warning(f"Task for session {session_id} already running")
        return

    task = asyncio.create_task(
        TaskManager.parse_and_ingest_log(session_id, file_path, log_type)
    )
    _active_tasks[session_id] = task

    logger.info(f"Started background parsing task for session {session_id}")


def is_task_running(session_id: UUID) -> bool:
    """Check if a parsing task is currently running."""
    return session_id in _active_tasks and not _active_tasks[session_id].done()


async def get_task_status(session_id: UUID) -> Optional[str]:
    """Get the status of a parsing task."""
    if session_id not in _active_tasks:
        return None

    task = _active_tasks[session_id]
    if task.done():
        if task.exception():
            return f"failed: {task.exception()}"
        else:
            return "completed"
    else:
        return "running"
