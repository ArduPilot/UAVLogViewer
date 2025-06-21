"""
FastAPI application for UAV Log Viewer chatbot backend.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4
import json

# Silence HuggingFace tokenizers warning in multi-process environment
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# Load environment variables from .env file
from dotenv import load_dotenv

# Try to load .env from multiple locations
env_paths = [
    Path(__file__).parent / ".env",  # backend/.env
    Path(__file__).parent.parent / ".env",  # root/.env
    ".env",  # current directory
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        logging.info(f"Loaded environment variables from {env_path}")
        break
else:
    logging.info("No .env file found, using system environment variables")

from fastapi import FastAPI, HTTPException, UploadFile, File, status, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from db import get_sqlite_manager, get_duckdb_manager, get_uploads_dir
from parsers import detect_log_type, LogParseError
from schemas import (
    HealthResponse,
    UploadLogResponse,
    SessionStatus,
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    LogFileType,
    ParseStatus,
    SessionListResponse,
)
from tasks import start_parse_task, is_task_running
from services.llm_client import (
    get_llm_client,
    set_llm_client,
    initialize_default_llm_client,
    LLMClient,
    LLMConfigurationError,
    LLMServiceError,
)
from services.flight_context import (
    extract_flight_metrics,
    has_sufficient_flight_data,
    format_metrics_summary,
)
from services.prompt_templates import (
    validate_prompt_inputs,
    _get_flight_aware_instructions,
    _get_no_session_instructions,
    _format_flight_metrics_for_developer_message,
)
from services.chat_orchestrator import ChatOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="UAV Log Viewer Chatbot API",
    description="Backend API for analyzing UAV flight logs with AI-powered chat interface",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],  # Vue dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
ALLOWED_EXTENSIONS = {".tlog", ".bin"}

# ---------------------------------------------------------------------------
# Configuration Flags
# ---------------------------------------------------------------------------

# Flag to control whether development-only debug routes are exposed.
# Set `DEBUG_MODE=true` in the environment (or 1/yes) to enable them.
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() in {"1", "true", "yes"}


# Dependency injection for LLM client
async def get_llm_client_dependency() -> LLMClient:
    """FastAPI dependency to get LLM client."""
    try:
        return get_llm_client()
    except LLMConfigurationError as e:
        logger.error(f"LLM client not configured: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service temporarily unavailable - LLM not configured",
        )


# Dependency injection for ChatOrchestrator
async def get_chat_orchestrator_dependency(
    llm_client: LLMClient = Depends(get_llm_client_dependency),
) -> ChatOrchestrator:
    """FastAPI dependency to get ChatOrchestrator with tool registry."""

    # Create a dummy tool registry that will be initialized per-request
    # The orchestrator will create the actual tool registry with session context
    class DummyToolRegistry:
        def __init__(self):
            self.sqlite_manager = get_sqlite_manager()
            self.duckdb_manager = get_duckdb_manager()

    dummy_registry = DummyToolRegistry()

    return ChatOrchestrator(
        llm_client=llm_client,
        tool_registry=dummy_registry,
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    """Handle Pydantic validation errors."""
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(error="Validation Error", detail=str(exc)).dict(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal Server Error", detail="An unexpected error occurred"
        ).dict(),
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@app.post("/upload-log", response_model=UploadLogResponse)
async def upload_log(file: UploadFile = File(...)):
    """
    Upload and parse a UAV log file (.tlog or .bin).

    Returns a session_id and starts background parsing.
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided"
            )

        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        # Detect log type
        log_type = detect_log_type(file.filename)
        if not log_type:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Could not determine log file type",
            )

        # Read file content and check size
        content = await file.read()
        file_size = len(content)

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file"
            )

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)} MB",
            )

        # Generate session ID and save file
        session_id = uuid4()
        uploads_dir = get_uploads_dir()
        file_path = uploads_dir / f"{session_id}{file_ext}"

        try:
            with open(file_path, "wb") as f:
                f.write(content)
        except IOError as e:
            logger.error(f"Failed to save uploaded file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save uploaded file",
            )

        # Create session record
        sqlite_manager = get_sqlite_manager()
        try:
            await sqlite_manager.create_session(
                session_id=session_id,
                filename=file.filename,
                file_size=file_size,
                log_type=log_type,
            )
        except Exception as e:
            logger.error(f"Failed to create session record: {e}")
            # Clean up uploaded file
            try:
                file_path.unlink()
            except:
                pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create session record",
            )

        # Start background parsing task
        try:
            await start_parse_task(session_id, file_path, log_type)
        except Exception as e:
            logger.error(f"Failed to start parsing task: {e}")
            # Note: We don't clean up here as the session record exists
            # The task will mark it as failed

        logger.info(
            f"Successfully uploaded file {file.filename} as session {session_id}"
        )

        return UploadLogResponse(
            session_id=session_id,
            filename=file.filename,
            file_size=file_size,
            log_type=log_type,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in upload_log: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during file upload",
        )


