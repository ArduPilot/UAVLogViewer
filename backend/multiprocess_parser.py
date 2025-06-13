#!/usr/bin/env python3
"""
Multiprocessing-based log parser for improved performance.
"""

import asyncio
import logging
import multiprocessing as mp
import queue
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from uuid import UUID

from parsers import create_parser, LogFileType

logger = logging.getLogger(__name__)


class MultiprocessLogParser:
    """High-performance multiprocessing log parser."""

    def __init__(self, num_workers: int = None):
        self.num_workers = num_workers or min(
            mp.cpu_count(), 4
        )  # Limit to 4 workers max
        self.message_queue = None
        self.result_queue = None
        self.workers = []

    async def parse_log_async(
        self,
        session_id: UUID,
        file_path: Path,
        log_type: LogFileType,
        duckdb_manager: Any,
        max_messages: Optional[int] = None,
    ) -> Tuple[int, Optional[float], Dict[str, Any]]:
        """Parse log file using multiprocessing."""

        logger.info(f"Starting multiprocess parsing with {self.num_workers} workers")

        # Run in thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._parse_log_sync,
            session_id,
            file_path,
            log_type,
            duckdb_manager,
            max_messages,
        )

    def _parse_log_sync(
        self,
        session_id: UUID,
        file_path: Path,
        log_type: LogFileType,
        duckdb_manager: Any,
        max_messages: Optional[int] = None,
    ) -> Tuple[int, Optional[float], Dict[str, Any]]:
        """Synchronous multiprocess parsing implementation."""

        # Create multiprocessing queues (increased sizes for better throughput)
        self.message_queue = mp.Queue(maxsize=20000)  # Buffer for messages
        self.result_queue = mp.Queue(maxsize=5000)  # Buffer for processed results

        # Create and start worker processes
        self.workers = []
        for i in range(self.num_workers):
            worker = mp.Process(
                target=self._worker_process,
                args=(i, self.message_queue, self.result_queue, session_id),
            )
            worker.start()
            self.workers.append(worker)

        # Start database writer process (pass db path, not connection)
        db_writer = mp.Process(
            target=self._database_writer_process,
            args=(self.result_queue, duckdb_manager.db_path, session_id),
        )
        db_writer.start()

        try:
            # Start the producer process to read messages from file
            total_messages = self._produce_messages(
                session_id, file_path, log_type, max_messages
            )

            # Signal workers to stop by sending poison pills
            for _ in self.workers:
                self.message_queue.put(None)  # One poison pill per worker

            # Wait for all workers to complete
            for worker in self.workers:
                worker.join(timeout=10.0)  # Increased timeout
                if worker.is_alive():
                    logger.warning(
                        f"Worker {worker.pid} did not terminate gracefully, forcing..."
                    )
                    worker.terminate()
                    worker.join(timeout=2.0)

            # Signal database writer to stop and wait
            self.result_queue.put(None)  # Poison pill for db writer
            db_writer.join(timeout=15.0)  # Increased timeout for database operations

            if db_writer.is_alive():
                logger.warning(
                    "Database writer did not terminate gracefully, forcing..."
                )
                db_writer.terminate()
                db_writer.join(timeout=2.0)

            logger.info(f"Multiprocess parsing completed: {total_messages} messages")

            # Calculate basic metadata (simplified for demo)
            flight_duration = None
            vehicle_metadata = {
                "vehicle_type": "Unknown",
                "flight_modes_used": [],
                "autopilot_version": "Unknown",
            }

            return total_messages, flight_duration, vehicle_metadata

        except Exception as e:
            logger.error(f"Multiprocess parsing failed: {e}")
            # Clean up processes
            self._cleanup_processes(db_writer)
            raise

    def _produce_messages(
        self,
        session_id: UUID,
        file_path: Path,
        log_type: LogFileType,
        max_messages: Optional[int],
    ) -> int:
        """Producer process: read messages from file and send to queue."""

        parser = create_parser(session_id, file_path, log_type)
        message_count = 0

        logger.info("Starting message production...")

        for message in parser.get_messages():
            if max_messages and message_count >= max_messages:
                logger.info(f"Reached message limit: {max_messages}")
                break

            # Send message to workers
            try:
                self.message_queue.put(message, timeout=5.0)
                message_count += 1

                if message_count % 5000 == 0:
                    logger.info(f"Produced {message_count:,} messages")

            except queue.Full:
                logger.warning("Message queue full, slowing down production")
                time.sleep(0.1)

        logger.info(f"Message production completed: {message_count} messages")
        return message_count

    @staticmethod
    def _worker_process(
        worker_id: int,
        message_queue: mp.Queue,
        result_queue: mp.Queue,
        session_id: UUID,
    ):
        """Worker process: process messages and route to appropriate batches."""

        logger.info(f"Worker {worker_id} started")

        processed_count = 0
        batch_size = 2000  # Larger batch size for better performance
        batches = {"gps": [], "attitude": [], "sensor": [], "events": [], "system": []}

        while True:
            try:
                # Get message from queue
                message = message_queue.get(timeout=1.0)

                if message is None:  # Poison pill
                    break

                # Process message and route to batch
                MultiprocessLogParser._route_message_to_batch(
                    session_id, message, batches
                )
                processed_count += 1

                # Send full batches to database writer (larger batches = better performance)
                if processed_count % batch_size == 0:
                    MultiprocessLogParser._send_batches_to_db(result_queue, batches)

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")

        # Send remaining batches
        MultiprocessLogParser._send_batches_to_db(result_queue, batches)

        logger.info(
            f"Worker {worker_id} completed: {processed_count} messages processed"
        )

    @staticmethod
    def _route_message_to_batch(
        session_id: UUID, message: Dict[str, Any], batches: Dict[str, List]
    ):
        """Route message to appropriate batch (expanded version)."""

        msg_type = message.get("_type", "").upper()

        # Dataflash messages (most common for .bin files)
        if msg_type == "ATT":  # Attitude
            record = MultiprocessLogParser._prepare_attitude_record(session_id, message)
            batches["attitude"].append(record)
        elif msg_type == "IMU":  # Sensor data
            record = MultiprocessLogParser._prepare_sensor_record(session_id, message)
            batches["sensor"].append(record)
        elif msg_type in ["GPS", "POS"]:  # Standard GPS coordinates
            record = MultiprocessLogParser._prepare_gps_record(session_id, message)
            batches["gps"].append(record)
        elif msg_type in ["XKF1", "XKF2", "XKF3", "XKF4"]:  # EKF GPS/Navigation data
            record = MultiprocessLogParser._prepare_gps_record(session_id, message)
            batches["gps"].append(record)
        elif msg_type in ["MSG", "MODE", "FTN"]:  # Events and status
            record = MultiprocessLogParser._prepare_event_record(session_id, message)
            batches["events"].append(record)
        elif msg_type in [
            "BAT",
            "RATE",
            "PIDR",
            "PIDP",
            "PIDY",
            "PIDA",
        ]:  # System/Battery
            record = MultiprocessLogParser._prepare_system_record(session_id, message)
            batches["system"].append(record)
        # Add more message types as needed

    @staticmethod
    def _send_batches_to_db(result_queue: mp.Queue, batches: Dict[str, List]):
        """Send non-empty batches to database writer."""

        for batch_type, records in batches.items():
            if records:
                try:
                    # Longer timeout to reduce queue full warnings
                    result_queue.put((batch_type, records.copy()), timeout=5.0)
                    records.clear()
                except queue.Full:
                    # Only warn occasionally to avoid spam
                    if len(records) > 1000:  # Only warn for large batches
                        logger.warning(
                            f"Result queue full for {batch_type}, database writer may be slow ({len(records)} records pending)"
                        )
                    # Keep records for retry later instead of dropping

    @staticmethod
    def _database_writer_process(
        result_queue: mp.Queue, db_path: str, session_id: UUID
    ):
        """Database writer process: handle all database insertions."""

        logger.info("Database writer started")
        conn = None
        total_written = 0
        batches_processed = 0

        try:
            # Create new DuckDB connection in this process
            import duckdb

            conn = duckdb.connect(db_path)
            logger.info(f"Database writer connected to {db_path}")

            while True:
                try:
                    result = result_queue.get(timeout=5.0)  # Increased timeout

                    if result is None:  # Poison pill
                        logger.info("Database writer received shutdown signal")
                        break

                    batch_type, records = result

                    if not records:  # Skip empty batches
                        continue

                    # Write each batch individually with its own transaction
                    try:
                        MultiprocessLogParser._write_batch_to_db(
                            conn, batch_type, records
                        )

                        total_written += len(records)
                        batches_processed += 1

                        # More frequent logging for debugging
                        if batches_processed % 10 == 0 or total_written % 5000 == 0:
                            logger.info(
                                f"Database writer: {total_written:,} records written ({batches_processed} batches)"
                            )

                    except Exception as e:
                        logger.error(f"Database write error for {batch_type}: {e}")
                        # Continue processing other batches instead of stopping

                except queue.Empty:
                    # Timeout waiting for data - this is normal during shutdown
                    continue
                except Exception as e:
                    logger.error(f"Database writer queue error: {e}")
                    continue

        except Exception as e:
            logger.error(f"Database writer fatal error: {e}")
        finally:
            # Ensure database connection is properly closed
            if conn:
                try:
                    conn.close()
                    logger.info("Database writer connection closed")
                except:
                    pass

            logger.info(
                f"Database writer completed: {total_written:,} records written in {batches_processed} batches"
            )

    @staticmethod
    def _write_batch_to_db(conn, batch_type: str, records: List):
        """Write a batch of records to the database with individual transaction."""

        if not records:
            return

        try:
            conn.execute("BEGIN TRANSACTION")

            if batch_type == "gps":
                conn.executemany(
                    """
                    INSERT INTO gps_telemetry 
                    (session_id, time_boot_ms, timestamp_utc, lat, lon, alt, 
                     relative_alt, vx, vy, vz, hdg, eph, epv, vel, cog, fix_type, 
                     satellites_visible, dgps_numch, dgps_age) VALUES 
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
            else:
                logger.warning(f"Unknown batch type: {batch_type}")
                conn.execute("ROLLBACK")
                return

            conn.execute("COMMIT")

        except Exception as e:
            try:
                conn.execute("ROLLBACK")
            except:
                pass
            raise  # Re-raise the exception for logging

    # Record preparation methods (expanded versions)
    @staticmethod
    def _prepare_attitude_record(session_id: UUID, message: Dict[str, Any]) -> tuple:
        return (
            str(session_id),
            message.get("time_boot_ms", 0),
            message.get("timestamp_utc"),
            message.get("Roll"),
            message.get("Pitch"),
            message.get("Yaw"),
            None,
            None,
            None,  # Speed data not in ATT messages
        )

    @staticmethod
    def _prepare_sensor_record(session_id: UUID, message: Dict[str, Any]) -> tuple:
        return (
            str(session_id),
            message.get("time_boot_ms", 0),
            message.get("timestamp_utc"),
            message.get("AccX"),
            message.get("AccY"),
            message.get("AccZ"),
            message.get("GyrX"),
            message.get("GyrY"),
            message.get("GyrZ"),
            None,
            None,
            None,  # Mag data not in IMU messages
        )

    @staticmethod
    def _prepare_event_record(session_id: UUID, message: Dict[str, Any]) -> tuple:
        msg_type = message.get("_type", "UNKNOWN")
        if msg_type == "MSG":
            description = message.get("Message", "")
        elif msg_type == "MODE":
            description = f"Mode changed to {message.get('Mode', 'Unknown')}"
        else:
            description = str(message)

        return (
            str(session_id),
            message.get("time_boot_ms", 0),
            message.get("timestamp_utc"),
            msg_type,
            description,
            "info",
            None,
        )

    @staticmethod
    def _prepare_system_record(session_id: UUID, message: Dict[str, Any]) -> tuple:
        return (
            str(session_id),
            message.get("time_boot_ms", 0),
            message.get("timestamp_utc"),
            message.get("Volt"),
            message.get("Curr"),
            message.get("RemPct"),
            message.get("Temp"),
            None,
            None,
            None,
            None,
            None,
            None,  # Radio data not in BAT messages
        )

    @staticmethod
    def _prepare_gps_record(session_id: UUID, message: Dict[str, Any]) -> tuple:
        """Prepare GPS record from GPS/POS or XKF messages."""
        msg_type = message.get("_type", "").upper()

        if msg_type in ["GPS", "POS"]:
            # Standard GPS/POS messages with simple field names
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
        else:
            # XKF messages with EKF field names
            return (
                str(session_id),
                message.get("time_boot_ms", 0),
                message.get("timestamp_utc"),
                message.get("Lat"),  # Latitude
                message.get("Lng"),  # Longitude
                message.get("Alt"),  # Altitude
                None,  # relative_alt not in XKF
                message.get("VN"),  # North velocity
                message.get("VE"),  # East velocity
                message.get("VD"),  # Down velocity
                None,  # hdg not in XKF
                None,  # eph not in XKF
                None,  # epv not in XKF
                None,  # vel (computed from VN, VE)
                None,  # cog not in XKF
                None,  # fix_type not in XKF
                None,  # satellites_visible not in XKF
                None,  # dgps_numch not in XKF
                None,  # dgps_age not in XKF
            )

    def _cleanup_processes(self, db_writer):
        """Clean up worker processes in case of error."""

        logger.info("Cleaning up multiprocessing workers...")

        # Terminate workers with grace period
        for i, worker in enumerate(self.workers):
            if worker.is_alive():
                logger.info(f"Terminating worker {i}")
                worker.terminate()
                worker.join(timeout=2.0)
                if worker.is_alive():
                    logger.warning(f"Worker {i} did not terminate, killing...")
                    worker.kill() if hasattr(worker, "kill") else None

        # Terminate database writer
        if db_writer and db_writer.is_alive():
            logger.info("Terminating database writer")
            db_writer.terminate()
            db_writer.join(timeout=3.0)
            if db_writer.is_alive():
                logger.warning("Database writer did not terminate, killing...")
                db_writer.kill() if hasattr(db_writer, "kill") else None

        logger.info("Process cleanup completed")
