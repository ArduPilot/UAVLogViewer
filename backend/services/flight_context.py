"""
Flight context extraction service.
Transforms raw session data into structured flight metrics for LLM consumption.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def extract_flight_metrics(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and format flight metrics for LLM consumption.

    Parameters
    ----------
    session_data : Dict[str, Any]
        Raw session data from SQLite database

    Returns
    -------
    Dict[str, Any]
        Structured flight metrics formatted for LLM context
    """
    if not session_data:
        return {}

    try:
        # Basic flight information
        basic_info = {
            "filename": session_data.get("filename", "Unknown"),
            "log_type": session_data.get("log_type", "Unknown"),
            "file_size_mb": round(session_data.get("file_size", 0) / (1024 * 1024), 2),
            "upload_date": _format_datetime(session_data.get("created_at")),
            "processing_date": _format_datetime(session_data.get("processed_at")),
        }

        # Flight duration and timing
        duration_seconds = session_data.get("flight_duration_seconds")
        timing = {}
        if duration_seconds is not None:
            timing = {
                "total_duration_seconds": round(duration_seconds, 1),
                "total_duration_minutes": round(duration_seconds / 60, 1),
                "start_time": _format_datetime(session_data.get("start_time")),
                "end_time": _format_datetime(session_data.get("end_time")),
            }

        # Altitude metrics
        altitude = {}
        max_alt = session_data.get("max_altitude_m")
        min_alt = session_data.get("min_altitude_m")

        try:
            if max_alt is not None or min_alt is not None:
                altitude = {
                    "maximum_altitude_meters": (
                        round(max_alt, 1) if max_alt is not None else "Not available"
                    ),
                    "minimum_altitude_meters": (
                        round(min_alt, 1) if min_alt is not None else "Not available"
                    ),
                    "altitude_range_meters": (
                        round(max_alt - min_alt, 1)
                        if (max_alt is not None and min_alt is not None)
                        else "Not available"
                    ),
                }
        except Exception as e:
            logger.error(
                f"Error in altitude metrics calculation: {e}, max_alt={max_alt}, min_alt={min_alt}"
            )
            altitude = {}

        # Speed and distance metrics
        speed_distance = {}
        max_speed = session_data.get("max_speed_ms")
        total_distance = session_data.get("total_distance_km")

        try:
            if max_speed is not None or total_distance is not None:
                speed_distance = {
                    "maximum_ground_speed_ms": (
                        round(max_speed, 1)
                        if max_speed is not None
                        else "Not available"
                    ),
                    "maximum_ground_speed_kmh": (
                        round(max_speed * 3.6, 1)
                        if max_speed is not None
                        else "Not available"
                    ),
                    "total_distance_km": (
                        round(total_distance, 2)
                        if total_distance is not None
                        else "Not available"
                    ),
                    "average_speed_ms": _calculate_average_speed(
                        total_distance, duration_seconds
                    ),
                }
        except Exception as e:
            logger.error(
                f"Error in speed/distance metrics calculation: {e}, max_speed={max_speed}, total_distance={total_distance}, duration_seconds={duration_seconds}"
            )
            speed_distance = {}

        # GPS and navigation
        navigation = {}
        gps_fix_type = session_data.get("gps_fix_type_max")
        if gps_fix_type is not None:
            navigation = {
                "best_gps_fix_type": gps_fix_type,
                "gps_fix_quality": _interpret_gps_fix_type(gps_fix_type),
            }

        # System health and messages
        system_health = {
            "total_messages_parsed": session_data.get("message_count") or 0,
            "error_count": session_data.get("error_count") or 0,
            "warning_count": session_data.get("warning_count") or 0,
            "message_types_available": session_data.get("available_message_types")
            or [],
        }

        # Vehicle and flight modes
        vehicle_info = {}
        vehicle_type = session_data.get("vehicle_type")
        flight_modes = session_data.get("flight_modes_used")
        autopilot_version = session_data.get("autopilot_version")

        if vehicle_type or flight_modes or autopilot_version:
            vehicle_info = {
                "vehicle_type": _interpret_vehicle_type(vehicle_type),
                "flight_modes_used": (
                    flight_modes if isinstance(flight_modes, list) else []
                ),
                "autopilot_version": autopilot_version,
            }

        # Compile final metrics dictionary (only include sections with data)
        metrics = {"basic_info": basic_info}

        if timing:
            metrics["flight_timing"] = timing
        if altitude:
            metrics["altitude_performance"] = altitude
        if speed_distance:
            metrics["speed_and_distance"] = speed_distance
        if navigation:
            metrics["navigation_data"] = navigation
        if system_health["total_messages_parsed"] > 0:
            metrics["system_health"] = system_health
        if vehicle_info:
            metrics["vehicle_information"] = vehicle_info

        return metrics

    except Exception as e:
        logger.error(f"Error extracting flight metrics: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "error": f"Failed to extract flight metrics: {str(e)}",
            "basic_info": {
                "filename": session_data.get("filename", "Unknown"),
                "status": "Error during metrics extraction",
            },
        }