@app.get("/sessions/{session_id}", response_model=SessionStatus)
async def get_session_status(session_id: UUID):
    """
    Get the status of a parsing session.
    """
    try:
        sqlite_manager = get_sqlite_manager()
        session = await sqlite_manager.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        # Check if task is still running
        if session["status"] == ParseStatus.PROCESSING:
            if not is_task_running(session_id):
                # Task is no longer running but status wasn't updated
                # This might happen if the task crashed
                await sqlite_manager.update_session_status(
                    session_id,
                    ParseStatus.FAILED,
                    error_message="Task terminated unexpectedly",
                )
                session["status"] = ParseStatus.FAILED
                session["error_message"] = "Task terminated unexpectedly"

        return SessionStatus(**session)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session status",
        )


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    orchestrator: ChatOrchestrator = Depends(get_chat_orchestrator_dependency),
):
    """
    Chat endpoint for conversing about flight log data.

    This endpoint now uses the ChatOrchestrator to handle the complete
    request-execution-response loop, including potential tool calls.
    """
    return await orchestrator.process_message(request)


if DEBUG_MODE:

    @app.get("/debug/table-counts")
    async def get_table_counts():
        """Get row counts from all database tables for debugging."""
        try:
            from db import get_duckdb_manager

            duckdb_manager = get_duckdb_manager()
            conn = duckdb_manager.get_connection()

            tables = [
                "gps_telemetry",
                "attitude_telemetry",
                "sensor_telemetry",
                "flight_events",
                "system_status",
            ]
            counts = {}

            for table in tables:
                try:
                    result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                    counts[table] = result[0] if result else 0
                except Exception as e:
                    counts[table] = f"Error: {str(e)}"

            return {"table_counts": counts}

        except Exception as e:
            logger.error(f"Error getting table counts: {e}")
            return {"error": str(e)}

    @app.get("/debug/conversation/{conversation_id}")
    async def debug_get_conversation(
        conversation_id: UUID, limit: Optional[int] = None
    ):
        """Return messages for a given conversation (debug only)."""
        try:
            sqlite_manager = get_sqlite_manager()
            rows = await sqlite_manager.get_conversation(conversation_id, limit)
            return {"conversation_id": conversation_id, "messages": rows}
        except Exception as e:
            logger.error("Error getting conversation debug data: %s", e)
            raise HTTPException(status_code=500, detail="Failed to fetch conversation")

    @app.get("/debug/llm-status")
    async def debug_llm_status():
        """Check LLM client status for debugging."""
        try:
            llm_client = get_llm_client()
            health = await llm_client.health_check()

            return {
                "client_type": type(llm_client).__name__,
                "healthy": health,
                "model": getattr(llm_client, "model", "unknown"),
            }
        except LLMConfigurationError as e:
            return {"error": "LLM not configured", "detail": str(e)}
        except Exception as e:
            logger.error(f"Error checking LLM status: {e}")
            return {"error": "Failed to check LLM status", "detail": str(e)}

    @app.get("/debug/documentation-status")
    async def debug_documentation_status():
        """Check ArduPilot documentation system status for debugging."""
        try:
            from services.doc_initialization import get_documentation_status

            return get_documentation_status()
        except Exception as e:
            logger.error(f"Error checking documentation status: {e}")
            return {"error": "Failed to check documentation status", "detail": str(e)}


@app.get("/sessions", response_model=SessionListResponse)
async def list_sessions(limit: Optional[int] = None):
    """Return a list of all available session IDs (most recent first).

    Query Parameters
    ----------------
    limit: Optional[int]
        Maximum number of session IDs to return. If omitted, all IDs are returned.
    """
    try:
        sqlite_manager = get_sqlite_manager()
        session_ids = await sqlite_manager.list_session_ids(limit)
        return SessionListResponse(session_ids=session_ids)
    except Exception as e:
        logger.error(f"Error listing session IDs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list sessions",
        )


# Application lifecycle events
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting UAV Log Viewer Chatbot API")

    # Ensure required directories exist
    uploads_dir = get_uploads_dir()
    uploads_dir.mkdir(parents=True, exist_ok=True)

    # Initialize databases
    try:
        sqlite_manager = get_sqlite_manager()
        # The __init__ of the manager already creates the tables.
        # No explicit initialize call is needed.
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Initialize ArduPilot documentation system
    try:
        from services.doc_initialization import initialize_documentation_system

        doc_success = await initialize_documentation_system()
        if doc_success:
            logger.info("ArduPilot documentation system initialized successfully")
        else:
            logger.warning(
                "ArduPilot documentation system initialization failed - search may not work"
            )
            # Don't fail startup - the system can work without docs
    except Exception as e:
        logger.error(f"Failed to initialize documentation system: {e}")
        # Don't fail startup - just log the error

    # Initialize LLM client
    try:
        llm_client = await initialize_default_llm_client()
        set_llm_client(llm_client)
        logger.info("LLM client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize LLM client: {e}")
        # Don't fail startup - just log the error
        # The dependency injection will handle the error appropriately

    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down UAV Log Viewer Chatbot API")

    # TODO: Clean up any resources, close connections, etc.

    logger.info("Application shutdown complete")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
