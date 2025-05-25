from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
import uuid
import asyncio
import logging
import traceback
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse

from agents.uav_agent import UavAgent, CustomJSONEncoder, ensure_serializable
from telemetry.parser import TelemetryParser
from telemetry.analyzer import TelemetryAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Session timeout in minutes (default: 30 minutes)
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))

# CORS configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8080").split(",")
ALLOWED_METHODS = os.getenv("ALLOWED_METHODS", "GET,POST,PUT,DELETE").split(",")
ALLOWED_HEADERS = os.getenv("ALLOWED_HEADERS", "Content-Type,Accept,Origin,X-Requested-With,X-Session-ID").split(",")
CORS_MAX_AGE = int(os.getenv("CORS_MAX_AGE", "3600"))

# File upload configuration
TEMP_UPLOAD_DIR = os.getenv("TEMP_UPLOAD_DIR", "temp")

# Global session registry
class SessionRegistry:
    def __init__(self):
        self.sessions: Dict[str, SessionData] = {}
        # Schedule periodic cleanup of expired sessions
        self.last_cleanup = datetime.now(timezone.utc)
        
    def create_session(self, session_id: str, telemetry_data: Dict, analyzer: TelemetryAnalyzer) -> 'SessionData':
        """Create a new session with the given ID and data."""
        if session_id in self.sessions:
            # Update existing session
            session = self.sessions[session_id]
            session.telemetry_data = telemetry_data
            session.analyzer = analyzer
            session.last_activity = datetime.now(timezone.utc)
            # Create new agent with updated data
            if analyzer is not None:  # Only create agent if analyzer is provided
                session.agent = UavAgent(session_id=session_id, analyzer=analyzer)
            return session
        else:
            # Create new session
            session = SessionData(
                id=session_id,
                telemetry_data=telemetry_data,
                analyzer=analyzer
            )
            self.sessions[session_id] = session
            return session
    
    def get_session(self, session_id: str) -> Optional['SessionData']:
        """Get session by ID, updating its last activity time."""
        session = self.sessions.get(session_id)
        if session:
            session.last_activity = datetime.now(timezone.utc)
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID."""
        if session_id in self.sessions:
            # Clean up session resources
            try:
                session = self.sessions[session_id]
                if session.agent and hasattr(session.agent, 'clear_memory'):
                    session.agent.clear_memory()
            except Exception as e:
                logger.error(f"Error during session cleanup: {str(e)}")
            
            # Remove from registry
            del self.sessions[session_id]
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """Remove sessions that have been inactive for too long."""
        now = datetime.now(timezone.utc)
        # Only run cleanup every 5 minutes
        if (now - self.last_cleanup).total_seconds() < 300:
            return
        
        self.last_cleanup = now
        expired_ids = []
        
        for session_id, session in self.sessions.items():
            # Check if session has expired
            if (now - session.last_activity).total_seconds() > SESSION_TIMEOUT_MINUTES * 60:
                expired_ids.append(session_id)
        
        # Delete expired sessions
        for session_id in expired_ids:
            logger.info(f"Cleaning up expired session: {session_id}")
            self.delete_session(session_id)
        
        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} expired sessions")

# Session data class
class SessionData:
    def __init__(
        self, 
        id: str, 
        telemetry_data: Dict,
        analyzer: TelemetryAnalyzer
    ):
        self.id = id
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = self.created_at
        self.telemetry_data = telemetry_data
        self.analyzer = analyzer
        # Create agent for this session only if we have an analyzer
        self.agent = UavAgent(session_id=id, analyzer=analyzer) if analyzer is not None else None
        self.messages: List[Dict] = []

# Create global session registry
registry = SessionRegistry()

# Define FastAPI app lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure temporary directory exists
    os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)
    logger.info(f"UAV Log Viewer API starting. Temp directory: {TEMP_UPLOAD_DIR}")
    yield
    # Shutdown: Clean up
    logger.info("UAV Log Viewer API shutting down. Cleaning up resources.")
    for session_id in list(registry.sessions.keys()):
        registry.delete_session(session_id)

# Initialize FastAPI application
app = FastAPI(lifespan=lifespan)

# Add CORS middleware with explicit method and header restrictions
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
    expose_headers=["X-Session-ID"],  # Expose session ID header for client use
    max_age=CORS_MAX_AGE,
)

# ─────────────────────────────────────────────────────────────────────────────
# Pydantic models for API
# ─────────────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    analysis: Optional[Dict[str, Any]] = None
    session_id: str

class SessionInfo(BaseModel):
    id: str
    created_at: datetime
    last_activity: datetime
    has_telemetry: bool

class SessionListResponse(BaseModel):
    sessions: List[SessionInfo]

class SessionResponse(BaseModel):
    session_id: str
    message: str

class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None

# ─────────────────────────────────────────────────────────────────────────────
# Dependencies
# ─────────────────────────────────────────────────────────────────────────────

async def get_session_from_header(
    x_session_id: Optional[str] = Header(None)
) -> Optional[SessionData]:
    """Get session from X-Session-ID header if provided."""
    if not x_session_id:
        logger.debug("No X-Session-ID header provided")
        return None
    
    logger.debug(f"Looking up session with ID: {x_session_id}")
    
    # Check if session exists
    session = registry.get_session(x_session_id)
    if session:
        logger.debug(f"Found session {x_session_id}, analyzer present: {session.analyzer is not None}")
        return session
    
    # Session not found
    logger.debug(f"Session not found: {x_session_id}")
    return None

async def get_or_create_session(
    session: Optional[SessionData] = Depends(get_session_from_header)
) -> SessionData:
    """Get existing session or create a new one."""
    if session:
        return session
    
    # Create new session ID
    session_id = str(uuid.uuid4())
    
    # Create minimal session without telemetry data
    # This will be updated when telemetry is uploaded
    minimal_session = SessionData(
        id=session_id,
        telemetry_data={},
        analyzer=None  # Will be populated with upload
    )
    
    registry.sessions[session_id] = minimal_session
    return minimal_session

async def ensure_session_with_telemetry(
    session: SessionData = Depends(get_or_create_session)
) -> SessionData:
    """Ensure the session has telemetry data, raising an exception if not."""
    # Check if session has telemetry data
    if not session.telemetry_data or not session.analyzer:
        raise HTTPException(
            status_code=400,
            detail="No telemetry data available. Please upload a log file first."
        )
    
    return session

# ─────────────────────────────────────────────────────────────────────────────
# API routes
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/upload", response_model=SessionResponse)
async def upload_log(
    file: UploadFile = File(...),
    session: SessionData = Depends(get_or_create_session)
):
    """
    Upload a telemetry log file for processing.
    
    This endpoint parses the uploaded log file into telemetry data and creates/updates
    a session with an agent that can analyze the data.
    
    Returns:
        SessionResponse: Confirmation with session ID
    """
    file_path = None
    try:
        # Clean up old sessions periodically
        registry.cleanup_expired_sessions()
        
        # Save file temporarily
        file_path = f"{TEMP_UPLOAD_DIR}/{session.id}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        try:
            # Parse telemetry data - rely on parser to handle the details
            logger.info(f"Parsing telemetry log: {file.filename} for session {session.id}")
            parser = TelemetryParser(file_path)
            
            try:
                telemetry_data = parser.parse()
                
                # Check if we have any data
                if not telemetry_data or all(df.empty for df in telemetry_data.values()):
                    logger.warning(f"No usable data found in {file.filename}")
                    raise HTTPException(
                        status_code=400,
                        detail="No usable telemetry data found in the log file. Please try a different file."
                    )
                
                # Create analyzer with the parsed telemetry data
                logger.info(f"Creating analyzer for session {session.id}")
                analyzer = TelemetryAnalyzer(telemetry_data)
            
                # Update session with telemetry data and analyzer
                registry.create_session(
                    session_id=session.id,
                    telemetry_data=telemetry_data,
                    analyzer=analyzer
                )
            
                logger.info(f"Successfully processed log for session {session.id}")
                
                # Clean up temporary file
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        file_path = None
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to clean up temporary file: {str(cleanup_error)}")
                
                # Create response with session ID and set header
                response = SessionResponse(
                    session_id=session.id, 
                    message=f"Log file {file.filename} processed successfully"
                )
                
                # Convert the response to a dict, make it serializable, then dump to JSON
                response_dict = ensure_serializable(response.model_dump())
                response_json = json.dumps(response_dict, cls=CustomJSONEncoder)
                
                # Use FastAPI Response with pre-serialized JSON
                return JSONResponse(
                    content=json.loads(response_json),  # Parse back to dict
                    headers={"X-Session-ID": session.id}
                )
            
            except Exception as parsing_error:
                logger.error(f"Error parsing log file: {str(parsing_error)}")
                logger.error(traceback.format_exc())
                
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not parse the log file: {str(parsing_error)}"
                )
                
        except HTTPException:
            # Re-raise HTTP exceptions directly
            raise
        
        except Exception as processing_error:
            # Log other errors and return a friendly message
            logger.error(f"Error processing log file: {str(processing_error)}")
            logger.error(f"Processing error traceback: {traceback.format_exc()}")
            
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to process log file: {str(processing_error)}"
            )
    
    except HTTPException:
        # Make sure to clean up the file if there's an exception
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temporary file during error: {str(cleanup_error)}")
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        # Make sure to clean up the file if there's an exception
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temporary file during error: {str(cleanup_error)}")
                
        # Log general errors
        logger.error(f"Unexpected error in upload endpoint: {str(e)}")
        logger.error(f"Unexpected error traceback: {traceback.format_exc()}")
        
        # Return a generic error message
        raise HTTPException(
            status_code=500, 
            detail="An unexpected error occurred while processing your upload. Please try again later."
        )


@app.post("/chat", response_model=ChatResponse)
async def chat(
    message: ChatMessage,
    current_session: Optional[SessionData] = Depends(get_session_from_header)
):
    """
    Process a chat message using the UAV agent.
    
    This endpoint takes a user message and processes it against the telemetry
    data in the session, returning a response from the agent.
    
    Args:
        message: The user's chat message
        current_session: The session from header (from dependency)
        
    Returns:
        ChatResponse: Agent's response with analysis data
    """
    try:
        logger.info(f"Chat request received. Message: '{message.message[:30]}...', Header session: {current_session.id if current_session else 'None'}, Message session_id: {message.session_id or 'None'}")
        
        # Check if session ID is provided in the message and use it if available
        if message.session_id:
            session = registry.get_session(message.session_id)
            if not session:
                logger.warning(f"Session ID from message not found: {message.session_id}")
                raise HTTPException(
                    status_code=404,
                    detail=f"Session with ID {message.session_id} not found. Please upload a log file first."
                )
            logger.info(f"Using session from message ID: {session.id}")
        else:
            # Use the session from header
            session = current_session
            if not session:
                logger.warning("No session available in header or message")
                raise HTTPException(
                    status_code=400,
                    detail="No session available. Please upload a log file first."
                )
            logger.info(f"Using session from header: {session.id}")

        # Verify the session has telemetry data
        if not session.telemetry_data or not session.analyzer:
            logger.warning(f"Session {session.id} has no telemetry data")
            raise HTTPException(
                status_code=400,
                detail="No telemetry data available. Please upload a log file first."
            )
        logger.info(f"Session {session.id} has telemetry data and analyzer")
        
        # Ensure agent is initialized
        if not session.agent:
            if session.analyzer:
                # Initialize agent if we have analyzer but no agent
                logger.info(f"Initializing agent for session {session.id}")
                session.agent = UavAgent(session_id=session.id, analyzer=session.analyzer)
            else:
                logger.warning(f"Session {session.id} has no analyzer for agent initialization")
                raise HTTPException(
                    status_code=400,
                    detail="No telemetry data available. Please upload a log file first."
                )
        else:
            logger.info(f"Using existing agent for session {session.id}")
                
        # Process message with the agent
        try:
            # Set a timeout for the chat operation
            result = await asyncio.wait_for(
                session.agent.process_message(message.message),
                timeout=90.0  # 90 seconds timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Chat operation timed out for session {session.id}")
            return ChatResponse(
                response="I'm sorry, but your query is taking too long to process. Please try a simpler question.",
                session_id=session.id
            )
        except Exception as agent_error:
            # Log the error but return a graceful response
            logger.error(f"Agent error processing message: {str(agent_error)}")
            logger.error(f"Agent error traceback: {traceback.format_exc()}")
            
            return ChatResponse(
                response="I encountered an issue while processing your question. Let me try a simpler approach.",
                session_id=session.id
            )
        
        # Check if result contains an error field
        if isinstance(result, dict) and "error" in result and result["error"]:
            logger.error(f"Error reported from agent: {result['error']}")
            
            # Instead of raising an exception, return a graceful response
            return ChatResponse(
                response=f"I encountered a problem analyzing the telemetry data. {result.get('answer', 'Please try asking in a different way.')}",
                session_id=session.id
            )
        
        # Extract response and analysis data
        response_text = result.get("answer") or (
            "I couldn't generate an answer for your question."
        )
        analysis_data = result.get("analysis")
        
        # Store the message in session history
        try:
            session.messages.append({
                "role": "user",
                "content": message.message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            session.messages.append({
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except Exception as history_error:
            # Log but continue if saving to history fails
            logger.warning(f"Failed to save message to history: {str(history_error)}")
        
        # Return the response with session ID in both body and header
        response = ChatResponse(
            response=response_text,
            analysis=analysis_data,
            session_id=session.id
        )
        
        # Ensure the response is serializable using our custom encoder
        response_dict = ensure_serializable(response.model_dump())
        
        # Manually serialize to JSON with our custom encoder
        response_json = json.dumps(response_dict, cls=CustomJSONEncoder)
        
        # Use JSONResponse with pre-serialized content
        return JSONResponse(
            content=json.loads(response_json),  # Parse back to dict
            headers={"X-Session-ID": session.id}
        )
    except HTTPException:
        # Re-raise HTTP exceptions for proper handling
        raise
    except asyncio.CancelledError:
        logger.error(f"Chat task cancelled for session {session.id}")
        return ChatResponse(
            response="I'm sorry, but your request was cancelled. Please try again.",
            session_id=session.id
        )
    except Exception as e:
        # Log the error but return a graceful response
        logger.error(f"Unexpected error in chat endpoint: {str(e)}")
        logger.error(f"Chat error traceback: {traceback.format_exc()}")
        
        return ChatResponse(
            response="I'm sorry, but I encountered an unexpected issue. Please try again or upload a different log file.",
            session_id=session.id
        )


@app.get("/session/messages", response_model=Dict[str, List[Dict]])
async def get_session_messages(
    session_id: Optional[str] = None,
    current_session: Optional[SessionData] = Depends(get_session_from_header)
):
    """
    Get all messages for the current session.
    
    Returns:
        Dict: Contains a list of messages in the session
    """
    try:
        # Determine which session to use
        if session_id:
            session = registry.get_session(session_id)
            if not session:
                error_content = {"detail": f"Session with ID {session_id} not found"}
                error_json = json.dumps(ensure_serializable(error_content), cls=CustomJSONEncoder)
                return JSONResponse(
                    status_code=404,
                    content=json.loads(error_json),
                    headers={}
                )
        else:
            session = current_session
            if not session:
                error_content = {"detail": "No session available. Please upload a log file first."}
                error_json = json.dumps(ensure_serializable(error_content), cls=CustomJSONEncoder)
                return JSONResponse(
                    status_code=400, 
                    content=json.loads(error_json),
                    headers={}
                )
        
        # Get agent messages if available
        if session.agent and hasattr(session.agent, 'memory_manager'):
            try:
                agent_messages = session.agent.memory_manager.get_session_messages()
                content = {"messages": agent_messages}
                content_json = json.dumps(ensure_serializable(content), cls=CustomJSONEncoder)
                return JSONResponse(
                    content=json.loads(content_json),
                    headers={"X-Session-ID": session.id}
                )
            except Exception as e:
                # Log error but fall back to session messages
                logger.warning(f"Error retrieving agent messages: {str(e)}")
        
        # Fall back to session messages
        content = {"messages": session.messages}
        content_json = json.dumps(ensure_serializable(content), cls=CustomJSONEncoder)
        return JSONResponse(
            content=json.loads(content_json),
            headers={"X-Session-ID": session.id}
        )
    except Exception as e:
        # Log error but return empty list rather than failing
        logger.error(f"Error retrieving session messages: {str(e)}")
        logger.error(traceback.format_exc())
        return {"messages": []}


@app.get("/sessions", response_model=SessionListResponse)
async def list_sessions():
    """
    List all active sessions.
    
    Returns:
        SessionListResponse: List of session information
    """
    try:
        # Clean up old sessions
        registry.cleanup_expired_sessions()
        
        # Return all available sessions
        return SessionListResponse(
            sessions=[
                SessionInfo(
                    id=session.id,
                    created_at=session.created_at,
                    last_activity=session.last_activity,
                    has_telemetry=bool(session.telemetry_data and session.analyzer)
                ) for session in registry.sessions.values()
            ]
        )
    except Exception as e:
        # Log error but return empty list rather than failing
        logger.error(f"Error listing sessions: {str(e)}")
        logger.error(traceback.format_exc())
        return SessionListResponse(sessions=[])


@app.delete("/session", response_model=Dict[str, str])
async def end_session(
    session: SessionData = Depends(get_session_from_header)
):
    """
    End and delete a session.
    
    Args:
        session: The session to end (from dependency)
        
    Returns:
        Dict: Success message
    """
    try:
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Clean up session
        if registry.delete_session(session.id):
            return {"message": f"Session {session.id} ended successfully"}
        else:
            logger.warning(f"Failed to delete session {session.id}")
            return {"message": f"Session {session.id} may not have been fully cleaned up"}
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log error but return a user-friendly message
        logger.error(f"Error ending session: {str(e)}")
        logger.error(traceback.format_exc())
        return {"message": "An error occurred while ending the session, but it may have been partially cleaned up"}


@app.get("/")
async def root():
    """API root endpoint with information."""
    return {
        "status": "API is running", 
        "version": "2.0",
        "endpoints": [
            "/upload - Upload a telemetry log file",
            "/chat - Process a chat message",
            "/session/messages - Get session messages",
            "/sessions - List all active sessions",
            "/session - Delete current session"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on {HOST}:{PORT}")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True) 