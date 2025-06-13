"""
Pydantic schemas for request/response validation.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field, validator


class LogFileType(str, Enum):
    """Supported log file types."""

    TLOG = "tlog"
    BIN = "bin"


class ParseStatus(str, Enum):
    """Status of log file parsing."""

    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class UploadLogResponse(BaseModel):
    """Response from log upload endpoint."""

    session_id: UUID
    status: ParseStatus = ParseStatus.PROCESSING
    filename: str
    file_size: int
    log_type: LogFileType
    message: str = "Log upload successful, processing started"


class SessionStatus(BaseModel):
    """Session status and metadata."""

    session_id: UUID
    filename: str
    file_size: int
    log_type: LogFileType
    status: ParseStatus
    created_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    # Flight metadata (populated after parsing)
    flight_duration_seconds: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    message_count: Optional[int] = None
    available_message_types: Optional[List[str]] = None

    # Vehicle and flight specific data (from MAVLink messages)
    vehicle_type: Optional[str] = None  # From HEARTBEAT.type
    flight_modes_used: Optional[List[str]] = None  # From HEARTBEAT.custom_mode
    total_distance_km: Optional[float] = None  # Calculated from GPS
    max_altitude_m: Optional[float] = None  # From GPS messages
    min_altitude_m: Optional[float] = None  # From GPS messages
    max_speed_ms: Optional[float] = None  # From GPS.vel
    gps_fix_type_max: Optional[int] = None  # From GPS_RAW_INT.fix_type
    error_count: Optional[int] = None  # From STATUSTEXT severity <= 3
    warning_count: Optional[int] = None  # From STATUSTEXT severity == 4

    # Optional fields (may not be available in all logs)
    autopilot_version: Optional[str] = None  # From AUTOPILOT_VERSION if present


class ChatRequest(BaseModel):
    """Chat message request."""

    session_id: UUID
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[UUID] = None


class ChatResponse(BaseModel):
    """Chat message response."""

    response: str
    session_id: UUID
    conversation_id: UUID
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


class ConversationMessage(BaseModel):
    """Represents a single message in a chatbot conversation (either user or assistant)."""

    conversation_id: UUID
    session_id: UUID
    message_type: str = Field(..., pattern="^(user|assistant)$")
    message: str = Field(..., min_length=1, max_length=2000)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[UUID] = None


class FlightMetrics(BaseModel):
    """Basic flight metrics computed during parsing."""

    max_altitude: Optional[float] = None
    min_altitude: Optional[float] = None
    max_speed: Optional[float] = None
    max_battery_voltage: Optional[float] = None
    min_battery_voltage: Optional[float] = None
    gps_fix_count: Optional[int] = None
    total_distance: Optional[float] = None
    total_distance_km: Optional[float] = None  # Total distance travelled (kilometres)
    max_altitude_m: Optional[float] = (
        None  # Max altitude in metres (relative/ASL depending on source)
    )
    min_altitude_m: Optional[float] = None  # Min altitude in metres
    max_speed_ms: Optional[float] = None  # Maximum ground speed (m/s)
    gps_fix_type_max: Optional[int] = None  # Best GPS fix type achieved
    error_count: Optional[int] = None  # Number of MAV_SEVERITY_ERROR or worse messages
    warning_count: Optional[int] = None  # Number of MAV_SEVERITY_WARNING messages

    @validator("max_altitude", "min_altitude", "max_speed", pre=True)
    def validate_positive_metrics(cls, v):
        if v is not None and v < 0:
            return None
        return v


class SessionListResponse(BaseModel):
    """Response model for listing all available session IDs."""

    session_ids: List[UUID]