def _format_datetime(dt) -> Optional[str]:
    """Format datetime for human readability."""
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except:
            return dt
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    return str(dt)


def _calculate_average_speed(
    distance_km: Optional[float], duration_seconds: Optional[float]
) -> str:
    """Calculate average speed from distance and duration."""
    if distance_km is None or duration_seconds is None or duration_seconds <= 0:
        return "Not available"

    avg_speed_ms = (distance_km * 1000) / duration_seconds
    return f"{avg_speed_ms:.1f} m/s"


def _interpret_gps_fix_type(fix_type: int) -> str:
    """Interpret GPS fix type code."""
    gps_fix_types = {
        0: "No GPS",
        1: "No Fix",
        2: "2D Fix",
        3: "3D Fix",
        4: "DGPS",
        5: "RTK Float",
        6: "RTK Fixed",
    }
    return gps_fix_types.get(fix_type, f"Unknown ({fix_type})")


def _interpret_vehicle_type(vehicle_type: Optional[str]) -> str:
    """Interpret vehicle type."""
    if not vehicle_type:
        return "Unknown"

    # Common ArduPilot vehicle types
    vehicle_types = {
        "1": "Fixed Wing",
        "2": "Quadrotor",
        "3": "Coaxial Helicopter",
        "4": "Helicopter",
        "10": "Ground Rover",
        "12": "Submarine",
    }

    return vehicle_types.get(str(vehicle_type), vehicle_type)


def has_sufficient_flight_data(session_data: Dict[str, Any]) -> bool:
    """
    Check if session has sufficient flight data for meaningful analysis.

    Parameters
    ----------
    session_data : Dict[str, Any]
        Session data from database

    Returns
    -------
    bool
        True if session has meaningful flight metrics
    """
    if not session_data:
        return False

    # Check for basic flight indicators
    has_duration = session_data.get("flight_duration_seconds") is not None
    has_messages = (session_data.get("message_count") or 0) > 0
    has_metrics = any(
        [
            session_data.get("max_altitude_m"),
            session_data.get("max_speed_ms"),
            session_data.get("total_distance_km"),
        ]
    )

    return has_duration or (has_messages and has_metrics)


def format_metrics_summary(metrics: Dict[str, Any]) -> str:
    """
    Create a concise summary of key flight metrics for LLM context.

    Parameters
    ----------
    metrics : Dict[str, Any]
        Extracted flight metrics

    Returns
    -------
    str
        Human-readable summary of key metrics
    """
    if not metrics or "error" in metrics:
        return "No flight data available for analysis."

    summary_parts = []

    # Basic info
    if "basic_info" in metrics:
        filename = metrics["basic_info"].get("filename", "Unknown")
        summary_parts.append(f"Flight log: {filename}")

    # Duration
    if "flight_timing" in metrics:
        duration_min = metrics["flight_timing"].get("total_duration_minutes")
        if duration_min:
            summary_parts.append(f"Duration: {duration_min} minutes")

    # Altitude
    if "altitude_performance" in metrics:
        max_alt = metrics["altitude_performance"].get("maximum_altitude_meters")
        if max_alt != "Not available":
            summary_parts.append(f"Max altitude: {max_alt}m")

    # Distance
    if "speed_and_distance" in metrics:
        distance = metrics["speed_and_distance"].get("total_distance_km")
        if distance != "Not available":
            summary_parts.append(f"Distance: {distance}km")

    # System health
    if "system_health" in metrics:
        errors = metrics["system_health"].get("error_count", 0)
        if errors > 0:
            summary_parts.append(f"Errors: {errors}")

    return (
        " | ".join(summary_parts) if summary_parts else "Limited flight data available."
    )
