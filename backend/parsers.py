"""
MAVLink and Dataflash log parsers using pymavlink.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Generator
from uuid import UUID

try:
    from pymavlink import mavutil
except ImportError:
    logger.error("pymavlink not installed. Install with: pip install pymavlink")
    raise

from schemas import LogFileType, FlightMetrics

logger = logging.getLogger(__name__)


class LogParseError(Exception):
    """Exception raised during log parsing."""

    pass


class BaseLogParser:
    """Base class for log parsers."""

    def __init__(self, session_id: UUID, file_path: Path):
        self.session_id = session_id
        self.file_path = file_path
        self.metrics = FlightMetrics()
        self.available_message_types: List[str] = []
        self._messages_cache: Optional[List[Dict[str, Any]]] = None

    def parse(self) -> Dict[str, Any]:
        """Parse the log file and return metadata."""
        raise NotImplementedError

    def get_messages(self) -> Generator[Dict[str, Any], None, None]:
        """Generator that yields parsed messages."""
        raise NotImplementedError

    def _message_to_dict(self, msg) -> Dict[str, Any]:
        """Convert pymavlink message to dictionary maintaining full precision."""
        try:
            msg_dict = msg.to_dict()
            msg_dict["_type"] = msg.get_type()

            # Preserve full timestamp precision - don't convert to int!
            if hasattr(msg, "time_boot_ms"):
                # Keep original precision for time_boot_ms
                msg_dict["time_boot_ms"] = msg.time_boot_ms
            elif hasattr(msg, "_timestamp"):
                # For some log formats, convert timestamp to boot time but preserve precision
                msg_dict["time_boot_ms"] = msg._timestamp * 1000.0  # Keep as float!

            # Add UTC timestamp for better time handling
            if hasattr(msg, "_timestamp"):
                try:
                    msg_dict["timestamp_utc"] = datetime.utcfromtimestamp(
                        msg._timestamp
                    )
                except (ValueError, OSError):
                    msg_dict["timestamp_utc"] = None

            # CRITICAL: Preserve raw coordinate values for GPS data
            # JavaScript stores raw integer values from MAVLink, we should too
            msg_type = msg.get_type()
            if msg_type == "GPS":
                # Keep raw integer values like JavaScript does
                if hasattr(msg, "Lat"):
                    msg_dict["Lat"] = int(msg.Lat)  # Raw GPS coordinate
                if hasattr(msg, "Lng"):
                    msg_dict["Lng"] = int(msg.Lng)  # Raw GPS coordinate
                if hasattr(msg, "Alt"):
                    msg_dict["Alt"] = int(msg.Alt)  # Raw altitude
                if hasattr(msg, "RelHomeAlt"):
                    msg_dict["RelHomeAlt"] = float(
                        msg.RelHomeAlt
                    )  # Keep precision for relative alt
                if hasattr(msg, "RelOriginAlt"):
                    # Handle None values properly
                    if msg.RelOriginAlt is not None:
                        msg_dict["RelOriginAlt"] = float(msg.RelOriginAlt)
                    else:
                        msg_dict["RelOriginAlt"] = None

            return msg_dict
        except Exception as e:
            logger.warning(f"Failed to convert message to dict: {e}")
            return {
                "_type": getattr(msg, "get_type", lambda: "UNKNOWN")(),
                "time_boot_ms": 0.0,  # Keep as float
                "timestamp_utc": None,
            }


class TLogParser(BaseLogParser):
    """Parser for .tlog files (MAVLink telemetry)."""

    def parse(self) -> Dict[str, Any]:
        """Parse TLOG file using pymavlink."""
        logger.info(f"Starting TLOG parsing for session {self.session_id}")

        try:
            # Cache messages during parsing for metrics calculation
            self._messages_cache = []
            message_types = set()

            # Parse messages and cache them
            for msg_dict in self.get_messages():
                self._messages_cache.append(msg_dict)
                message_types.add(msg_dict.get("_type", "UNKNOWN"))

            self.available_message_types = list(message_types)

            # Calculate metrics from cached messages
            self._calculate_metrics()

            return {
                "message_count": len(self._messages_cache),
                "available_message_types": self.available_message_types,
            }

        except Exception as e:
            logger.error(f"Failed to parse TLOG file {self.file_path}: {e}")
            raise LogParseError(f"TLOG parsing failed: {e}")

    def get_messages(self) -> Generator[Dict[str, Any], None, None]:
        """Generator for TLOG messages."""
        # If we have cached messages with content, yield them
        if self._messages_cache is not None and len(self._messages_cache) > 0:
            for msg in self._messages_cache:
                yield msg
            return

        try:
            # Connect to the log file
            mlog = mavutil.mavlink_connection(str(self.file_path))

            while True:
                msg = mlog.recv_match()
                if msg is None:
                    break

                yield self._message_to_dict(msg)

        except Exception as e:
            logger.error(f"Error reading TLOG messages: {e}")
            raise LogParseError(f"Failed to read TLOG messages: {e}")

    def _calculate_metrics(self):
        """Calculate flight metrics from cached messages."""
        if not self._messages_cache:
            return

        gps_data = []
        battery_data = []
        status_messages = []

        for msg in self._messages_cache:
            msg_type = msg.get("_type", "")

            # Collect GPS data
            if msg_type in ["GLOBAL_POSITION_INT", "GPS_RAW_INT"]:
                if msg.get("alt") is not None:
                    alt_m = msg.get("alt", 0) / 1000.0  # Convert from mm to m
                    gps_data.append(
                        {
                            "alt": alt_m,
                            "vel": (
                                msg.get("vel", 0) / 100.0 if msg.get("vel") else 0
                            ),  # Convert cm/s to m/s
                            "fix_type": msg.get("fix_type", 0),
                        }
                    )

            # Collect battery data
            elif msg_type == "SYS_STATUS":
                if msg.get("voltage_battery") is not None:
                    battery_data.append(
                        msg.get("voltage_battery", 0) / 1000.0
                    )  # Convert to V

            # Collect status messages for error/warning count
            elif msg_type == "STATUSTEXT":
                severity = msg.get("severity", 6)
                status_messages.append(severity)

        # Calculate GPS metrics
        if gps_data:
            altitudes = [
                d["alt"] for d in gps_data if d["alt"] > -1000
            ]  # Filter invalid altitudes
            speeds = [d["vel"] for d in gps_data if d["vel"] >= 0]
            fix_types = [d["fix_type"] for d in gps_data]

            if altitudes:
                self.metrics.max_altitude_m = max(altitudes)
                self.metrics.min_altitude_m = min(altitudes)

            if speeds:
                self.metrics.max_speed_ms = max(speeds)

            if fix_types:
                self.metrics.gps_fix_type_max = max(fix_types)
                self.metrics.gps_fix_count = len(
                    [f for f in fix_types if f >= 2]
                )  # Valid fixes

        # Calculate battery metrics
        if battery_data:
            self.metrics.max_battery_voltage = max(battery_data)
            self.metrics.min_battery_voltage = min(battery_data)

        # Calculate error/warning counts
        if status_messages:
            self.metrics.error_count = len(
                [s for s in status_messages if s <= 3]
            )  # ERROR or worse
            self.metrics.warning_count = len(
                [s for s in status_messages if s == 4]
            )  # WARNING


class BinLogParser(BaseLogParser):
    """Parser for .bin files (ArduPilot Dataflash)."""

    def parse(self) -> Dict[str, Any]:
        """Parse BIN file using pymavlink DFReader."""
        logger.info(f"Starting BIN parsing for session {self.session_id}")

        try:
            # Cache messages during parsing for metrics calculation
            self._messages_cache = []
            message_types = set()

            # Parse messages and cache them
            for msg_dict in self.get_messages():
                self._messages_cache.append(msg_dict)
                message_types.add(msg_dict.get("_type", "UNKNOWN"))

            self.available_message_types = list(message_types)

            # Calculate metrics from cached messages
            self._calculate_metrics()

            return {
                "message_count": len(self._messages_cache),
                "available_message_types": self.available_message_types,
            }

        except Exception as e:
            logger.error(f"Failed to parse BIN file {self.file_path}: {e}")
            raise LogParseError(f"BIN parsing failed: {e}")

    def get_messages(self) -> Generator[Dict[str, Any], None, None]:
        """Generator for BIN messages."""
        # If we have cached messages with content, yield them
        if self._messages_cache is not None and len(self._messages_cache) > 0:
            for msg in self._messages_cache:
                yield msg
            return

        try:
            # Use mavutil for dataflash logs - it handles .bin files correctly
            mlog = mavutil.mavlink_connection(
                str(self.file_path), dialect="ardupilotmega"
            )

            while True:
                msg = mlog.recv_match()
                if msg is None:
                    break

                yield self._message_to_dict(msg)

        except Exception as e:
            logger.error(f"Error reading BIN messages: {e}")
            raise LogParseError(f"Failed to read BIN messages: {e}")

    def _calculate_metrics(self):
        """Calculate flight metrics from cached messages."""
        if not self._messages_cache:
            return

        altitude_data = []
        battery_data = []
        error_count = 0
        warning_count = 0

        for msg in self._messages_cache:
            msg_type = msg.get("_type", "").upper()

            # -----------------------------
            # Altitude & battery collection
            # -----------------------------
            if msg_type == "BARO":
                alt = msg.get("Alt")
                if alt is not None:
                    altitude_data.append(alt)  # already metres
            elif msg_type in {"GPS", "POS"}:  # Dataflash GPS/POS
                alt = msg.get("Alt")
                if alt is not None:
                    altitude_data.append(
                        alt / 100.0 if alt > 90_000 else alt
                    )  # convert cm->m if needed

            if msg_type == "BAT":
                volt = msg.get("Volt")
                if volt is not None:
                    battery_data.append(volt)

            # -----------------------------
            # Error / warning determination
            # -----------------------------
            if msg_type == "ERR":
                error_count += 1
            elif msg_type in {"EV", "EVT"}:
                sev = msg.get("Severity") or msg.get("LogLevel")
                if sev is not None:
                    if sev <= 3:
                        error_count += 1
                    elif sev == 4:
                        warning_count += 1
            elif msg_type == "STATUSTEXT":
                sev = msg.get("severity", 6)
                if sev <= 3:
                    error_count += 1
                elif sev == 4:
                    warning_count += 1
            elif msg_type == "MSG":
                text = msg.get("Message", "").upper()
                if any(k in text for k in ("FAIL", "ERR", "FAILSAFE")):
                    error_count += 1

        # -----------------------------
        # Derive metrics
        # -----------------------------
        if altitude_data:
            valid_altitudes = [alt for alt in altitude_data if abs(alt) < 5000]
            if valid_altitudes:
                self.metrics.max_altitude_m = max(valid_altitudes)
                self.metrics.min_altitude_m = min(valid_altitudes)

        if battery_data:
            self.metrics.max_battery_voltage = max(battery_data)
            self.metrics.min_battery_voltage = min(battery_data)

        self.metrics.error_count = error_count
        self.metrics.warning_count = warning_count


def create_parser(
    session_id: UUID, file_path: Path, log_type: LogFileType
) -> BaseLogParser:
    """Factory function to create appropriate parser."""
    if log_type == LogFileType.TLOG:
        return TLogParser(session_id, file_path)
    elif log_type == LogFileType.BIN:
        return BinLogParser(session_id, file_path)
    else:
        raise LogParseError(f"Unsupported log type: {log_type}")


def detect_log_type(filename: str) -> Optional[LogFileType]:
    """Detect log type from filename."""
    filename_lower = filename.lower()

    if filename_lower.endswith(".tlog"):
        return LogFileType.TLOG
    elif filename_lower.endswith(".bin"):
        return LogFileType.BIN
    else:
        return None
